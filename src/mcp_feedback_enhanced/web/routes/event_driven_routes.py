#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件驅動路由
============

基於事件驅動架構的新路由處理器，逐步替換舊的路由邏輯。
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

from ..core import get_webui_adapter, initialize_webui_adapter
from ...debug import web_debug_log as debug_log

if TYPE_CHECKING:
    from ..main import WebUIManager

logger = logging.getLogger(__name__)


def setup_event_driven_routes(manager: 'WebUIManager'):
    """設置事件驅動路由"""
    
    @manager.app.websocket("/ws/v2")
    async def websocket_endpoint_v2(websocket: WebSocket):
        """事件驅動的 WebSocket 端點"""
        # 獲取當前活躍會話
        session = manager.get_current_session()
        if not session:
            await websocket.close(code=4004, reason="沒有活躍會話")
            return
        
        # 初始化事件驅動適配器
        try:
            adapter = await initialize_webui_adapter(manager)
            debug_log("✅ 事件驅動適配器已初始化")
        except Exception as e:
            debug_log(f"❌ 初始化事件驅動適配器失敗: {e}")
            await websocket.close(code=4005, reason="架構初始化失敗")
            return
        
        # 使用事件驅動的 WebSocket 處理器
        await adapter.handle_websocket_connection(websocket, session)
    
    @manager.app.get("/api/v2/health")
    async def health_check_v2():
        """事件驅動架構健康檢查"""
        try:
            adapter = get_webui_adapter(manager)
            health = await adapter.health_check()
            
            return JSONResponse(content={
                "status": "success",
                "health": health,
                "timestamp": time.time()
            })
        except Exception as e:
            debug_log(f"健康檢查失敗: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": str(e),
                    "timestamp": time.time()
                }
            )
    
    @manager.app.get("/api/v2/statistics")
    async def get_statistics_v2():
        """獲取事件驅動架構統計信息"""
        try:
            adapter = get_webui_adapter(manager)
            stats = adapter.get_statistics()
            
            return JSONResponse(content={
                "status": "success",
                "statistics": stats,
                "timestamp": time.time()
            })
        except Exception as e:
            debug_log(f"獲取統計信息失敗: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": str(e),
                    "timestamp": time.time()
                }
            )
    
    @manager.app.post("/api/v2/session/create")
    async def create_session_v2(request: Request):
        """事件驅動的會話創建"""
        try:
            data = await request.json()
            project_directory = data.get("project_directory", "")
            summary = data.get("summary", "")
            timeout = data.get("timeout", 600)
            
            if not project_directory or not summary:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": "缺少必要參數: project_directory 和 summary"
                    }
                )
            
            adapter = await initialize_webui_adapter(manager)
            session_id = await adapter.create_session(project_directory, summary, timeout)
            
            return JSONResponse(content={
                "status": "success",
                "session_id": session_id,
                "message": "會話創建成功"
            })
            
        except Exception as e:
            debug_log(f"創建會話失敗: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": f"創建會話失敗: {str(e)}"
                }
            )
    
    @manager.app.post("/api/v2/session/update")
    async def update_session_v2(request: Request):
        """事件驅動的會話更新"""
        try:
            data = await request.json()
            session_id = data.get("session_id", "")
            old_session_id = data.get("old_session_id")
            changes = data.get("changes", {})
            
            if not session_id:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": "缺少必要參數: session_id"
                    }
                )
            
            adapter = get_webui_adapter(manager)
            await adapter.update_session(session_id, old_session_id, changes)
            
            return JSONResponse(content={
                "status": "success",
                "message": "會話更新成功"
            })
            
        except Exception as e:
            debug_log(f"更新會話失敗: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": f"更新會話失敗: {str(e)}"
                }
            )
    
    @manager.app.post("/api/v2/session/broadcast")
    async def broadcast_to_session_v2(request: Request):
        """事件驅動的會話廣播"""
        try:
            data = await request.json()
            session_id = data.get("session_id", "")
            message = data.get("message", {})
            
            if not session_id or not message:
                return JSONResponse(
                    status_code=400,
                    content={
                        "status": "error",
                        "message": "缺少必要參數: session_id 和 message"
                    }
                )
            
            adapter = get_webui_adapter(manager)
            await adapter.broadcast_to_session(session_id, message)
            
            return JSONResponse(content={
                "status": "success",
                "message": "消息廣播成功"
            })
            
        except Exception as e:
            debug_log(f"廣播消息失敗: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": f"廣播消息失敗: {str(e)}"
                }
            )
    
    @manager.app.get("/api/v2/session/current")
    async def get_current_session_v2():
        """獲取當前會話信息"""
        try:
            adapter = get_webui_adapter(manager)
            current_session = adapter.get_current_session()
            
            if not current_session:
                return JSONResponse(content={
                    "status": "success",
                    "session": None,
                    "message": "沒有活躍會話"
                })
            
            return JSONResponse(content={
                "status": "success",
                "session": {
                    "session_id": current_session.session_id,
                    "project_directory": current_session.project_directory,
                    "summary": current_session.summary,
                    "status": current_session.status.value,
                    "status_message": current_session.status_message,
                    "created_at": current_session.created_at,
                    "last_activity": current_session.last_activity
                }
            })
            
        except Exception as e:
            debug_log(f"獲取當前會話失敗: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": f"獲取當前會話失敗: {str(e)}"
                }
            )
    
    @manager.app.get("/api/v2/debug/events")
    async def get_event_history():
        """獲取事件歷史（調試用）"""
        try:
            adapter = get_webui_adapter(manager)
            if not adapter._initialized:
                return JSONResponse(content={
                    "status": "error",
                    "message": "事件驅動架構未初始化"
                })
            
            # 獲取事件歷史
            event_history = adapter.architecture_manager.event_bus.get_event_history(50)
            
            # 轉換為可序列化的格式
            serializable_events = []
            for event in event_history:
                serializable_events.append({
                    "event_id": event.event_id,
                    "event_type": event.__class__.__name__,
                    "timestamp": event.timestamp.isoformat(),
                    "priority": event.priority.value,
                    "source": event.source,
                    "metadata": event.metadata
                })
            
            return JSONResponse(content={
                "status": "success",
                "events": serializable_events,
                "count": len(serializable_events)
            })
            
        except Exception as e:
            debug_log(f"獲取事件歷史失敗: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "status": "error",
                    "message": f"獲取事件歷史失敗: {str(e)}"
                }
            )
    
    debug_log("✅ 事件驅動路由已設置完成")
