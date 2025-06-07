"""
構建工具模組
提供前端構建和集成相關的工具函數
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

def get_project_root() -> Path:
    """獲取專案根目錄"""
    # 從當前文件向上查找 pyproject.toml
    current = Path(__file__).parent
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    
    # 如果找不到，使用相對路徑
    return Path(__file__).parent.parent.parent.parent

def get_frontend_dir() -> Path:
    """獲取前端開發目錄"""
    return get_project_root() / "frontend-dev"

def get_backend_frontend_dir() -> Path:
    """獲取後端前端文件目錄"""
    return Path(__file__).parent.parent / "frontend"

def check_frontend_built() -> bool:
    """檢查前端是否已構建"""
    backend_frontend_dir = get_backend_frontend_dir()
    dist_dir = backend_frontend_dir / "dist"
    index_html = dist_dir / "index.html"
    
    return dist_dir.exists() and index_html.exists()

def get_build_info() -> Dict[str, Any]:
    """獲取構建信息"""
    try:
        build_info_file = get_backend_frontend_dir() / "build_info.json"
        if build_info_file.exists():
            with open(build_info_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"無法讀取構建信息: {e}")
    
    return {}

def run_frontend_build(verbose: bool = True) -> bool:
    """
    運行前端構建
    
    Args:
        verbose: 是否顯示詳細輸出
        
    Returns:
        bool: 構建是否成功
    """
    try:
        # 導入構建腳本
        project_root = get_project_root()
        build_script = project_root / "scripts" / "build_frontend.py"
        
        if not build_script.exists():
            logger.error(f"構建腳本不存在: {build_script}")
            return False
        
        # 執行構建腳本
        cmd = [sys.executable, str(build_script)]
        if not verbose:
            cmd.append("--quiet")
        
        logger.info("開始前端構建...")
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=not verbose,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        
        if result.returncode == 0:
            logger.info("✅ 前端構建成功")
            return True
        else:
            logger.error("❌ 前端構建失敗")
            if not verbose and result.stderr:
                logger.error(f"錯誤輸出: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"前端構建過程中出現異常: {e}")
        return False

def ensure_frontend_built(force_rebuild: bool = False, verbose: bool = True) -> bool:
    """
    確保前端已構建
    
    Args:
        force_rebuild: 是否強制重新構建
        verbose: 是否顯示詳細輸出
        
    Returns:
        bool: 前端是否可用
    """
    if not force_rebuild and check_frontend_built():
        if verbose:
            build_info = get_build_info()
            build_time = build_info.get('build_time', '未知')
            logger.info(f"✅ 前端已構建 (構建時間: {build_time})")
        return True
    
    if verbose:
        logger.info("🔨 前端未構建或需要重新構建")
    
    return run_frontend_build(verbose)

def clean_frontend_build() -> bool:
    """
    清理前端構建結果
    
    Returns:
        bool: 清理是否成功
    """
    try:
        # 清理前端 dist 目錄
        frontend_dir = get_frontend_dir()
        frontend_dist = frontend_dir / "dist"
        if frontend_dist.exists():
            shutil.rmtree(frontend_dist)
            logger.info(f"✅ 已清理前端構建目錄: {frontend_dist}")
        
        # 清理後端前端目錄
        backend_frontend_dir = get_backend_frontend_dir()
        if backend_frontend_dir.exists():
            shutil.rmtree(backend_frontend_dir)
            logger.info(f"✅ 已清理後端前端目錄: {backend_frontend_dir}")
        
        return True
        
    except Exception as e:
        logger.error(f"清理前端構建失敗: {e}")
        return False

def get_frontend_stats() -> Dict[str, Any]:
    """
    獲取前端統計信息
    
    Returns:
        Dict: 前端統計信息
    """
    stats = {
        "frontend_built": check_frontend_built(),
        "build_info": get_build_info(),
        "frontend_dir": str(get_frontend_dir()),
        "backend_frontend_dir": str(get_backend_frontend_dir()),
        "file_count": 0,
        "total_size": 0
    }
    
    # 統計文件信息
    try:
        backend_frontend_dir = get_backend_frontend_dir()
        dist_dir = backend_frontend_dir / "dist"
        
        if dist_dir.exists():
            for file_path in dist_dir.rglob("*"):
                if file_path.is_file():
                    stats["file_count"] += 1
                    stats["total_size"] += file_path.stat().st_size
    except Exception as e:
        logger.warning(f"統計前端文件信息失敗: {e}")
    
    return stats

def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"

def check_node_environment() -> Dict[str, Any]:
    """
    檢查 Node.js 環境
    
    Returns:
        Dict: Node.js 環境信息
    """
    env_info = {
        "node_available": False,
        "npm_available": False,
        "node_version": None,
        "npm_version": None,
        "frontend_dir_exists": False,
        "package_json_exists": False
    }
    
    try:
        # 檢查 Node.js
        result = subprocess.run(
            ["node", "--version"],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        if result.returncode == 0:
            env_info["node_available"] = True
            env_info["node_version"] = result.stdout.strip()
    except FileNotFoundError:
        pass
    
    try:
        # 檢查 npm
        frontend_dir = get_frontend_dir()
        result = subprocess.run(
            ["npm", "--version"],
            cwd=frontend_dir,
            capture_output=True,
            text=True,
            shell=True,
            encoding='utf-8',
            errors='ignore'
        )
        if result.returncode == 0:
            env_info["npm_available"] = True
            env_info["npm_version"] = result.stdout.strip()
    except FileNotFoundError:
        pass
    
    # 檢查前端目錄
    frontend_dir = get_frontend_dir()
    env_info["frontend_dir_exists"] = frontend_dir.exists()
    env_info["package_json_exists"] = (frontend_dir / "package.json").exists()
    
    return env_info

def is_development_mode() -> bool:
    """檢查是否為開發模式"""
    return os.getenv("ENVIRONMENT", "production").lower() in ("development", "dev")

def get_frontend_url() -> str:
    """獲取前端 URL"""
    if is_development_mode():
        return os.getenv("FRONTEND_DEV_URL", "http://localhost:3000")
    else:
        return "/"
