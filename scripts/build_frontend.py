#!/usr/bin/env python3
"""
前端構建腳本
自動執行前端構建並將結果複製到後端包中
"""

import os
import sys
import shutil
import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, Any
import time

# 項目根目錄
PROJECT_ROOT = Path(__file__).parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend-dev"
BACKEND_FRONTEND_DIR = PROJECT_ROOT / "src" / "mcp_feedback_enhanced" / "frontend"
DIST_DIR = FRONTEND_DIR / "dist"

class FrontendBuilder:
    """前端構建器"""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.start_time = time.time()
        
    def log(self, message: str, level: str = "INFO") -> None:
        """記錄日誌"""
        if self.verbose:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] {level}: {message}")
    
    def run_command(self, command: list, cwd: Optional[Path] = None, shell: bool = False) -> subprocess.CompletedProcess:
        """執行命令"""
        self.log(f"執行命令: {' '.join(command)} (cwd: {cwd or PROJECT_ROOT})")

        try:
            result = subprocess.run(
                command,
                cwd=cwd or PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=True,
                shell=shell,
                encoding='utf-8',
                errors='ignore'  # 忽略編碼錯誤
            )

            if result.stdout:
                self.log(f"輸出: {result.stdout.strip()}")

            return result

        except subprocess.CalledProcessError as e:
            self.log(f"命令執行失敗: {e}", "ERROR")
            if e.stdout:
                self.log(f"標準輸出: {e.stdout}", "ERROR")
            if e.stderr:
                self.log(f"錯誤輸出: {e.stderr}", "ERROR")
            raise
        except FileNotFoundError as e:
            self.log(f"命令未找到: {e}", "ERROR")
            raise
    
    def check_prerequisites(self) -> bool:
        """檢查前置條件"""
        self.log("檢查前置條件...")

        # 檢查前端目錄
        if not FRONTEND_DIR.exists():
            self.log(f"❌ 前端目錄不存在: {FRONTEND_DIR}", "ERROR")
            return False

        # 檢查 package.json
        package_json = FRONTEND_DIR / "package.json"
        if not package_json.exists():
            self.log(f"❌ package.json 不存在: {package_json}", "ERROR")
            return False

        # 檢查 Node.js (在前端目錄中)
        try:
            result = self.run_command(["node", "--version"], cwd=FRONTEND_DIR)
            node_version = result.stdout.strip()
            self.log(f"Node.js 版本: {node_version}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log("❌ Node.js 未安裝或不在 PATH 中", "ERROR")
            return False

        # 檢查 npm (在前端目錄中，使用 shell)
        try:
            result = self.run_command(["npm", "--version"], cwd=FRONTEND_DIR, shell=True)
            npm_version = result.stdout.strip()
            self.log(f"npm 版本: {npm_version}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.log("❌ npm 未安裝或不在 PATH 中", "ERROR")
            return False

        self.log("✅ 前置條件檢查通過")
        return True
    
    def install_dependencies(self) -> bool:
        """安裝依賴"""
        self.log("安裝前端依賴...")
        
        try:
            # 檢查 node_modules 是否存在
            node_modules = FRONTEND_DIR / "node_modules"
            if node_modules.exists():
                self.log("node_modules 已存在，跳過安裝")
                return True
            
            # 安裝依賴
            self.run_command(["npm", "install"], cwd=FRONTEND_DIR, shell=True)
            self.log("✅ 依賴安裝完成")
            return True
            
        except subprocess.CalledProcessError:
            self.log("❌ 依賴安裝失敗", "ERROR")
            return False
    
    def build_frontend(self) -> bool:
        """構建前端"""
        self.log("開始構建前端...")
        
        try:
            # 清理舊的構建結果
            if DIST_DIR.exists():
                self.log("清理舊的構建結果...")
                shutil.rmtree(DIST_DIR)
            
            # 執行構建
            self.run_command(["npm", "run", "build"], cwd=FRONTEND_DIR, shell=True)
            
            # 檢查構建結果
            if not DIST_DIR.exists():
                self.log("❌ 構建失敗：dist 目錄不存在", "ERROR")
                return False
            
            # 檢查關鍵文件
            index_html = DIST_DIR / "index.html"
            if not index_html.exists():
                self.log("❌ 構建失敗：index.html 不存在", "ERROR")
                return False
            
            self.log("✅ 前端構建完成")
            return True
            
        except subprocess.CalledProcessError:
            self.log("❌ 前端構建失敗", "ERROR")
            return False
    
    def copy_build_results(self) -> bool:
        """複製構建結果到後端包"""
        self.log("複製構建結果到後端包...")
        
        try:
            # 創建目標目錄
            BACKEND_FRONTEND_DIR.mkdir(parents=True, exist_ok=True)
            
            # 清理舊的文件
            dist_target = BACKEND_FRONTEND_DIR / "dist"
            if dist_target.exists():
                shutil.rmtree(dist_target)
            
            # 複製構建結果
            shutil.copytree(DIST_DIR, dist_target)
            
            # 創建 __init__.py
            init_file = BACKEND_FRONTEND_DIR / "__init__.py"
            init_file.write_text('"""Frontend static files"""\n')
            
            # 統計文件
            file_count = sum(1 for _ in dist_target.rglob("*") if _.is_file())
            total_size = sum(f.stat().st_size for f in dist_target.rglob("*") if f.is_file())
            
            self.log(f"✅ 複製完成：{file_count} 個文件，總大小 {self.format_size(total_size)}")
            return True
            
        except Exception as e:
            self.log(f"❌ 複製失敗: {e}", "ERROR")
            return False
    
    def generate_build_info(self) -> bool:
        """生成構建信息"""
        self.log("生成構建信息...")
        
        try:
            build_info = {
                "build_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "build_duration": round(time.time() - self.start_time, 2),
                "node_version": self.run_command(["node", "--version"], cwd=FRONTEND_DIR).stdout.strip(),
                "npm_version": self.run_command(["npm", "--version"], cwd=FRONTEND_DIR, shell=True).stdout.strip(),
                "frontend_dir": str(FRONTEND_DIR),
                "dist_dir": str(DIST_DIR),
                "backend_dir": str(BACKEND_FRONTEND_DIR)
            }
            
            # 讀取 package.json 信息
            package_json = FRONTEND_DIR / "package.json"
            if package_json.exists():
                with open(package_json, 'r', encoding='utf-8') as f:
                    package_data = json.load(f)
                    build_info["frontend_version"] = package_data.get("version", "unknown")
                    build_info["dependencies"] = package_data.get("dependencies", {})
            
            # 保存構建信息
            build_info_file = BACKEND_FRONTEND_DIR / "build_info.json"
            with open(build_info_file, 'w', encoding='utf-8') as f:
                json.dump(build_info, f, indent=2, ensure_ascii=False)
            
            self.log("✅ 構建信息已生成")
            return True
            
        except Exception as e:
            self.log(f"❌ 生成構建信息失敗: {e}", "ERROR")
            return False
    
    def format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def build(self) -> bool:
        """執行完整構建流程"""
        self.log("🎯 開始前端構建流程")
        
        steps = [
            ("檢查前置條件", self.check_prerequisites),
            ("安裝依賴", self.install_dependencies),
            ("構建前端", self.build_frontend),
            ("複製構建結果", self.copy_build_results),
            ("生成構建信息", self.generate_build_info)
        ]
        
        for step_name, step_func in steps:
            self.log(f"📋 {step_name}...")
            if not step_func():
                self.log(f"❌ {step_name}失敗", "ERROR")
                return False
        
        duration = round(time.time() - self.start_time, 2)
        self.log(f"🎉 前端構建完成！耗時 {duration} 秒")
        return True


def main():
    """主函數"""
    import argparse
    
    parser = argparse.ArgumentParser(description="前端構建腳本")
    parser.add_argument("--quiet", "-q", action="store_true", help="靜默模式")
    parser.add_argument("--clean", "-c", action="store_true", help="清理構建結果")
    
    args = parser.parse_args()
    
    if args.clean:
        print("🧹 清理構建結果...")
        
        # 清理前端 dist
        if DIST_DIR.exists():
            shutil.rmtree(DIST_DIR)
            print(f"✅ 已清理: {DIST_DIR}")
        
        # 清理後端 frontend
        if BACKEND_FRONTEND_DIR.exists():
            shutil.rmtree(BACKEND_FRONTEND_DIR)
            print(f"✅ 已清理: {BACKEND_FRONTEND_DIR}")
        
        print("🎉 清理完成")
        return
    
    # 執行構建
    builder = FrontendBuilder(verbose=not args.quiet)
    success = builder.build()
    
    if success:
        print("🎉 前端構建成功！")
        sys.exit(0)
    else:
        print("❌ 前端構建失敗！")
        sys.exit(1)


if __name__ == "__main__":
    main()
