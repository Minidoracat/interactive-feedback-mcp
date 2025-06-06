#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebSocket 處理器
================

事件驅動的 WebSocket 處理器，整合現有的 WebUIManager 功能。
負責處理 WebSocket 連接、消息路由和會話管理。
"""

import asyncio
import json
import time
import logging
from typing import Dict, Any, Optional
from fastapi import WebSocket, WebSocketDisconnect

from .architecture_manager import ArchitectureManager
from .events import (
    ConnectionEstablishedEvent, ConnectionClosedEvent, ConnectionErrorEvent,
    SessionAssignedEvent, FeedbackSubmittedEvent, LatestSummaryRequestedEvent
)
from ..models.feedback_session import WebFeedbackSession, SessionStatus
from ...debug import web_debug_log as debug_log

logger = logging.getLogger(__name__)


class WebSocketHandler:
    """事件驅動的 WebSocket 處理器"""
    
    def __init__(self, architecture_manager: ArchitectureManager):
        self.architecture_manager = architecture_manager
        self.active_connections: Dict[str, Dict[str, Any]] = {}
        
        logger.info("WebSocket 處理器初始化完成")
    
    async def handle_websocket_connection(self, websocket: WebSocket, session: WebFeedbackSession):
        """
        處理 WebSocket 連接
        
        Args:
            websocket: WebSocket 連接
            session: 關聯的會話
        """
        connection = None
        
        try:
            # 接受 WebSocket 連接
            await websocket.accept()
            
            # 註冊連接到事件驅動架構
            client_info = {
                'user_agent': websocket.headers.get('user-agent', 'unknown'),
                'origin': websocket.headers.get('origin', 'unknown'),
                'session_id': session.session_id
            }
            
            connection = await self.architecture_manager.register_websocket_connection(
                websocket, session.session_id, client_info
            )
            
            if not connection:
                await websocket.close(code=4003, reason="連接註冊失敗")
                return
            
            # 更新會話的 WebSocket 連接
            session.websocket = websocket
            
            # 發布會話分配事件
            assignment_event = SessionAssignedEvent(
                session_id=session.session_id,
                connection_id=connection.connection_id,
                assignment_type="new"
            )
            await self.architecture_manager.event_bus.publish(assignment_event)
            
            debug_log(f"WebSocket 連接已建立: {connection.connection_id} -> 會話 {session.session_id}")
            
            # 發送連接確認和初始狀態
            await self._send_connection_confirmation(websocket, session)
            
            # 處理消息循環
            await self._message_loop(websocket, connection, session)
            
        except WebSocketDisconnect:
            debug_log(f"WebSocket 連接正常斷開: {connection.connection_id if connection else 'unknown'}")
        except ConnectionResetError:
            debug_log(f"WebSocket 連接被重置: {connection.connection_id if connection else 'unknown'}")
        except Exception as e:
            debug_log(f"WebSocket 錯誤: {e}")
            
            # 發布連接錯誤事件
            if connection:
                error_event = ConnectionErrorEvent(
                    connection_id=connection.connection_id,
                    session_id=session.session_id,
                    error_message=str(e),
                    error_type=type(e).__name__
                )
                await self.architecture_manager.event_bus.publish(error_event)
        
        finally:
            # 清理連接
            if connection:
                await self.architecture_manager.unregister_websocket_connection(
                    connection.connection_id, 1000, "連接關閉"
                )
            
            # 清理會話中的 WebSocket 連接
            if session.websocket == websocket:
                session.websocket = None
                debug_log("已清理會話中的 WebSocket 連接")
    
    async def _send_connection_confirmation(self, websocket: WebSocket, session: WebFeedbackSession):
        """發送連接確認和初始狀態"""
        try:
            # 發送連接確認
            await websocket.send_json({
                "type": "connection_established",
                "message": "WebSocket 連接已建立"
            })
            
            # 檢查是否有待發送的會話更新（從舊架構遷移）
            # 這裡可以通過狀態管理器檢查待更新數據
            pending_updates = await self.architecture_manager.state_manager.get_pending_updates(session.session_id)
            
            if pending_updates:
                debug_log("🔄 檢測到待發送的會話更新，準備發送通知")
                try:
                    await websocket.send_json({
                        "type": "session_updated",
                        "message": "新會話已創建，正在更新頁面內容",
                        "session_info": {
                            "project_directory": session.project_directory,
                            "summary": session.summary,
                            "session_id": session.session_id
                        }
                    })
                    
                    # 清理待更新數據
                    await self.architecture_manager.state_manager.clear_pending_updates(session.session_id)
                    debug_log("✅ 已發送會話更新通知到前端")
                except Exception as e:
                    debug_log(f"❌ 發送會話更新通知失敗: {e}")
            
            # 發送當前會話狀態
            try:
                await websocket.send_json({
                    "type": "status_update",
                    "status_info": session.get_status_info()
                })
                debug_log("✅ 已發送當前會話狀態到前端")
            except Exception as e:
                debug_log(f"❌ 發送會話狀態失敗: {e}")
                
        except Exception as e:
            debug_log(f"發送連接確認失敗: {e}")
    
    async def _message_loop(self, websocket: WebSocket, connection, session: WebFeedbackSession):
        """WebSocket 消息處理循環"""
        while True:
            try:
                # 接收消息
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # 更新連接心跳
                await self.architecture_manager.connection_pool.update_heartbeat(connection.connection_id)
                
                # 處理消息
                await self._handle_message(websocket, connection, session, message)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError as e:
                debug_log(f"JSON 解析錯誤: {e}")
                await self._send_error(websocket, "消息格式錯誤")
            except Exception as e:
                debug_log(f"消息處理錯誤: {e}")
                await self._send_error(websocket, f"處理錯誤: {str(e)}")
    
    async def _handle_message(self, websocket: WebSocket, connection, session: WebFeedbackSession, message: Dict[str, Any]):
        """處理單個 WebSocket 消息"""
        message_type = message.get("type")
        
        try:
            if message_type == "submit_feedback":
                await self._handle_submit_feedback(websocket, connection, session, message)
            
            elif message_type == "run_command":
                await self._handle_run_command(websocket, session, message)
            
            elif message_type == "get_status":
                await self._handle_get_status(websocket, session)
            
            elif message_type == "heartbeat":
                await self._handle_heartbeat(websocket, connection, session, message)
            
            elif message_type == "user_timeout":
                await self._handle_user_timeout(websocket, session, message)
            
            elif message_type == "request_latest_summary":
                await self._handle_latest_summary_request(websocket, connection, session, message)
            
            else:
                debug_log(f"未知的消息類型: {message_type}")
                await self._send_error(websocket, f"未知的消息類型: {message_type}")
                
        except Exception as e:
            debug_log(f"處理消息類型 {message_type} 時發生錯誤: {e}")
            await self._send_error(websocket, f"處理 {message_type} 時發生錯誤")
    
    async def _handle_submit_feedback(self, websocket: WebSocket, connection, session: WebFeedbackSession, message: Dict[str, Any]):
        """處理回饋提交"""
        feedback = message.get("feedback", "")
        images = message.get("images", [])
        settings = message.get("settings", {})
        
        # 提交回饋到會話
        await session.submit_feedback(feedback, images, settings)
        
        # 發布回饋提交事件
        feedback_event = FeedbackSubmittedEvent(
            session_id=session.session_id,
            connection_id=connection.connection_id,
            feedback_data={
                "feedback": feedback,
                "images": images,
                "settings": settings
            },
            has_images=bool(images),
            image_count=len(images)
        )
        await self.architecture_manager.event_bus.publish(feedback_event)
        
        debug_log(f"回饋已提交: 會話 {session.session_id}, 圖片數量: {len(images)}")
    
    async def _handle_run_command(self, websocket: WebSocket, session: WebFeedbackSession, message: Dict[str, Any]):
        """處理命令執行"""
        command = message.get("command", "")
        if command.strip():
            await session.run_command(command)
            debug_log(f"命令已執行: {command}")
    
    async def _handle_get_status(self, websocket: WebSocket, session: WebFeedbackSession):
        """處理狀態查詢"""
        try:
            await websocket.send_json({
                "type": "status_update",
                "status_info": session.get_status_info()
            })
        except Exception as e:
            debug_log(f"發送狀態更新失敗: {e}")
    
    async def _handle_heartbeat(self, websocket: WebSocket, connection, session: WebFeedbackSession, message: Dict[str, Any]):
        """處理心跳消息"""
        tab_id = message.get("tabId", "unknown")
        timestamp = message.get("timestamp", 0)
        
        # 更新標籤頁信息（保持與舊架構的兼容性）
        tab_info = {
            'timestamp': timestamp,
            'last_seen': time.time()
        }
        
        if hasattr(session, 'active_tabs'):
            session.active_tabs[tab_id] = tab_info
        else:
            session.active_tabs = {tab_id: tab_info}
        
        # 發送心跳回應
        try:
            await websocket.send_json({
                "type": "heartbeat_response",
                "tabId": tab_id,
                "timestamp": timestamp
            })
        except Exception as e:
            debug_log(f"發送心跳回應失敗: {e}")
    
    async def _handle_user_timeout(self, websocket: WebSocket, session: WebFeedbackSession, message: Dict[str, Any]):
        """處理用戶超時"""
        debug_log(f"收到用戶超時通知: {session.session_id}")
        
        # 清理會話資源
        await session._cleanup_resources_on_timeout()
        
        # 注意：不再自動停止服務器，保持服務器運行以支援持久性
    
    async def _handle_latest_summary_request(self, websocket: WebSocket, connection, session: WebFeedbackSession, message: Dict[str, Any]):
        """處理最新摘要請求"""
        request_type = message.get("request_type", "manual")
        
        # 發布最新摘要請求事件
        summary_event = LatestSummaryRequestedEvent(
            session_id=session.session_id,
            connection_id=connection.connection_id,
            request_type=request_type
        )
        await self.architecture_manager.event_bus.publish(summary_event)
        
        debug_log(f"最新摘要請求已發布: 會話 {session.session_id}, 類型: {request_type}")
    
    async def _send_error(self, websocket: WebSocket, error_message: str):
        """發送錯誤消息"""
        try:
            await websocket.send_json({
                "type": "error",
                "message": error_message
            })
        except Exception as e:
            debug_log(f"發送錯誤消息失敗: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """獲取 WebSocket 處理器統計信息"""
        return {
            'active_connections': len(self.active_connections),
            'architecture_stats': self.architecture_manager.get_statistics()
        }
