"""
靜態文件服務器
提供前端構建文件服務，支持 SPA 路由
"""

import os
import mimetypes
from pathlib import Path
from typing import Optional, Dict, Any
import json
import logging

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

class SPAStaticFiles(StaticFiles):
    """
    支持 SPA 的靜態文件服務器
    對於不存在的路由，返回 index.html
    """
    
    def __init__(self, *args, **kwargs):
        self.spa_mode = kwargs.pop('spa_mode', True)
        super().__init__(*args, **kwargs)
    
    async def get_response(self, path: str, scope):
        """
        獲取響應，支持 SPA 路由回退
        """
        try:
            # 嘗試獲取正常的靜態文件響應
            response = await super().get_response(path, scope)
            return response
        except HTTPException as e:
            if e.status_code == 404 and self.spa_mode:
                # 如果是 404 且啟用 SPA 模式，返回 index.html
                # 但排除 API 路由和文件擴展名
                if not path.startswith('api/') and '.' not in Path(path).name:
                    try:
                        return await super().get_response('index.html', scope)
                    except HTTPException:
                        pass
            raise


class FrontendStaticServer:
    """前端靜態文件服務器管理器"""
    
    def __init__(self, app: FastAPI):
        self.app = app
        self.frontend_dir = self._get_frontend_dir()
        self.build_info = self._load_build_info()
        
    def _get_frontend_dir(self) -> Optional[Path]:
        """獲取前端文件目錄"""
        # 嘗試多個可能的路徑
        possible_paths = [
            # 打包後的路徑
            Path(__file__).parent.parent / "frontend" / "dist",
            # 開發環境路徑
            Path(__file__).parent.parent.parent.parent / "frontend-dev" / "dist",
        ]
        
        for path in possible_paths:
            if path.exists() and (path / "index.html").exists():
                logger.info(f"找到前端文件目錄: {path}")
                return path
        
        logger.warning("未找到前端文件目錄")
        return None
    
    def _load_build_info(self) -> Dict[str, Any]:
        """加載構建信息"""
        try:
            build_info_file = Path(__file__).parent.parent / "frontend" / "build_info.json"
            if build_info_file.exists():
                with open(build_info_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"無法加載構建信息: {e}")
        
        return {}
    
    def setup_static_files(self) -> bool:
        """設置靜態文件服務"""
        if not self.frontend_dir:
            logger.error("前端文件目錄不存在，無法設置靜態文件服務")
            return False
        
        try:
            # 設置靜態文件服務
            self.app.mount(
                "/static",
                SPAStaticFiles(
                    directory=str(self.frontend_dir / "assets"),
                    spa_mode=False  # 靜態資源不需要 SPA 模式
                ),
                name="static"
            )
            
            # 設置根路徑的 SPA 服務
            self.app.mount(
                "/",
                SPAStaticFiles(
                    directory=str(self.frontend_dir),
                    html=True,
                    spa_mode=True
                ),
                name="spa"
            )
            
            logger.info("靜態文件服務設置完成")
            return True
            
        except Exception as e:
            logger.error(f"設置靜態文件服務失敗: {e}")
            return False
    
    def setup_routes(self):
        """設置額外的路由"""
        
        @self.app.get("/health/frontend")
        async def frontend_health():
            """前端健康檢查"""
            return {
                "status": "ok",
                "frontend_available": self.frontend_dir is not None,
                "frontend_dir": str(self.frontend_dir) if self.frontend_dir else None,
                "build_info": self.build_info
            }
        
        @self.app.get("/api/frontend/info")
        async def frontend_info():
            """前端信息 API"""
            if not self.frontend_dir:
                raise HTTPException(status_code=404, detail="Frontend not available")
            
            # 統計文件信息
            file_count = 0
            total_size = 0
            
            try:
                for file_path in self.frontend_dir.rglob("*"):
                    if file_path.is_file():
                        file_count += 1
                        total_size += file_path.stat().st_size
            except Exception as e:
                logger.warning(f"統計文件信息失敗: {e}")
            
            return {
                "frontend_dir": str(self.frontend_dir),
                "file_count": file_count,
                "total_size": total_size,
                "build_info": self.build_info,
                "available_files": [
                    str(f.relative_to(self.frontend_dir))
                    for f in self.frontend_dir.rglob("*")
                    if f.is_file()
                ][:20]  # 限制返回前 20 個文件
            }
    
    def get_mime_type(self, file_path: Path) -> str:
        """獲取 MIME 類型"""
        mime_type, _ = mimetypes.guess_type(str(file_path))
        
        if mime_type:
            return mime_type
        
        # 自定義 MIME 類型映射
        custom_types = {
            '.js': 'application/javascript',
            '.mjs': 'application/javascript',
            '.css': 'text/css',
            '.html': 'text/html',
            '.json': 'application/json',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon',
            '.woff': 'font/woff',
            '.woff2': 'font/woff2',
            '.ttf': 'font/ttf',
            '.eot': 'application/vnd.ms-fontobject'
        }
        
        suffix = file_path.suffix.lower()
        return custom_types.get(suffix, 'application/octet-stream')
    
    def setup_cache_headers(self):
        """設置緩存頭"""
        
        @self.app.middleware("http")
        async def add_cache_headers(request: Request, call_next):
            """添加緩存頭中間件"""
            response = await call_next(request)
            
            # 只對靜態文件添加緩存頭
            if request.url.path.startswith('/static/') or request.url.path.startswith('/assets/'):
                # 靜態資源長期緩存
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            elif request.url.path.endswith(('.html', '.htm')):
                # HTML 文件短期緩存
                response.headers["Cache-Control"] = "public, max-age=3600"
            elif request.url.path.startswith('/api/'):
                # API 不緩存
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            
            return response


