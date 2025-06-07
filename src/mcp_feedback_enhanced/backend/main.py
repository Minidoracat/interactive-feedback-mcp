"""
FastAPI Main Application for MCP Feedback Enhanced

This module provides the main FastAPI application with all routes, middleware,
and lifecycle management for the MCP Feedback Enhanced system.
"""

import asyncio
import logging
import sys
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .models import (
    ErrorResponse,
    HealthResponse,
    VersionResponse,
    SessionModel,
    FeedbackModel
)
from .session import get_session_manager
from .websocket import get_websocket_manager
from .mcp_server import get_mcp_server
from .file_handler import get_file_handler
from .static import setup_frontend_static, setup_development_static, is_development_mode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global startup time for uptime calculation
startup_time = time.time()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown operations.
    """
    # Startup
    logger.info("Starting MCP Feedback Enhanced application...")
    
    try:
        # Start session manager
        session_manager = get_session_manager()
        await session_manager.start()
        
        # Start MCP server
        mcp_server = get_mcp_server()
        await mcp_server.start()
        
        logger.info("Application startup completed successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Error during application startup: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down MCP Feedback Enhanced application...")
        
        try:
            # Stop MCP server
            mcp_server = get_mcp_server()
            await mcp_server.stop()
            
            # Stop session manager
            session_manager = get_session_manager()
            await session_manager.stop()
            
            logger.info("Application shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during application shutdown: {e}")


# Create FastAPI application
def create_app() -> FastAPI:
    """Create and configure the FastAPI application"""
    
    settings = get_settings()
    
    app = FastAPI(
        title="MCP Feedback Enhanced",
        description="Advanced feedback collection system with real-time web interface and file upload support",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )
    
    # Add middleware
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
    
    # Add routes
    add_api_routes(app)
    add_websocket_routes(app)
    add_static_routes(app)
    
    # Add exception handlers
    add_exception_handlers(app)
    
    return app


def add_api_routes(app: FastAPI):
    """Add API routes to the application"""
    
    @app.get("/api/health", response_model=HealthResponse)
    async def health_check():
        """Health check endpoint"""
        try:
            settings = get_settings()
            session_manager = get_session_manager()
            websocket_manager = get_websocket_manager()
            file_handler = get_file_handler()
            
            # Calculate uptime
            uptime = time.time() - startup_time
            
            # Get statistics
            session_stats = session_manager.get_session_stats()
            websocket_stats = websocket_manager.get_connection_stats()
            storage_stats = file_handler.get_storage_stats()
            
            return HealthResponse(
                status="healthy",
                version="0.1.0",
                timestamp=datetime.now(timezone.utc),
                uptime=uptime,
                sessions={
                    "total": session_stats["total"],
                    "active": session_stats["active"],
                    "completed": session_stats["completed"],
                    "expired": session_stats["expired"]
                }
            )
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            raise HTTPException(status_code=500, detail="Health check failed")
    
    @app.get("/api/version", response_model=VersionResponse)
    async def get_version():
        """Get version information"""
        try:
            return VersionResponse(
                version="0.1.0",
                build_date=None,
                git_commit=None,
                python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                dependencies={
                    "fastapi": "0.104.0+",
                    "uvicorn": "0.24.0+",
                    "pydantic": "2.5.0+",
                    "mcp": "1.9.3+"
                }
            )
            
        except Exception as e:
            logger.error(f"Version check failed: {e}")
            raise HTTPException(status_code=500, detail="Version check failed")
    
    @app.get("/api/sessions/{session_id}", response_model=Dict)
    async def get_session(session_id: str):
        """Get session information"""
        try:
            session_manager = get_session_manager()
            session = session_manager.get_session(session_id)
            
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            
            # Update activity
            session_manager.update_session_activity(session_id)
            
            return {
                "session_id": session.id,
                "status": session.status.value,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "expires_at": session.expires_at.isoformat(),
                "last_activity": session.last_activity.isoformat(),
                "is_expired": session.is_expired(),
                "is_active": session.is_active(),
                "has_feedback": session.feedback is not None,
                "client_info": session.client_info
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting session {session_id}: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @app.get("/api/sessions", response_model=Dict)
    async def list_sessions():
        """List all sessions with statistics"""
        try:
            session_manager = get_session_manager()
            websocket_manager = get_websocket_manager()
            
            session_stats = session_manager.get_session_stats()
            websocket_stats = websocket_manager.get_connection_stats()
            
            return {
                "session_statistics": session_stats,
                "websocket_statistics": websocket_stats,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error listing sessions: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")
    
    @app.get("/api/mcp/info", response_model=Dict)
    async def get_mcp_info():
        """Get MCP server information"""
        try:
            mcp_server = get_mcp_server()
            return mcp_server.get_server_info()
            
        except Exception as e:
            logger.error(f"Error getting MCP info: {e}")
            raise HTTPException(status_code=500, detail="Internal server error")


def add_websocket_routes(app: FastAPI):
    """Add WebSocket routes to the application"""
    
    @app.websocket("/ws/session/{session_id}")
    async def websocket_endpoint(websocket: WebSocket, session_id: str):
        """WebSocket endpoint for real-time session communication"""
        websocket_manager = get_websocket_manager()
        
        # Connect to session
        connected = await websocket_manager.connect(websocket, session_id)
        if not connected:
            return
        
        try:
            while True:
                # Receive message
                data = await websocket.receive_text()
                await websocket_manager.handle_message(websocket, data)
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for session {session_id}")
        except Exception as e:
            logger.error(f"WebSocket error for session {session_id}: {e}")
        finally:
            # Clean up connection
            await websocket_manager.disconnect(websocket)


def add_static_routes(app: FastAPI):
    """Add static file routes for frontend"""
    try:
        if is_development_mode():
            # 開發模式：設置開發代理
            setup_development_static(app)
            logger.info("🔧 開發模式：靜態文件代理已設置")
        else:
            # 生產模式：設置靜態文件服務
            static_server = setup_frontend_static(app)
            logger.info("🚀 生產模式：靜態文件服務已設置")

    except Exception as e:
        logger.error(f"Error setting up static routes: {e}")

        # 回退到基本 API 模式
        @app.get("/")
        async def fallback_root():
            """回退根端點"""
            return {
                "message": "MCP Feedback Enhanced API",
                "version": "0.1.0",
                "docs": "/docs",
                "health": "/api/health",
                "status": "Static file service unavailable - API only mode"
            }


def add_exception_handlers(app: FastAPI):
    """Add global exception handlers"""
    
    @app.exception_handler(404)
    async def not_found_handler(request, exc):
        """Handle 404 errors"""
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="NOT_FOUND",
                message="The requested resource was not found",
                timestamp=datetime.now(timezone.utc)
            ).model_dump()
        )
    
    @app.exception_handler(500)
    async def internal_error_handler(request, exc):
        """Handle 500 errors"""
        logger.error(f"Internal server error: {exc}")
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="INTERNAL_ERROR",
                message="An internal server error occurred",
                timestamp=datetime.now(timezone.utc)
            ).model_dump()
        )


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
        log_level=settings.log_level
    )
