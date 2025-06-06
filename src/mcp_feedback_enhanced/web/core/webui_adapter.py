#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WebUI 適配器
============

事件驅動架構與現有 WebUIManager 的適配器。
負責將現有的 WebUIManager 功能遷移到事件驅動架構。
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from .architecture_manager import ArchitectureManager, get_architecture_manager
from .websocket_handler import WebSocketHandler
from .events import SessionCreatedEvent, SessionUpdatedEvent
from ..models.feedback_session import WebFeedbackSession, SessionStatus
from ...debug import web_debug_log as debug_log

logger = logging.getLogger(__name__)


class EventDrivenWebUIAdapter:
    """事件驅動 WebUI 適配器"""
    
    def __init__(self, webui_manager):
        """
        初始化適配器
        
        Args:
            webui_manager: 現有的 WebUIManager 實例
        """
        self.webui_manager = webui_manager
        self.architecture_manager: Optional[ArchitectureManager] = None
        self.websocket_handler: Optional[WebSocketHandler] = None
        self._initialized = False
        
        logger.info("EventDrivenWebUIAdapter 初始化完成")
    
    async def initialize(self):
        """初始化事件驅動架構"""
        if self._initialized:
            return
        
        try:
            # 獲取或創建架構管理器
            self.architecture_manager = get_architecture_manager()
            
            # 啟動事件驅動架構
            await self.architecture_manager.start()
            
            # 創建 WebSocket 處理器
            self.websocket_handler = WebSocketHandler(self.architecture_manager)
            
            self._initialized = True
            debug_log("✅ 事件驅動架構已初始化")
            
        except Exception as e:
            logger.error(f"初始化事件驅動架構失敗: {e}")
            raise
    
    async def shutdown(self):
        """關閉事件驅動架構"""
        if not self._initialized:
            return
        
        try:
            if self.architecture_manager:
                await self.architecture_manager.stop()
            
            self._initialized = False
            debug_log("✅ 事件驅動架構已關閉")
            
        except Exception as e:
            logger.error(f"關閉事件驅動架構失敗: {e}")
    
    async def create_session(self, project_directory: str, summary: str, timeout: int = 600) -> str:
        """
        創建會話（事件驅動版本）
        
        Args:
            project_directory: 項目目錄
            summary: AI 工作摘要
            timeout: 超時時間
            
        Returns:
            str: 會話 ID
        """
        if not self._initialized:
            await self.initialize()
        
        # 生成安全的會話 ID
        session_id = self.architecture_manager.generate_session_id()
        
        # 創建會話到事件驅動架構
        await self.architecture_manager.create_session(
            session_id, project_directory, summary, timeout
        )
        
        # 創建傳統會話對象（保持兼容性）
        session = WebFeedbackSession(session_id, project_directory, summary)
        session.update_status(SessionStatus.WAITING, "等待 WebSocket 連接")
        
        # 更新 WebUIManager 的當前會話
        self.webui_manager.current_session = session
        self.webui_manager.sessions[session_id] = session
        
        # 設置待更新標記（保持與舊架構的兼容性）
        self.webui_manager._pending_session_update = True
        
        # 添加待更新數據到狀態管理器
        await self.architecture_manager.state_manager.add_pending_update(
            session_id, {
                'type': 'session_created',
                'project_directory': project_directory,
                'summary': summary,
                'session_id': session_id
            }
        )
        
        debug_log(f"✅ 事件驅動會話已創建: {session_id}")
        return session_id
    
    async def handle_websocket_connection(self, websocket, session: WebFeedbackSession):
        """
        處理 WebSocket 連接（事件驅動版本）
        
        Args:
            websocket: WebSocket 連接
            session: 會話對象
        """
        if not self._initialized:
            await self.initialize()
        
        if not self.websocket_handler:
            raise RuntimeError("WebSocket 處理器未初始化")
        
        # 使用事件驅動的 WebSocket 處理器
        await self.websocket_handler.handle_websocket_connection(websocket, session)
    
    async def update_session(self, session_id: str, old_session_id: Optional[str] = None, 
                           changes: Dict[str, Any] = None):
        """
        更新會話（事件驅動版本）
        
        Args:
            session_id: 新會話 ID
            old_session_id: 舊會話 ID（可選）
            changes: 變更內容
        """
        if not self._initialized:
            await self.initialize()
        
        # 發布會話更新事件
        update_event = SessionUpdatedEvent(
            session_id=session_id,
            old_session_id=old_session_id,
            update_type="content",
            changes=changes or {}
        )
        await self.architecture_manager.event_bus.publish(update_event)
        
        debug_log(f"✅ 會話更新事件已發布: {session_id}")
    
    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]):
        """
        向會話廣播消息（事件驅動版本）
        
        Args:
            session_id: 會話 ID
            message: 消息內容
        """
        if not self._initialized:
            await self.initialize()
        
        await self.architecture_manager.broadcast_to_session(session_id, message)
    
    async def submit_feedback(self, session_id: str, feedback_data: Dict[str, Any]):
        """
        提交回饋（事件驅動版本）
        
        Args:
            session_id: 會話 ID
            feedback_data: 回饋數據
        """
        if not self._initialized:
            await self.initialize()
        
        # 獲取連接 ID（如果有的話）
        connections = await self.architecture_manager.connection_pool.get_session_connections(session_id)
        connection_id = connections[0].connection_id if connections else "unknown"
        
        await self.architecture_manager.submit_feedback(session_id, connection_id, feedback_data)
    
    def get_current_session(self) -> Optional[WebFeedbackSession]:
        """獲取當前會話（保持兼容性）"""
        return self.webui_manager.current_session
    
    def get_session(self, session_id: str) -> Optional[WebFeedbackSession]:
        """獲取指定會話（保持兼容性）"""
        return self.webui_manager.sessions.get(session_id)
    
    async def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        if not self._initialized:
            return {
                'status': 'not_initialized',
                'architecture_manager': False,
                'websocket_handler': False
            }
        
        # 獲取架構管理器的健康狀態
        arch_health = await self.architecture_manager.health_check()
        
        return {
            'status': 'healthy' if self._initialized else 'unhealthy',
            'architecture_manager': arch_health,
            'websocket_handler': self.websocket_handler is not None,
            'webui_manager': {
                'current_session': self.webui_manager.current_session is not None,
                'total_sessions': len(self.webui_manager.sessions),
                'global_tabs': len(self.webui_manager.global_active_tabs)
            }
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """獲取統計信息"""
        stats = {
            'initialized': self._initialized,
            'webui_manager': {
                'current_session': self.webui_manager.current_session.session_id if self.webui_manager.current_session else None,
                'total_sessions': len(self.webui_manager.sessions),
                'global_tabs': len(self.webui_manager.global_active_tabs),
                'pending_update': getattr(self.webui_manager, '_pending_session_update', False)
            }
        }
        
        if self._initialized and self.architecture_manager:
            stats['architecture_manager'] = self.architecture_manager.get_statistics()
        
        if self.websocket_handler:
            stats['websocket_handler'] = self.websocket_handler.get_statistics()
        
        return stats


# 全局適配器實例
_adapter: Optional[EventDrivenWebUIAdapter] = None


def get_webui_adapter(webui_manager=None) -> EventDrivenWebUIAdapter:
    """
    獲取 WebUI 適配器實例（單例模式）
    
    Args:
        webui_manager: WebUIManager 實例（首次調用時需要）
        
    Returns:
        EventDrivenWebUIAdapter: 適配器實例
    """
    global _adapter
    if _adapter is None:
        if webui_manager is None:
            raise ValueError("首次調用時需要提供 webui_manager 參數")
        _adapter = EventDrivenWebUIAdapter(webui_manager)
    return _adapter


async def initialize_webui_adapter(webui_manager) -> EventDrivenWebUIAdapter:
    """
    初始化 WebUI 適配器
    
    Args:
        webui_manager: WebUIManager 實例
        
    Returns:
        EventDrivenWebUIAdapter: 初始化後的適配器
    """
    adapter = get_webui_adapter(webui_manager)
    await adapter.initialize()
    return adapter


async def shutdown_webui_adapter():
    """關閉 WebUI 適配器"""
    global _adapter
    if _adapter:
        await _adapter.shutdown()
        _adapter = None