def setup_frontend_static(app: FastAPI) -> FrontendStaticServer:
    """
    設置前端靜態文件服務
    
    Args:
        app: FastAPI 應用實例
        
    Returns:
        FrontendStaticServer 實例
    """
    static_server = FrontendStaticServer(app)
    
    # 設置靜態文件服務
    if static_server.setup_static_files():
        logger.info("✅ 前端靜態文件服務設置成功")
    else:
        logger.warning("⚠️ 前端靜態文件服務設置失敗，可能在開發模式下運行")
    
    # 設置額外路由
    static_server.setup_routes()
    
    # 設置緩存頭
    static_server.setup_cache_headers()
    
    return static_server


# 開發模式下的靜態文件服務
def setup_development_static(app: FastAPI, frontend_dev_url: str = "http://localhost:3000"):
    """
    開發模式下的靜態文件代理設置
    
    Args:
        app: FastAPI 應用實例
        frontend_dev_url: 前端開發服務器 URL
    """
    
    @app.get("/")
    async def development_root():
        """開發模式根路由"""
        return HTMLResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>MCP Feedback Enhanced - Development Mode</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .container {{ max-width: 600px; margin: 0 auto; }}
                .notice {{ background: #f0f9ff; border: 1px solid #0ea5e9; padding: 20px; border-radius: 8px; }}
                .links {{ margin-top: 20px; }}
                .links a {{ display: inline-block; margin-right: 15px; padding: 8px 16px; background: #3b82f6; color: white; text-decoration: none; border-radius: 4px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎯 MCP Feedback Enhanced</h1>
                <div class="notice">
                    <h3>🔧 開發模式</h3>
                    <p>您正在開發模式下運行後端服務。前端開發服務器應該在另一個端口運行。</p>
                    <div class="links">
                        <a href="{frontend_dev_url}" target="_blank">前端開發服務器</a>
                        <a href="/docs" target="_blank">API 文檔</a>
                        <a href="/health/frontend">前端健康檢查</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """)
    
    logger.info(f"🔧 開發模式：前端服務器 URL 設置為 {frontend_dev_url}")


# 工具函數
def is_development_mode() -> bool:
    """檢查是否為開發模式"""
    return os.getenv("ENVIRONMENT", "production").lower() in ("development", "dev")


def get_frontend_url() -> str:
    """獲取前端 URL"""
    if is_development_mode():
        return os.getenv("FRONTEND_DEV_URL", "http://localhost:3000")
    else:
        return "/"
