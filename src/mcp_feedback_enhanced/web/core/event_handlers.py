#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件處理器
==========

具體的事件處理器實現，處理各種系統事件。
包括連接事件、會話事件、狀態變更事件等的處理邏輯。
"""

import asyncio
import logging
from typing import Type, Dict, Any

from .events import (
    Event, EventHandler, 
    ConnectionEstablishedEvent, ConnectionClosedEvent, ConnectionErrorEvent,
    SessionCreatedEvent, SessionAssignedEvent, SessionUpdatedEvent, SessionTimeoutEvent,
    FeedbackSubmittedEvent, FeedbackProcessedEvent,
    StateChangedEvent, LatestSummaryRequestedEvent,
    SystemHealthCheckEvent, ErrorEvent
)
from .state_manager import StateManager, SessionState, ConnectionState
from .connection_pool import ConnectionPool

logger = logging.getLogger(__name__)


class ConnectionEventHandler(EventHandler):
    """連接事件處理器"""
    
    def __init__(self, state_manager: StateManager, connection_pool: ConnectionPool):
        self.state_manager = state_manager
        self.connection_pool = connection_pool
    
    def can_handle(self, event_type: Type[Event]) -> bool:
        """檢查是否能處理指定類型的事件"""
        return event_type in [
            ConnectionEstablishedEvent,
            ConnectionClosedEvent,
            ConnectionErrorEvent
        ]
    
    async def handle(self, event: Event) -> bool:
        """處理連接相關事件"""
        try:
            if isinstance(event, ConnectionEstablishedEvent):
                return await self._handle_connection_established(event)
            elif isinstance(event, ConnectionClosedEvent):
                return await self._handle_connection_closed(event)
            elif isinstance(event, ConnectionErrorEvent):
                return await self._handle_connection_error(event)
            
            return False
        except Exception as e:
            logger.error(f"連接事件處理失敗: {e}")
            return False
    
    async def _handle_connection_established(self, event: ConnectionEstablishedEvent) -> bool:
        """處理連接建立事件"""
        logger.info(f"處理連接建立事件: {event.connection_id}")
        
        # 更新連接狀態為已連接
        await self.state_manager.update_connection_state(
            event.connection_id, 
            ConnectionState.CONNECTED,
            "WebSocket 連接建立"
        )
        
        # 如果有關聯會話，更新會話狀態
        if event.session_id:
            await self.state_manager.update_session_state(
                event.session_id,
                SessionState.ACTIVE,
                "WebSocket 連接建立"
            )
        
        return True
    
    async def _handle_connection_closed(self, event: ConnectionClosedEvent) -> bool:
        """處理連接關閉事件"""
        logger.info(f"處理連接關閉事件: {event.connection_id} (代碼: {event.close_code})")
        
        # 更新連接狀態為已斷開
        await self.state_manager.update_connection_state(
            event.connection_id,
            ConnectionState.DISCONNECTED,
            f"連接關閉: {event.close_reason}"
        )
        
        # 如果有關聯會話，檢查是否還有其他連接
        if event.session_id:
            session_connections = await self.connection_pool.get_session_connections(event.session_id)
            if not session_connections:
                # 沒有其他連接，將會話狀態設為等待
                await self.state_manager.update_session_state(
                    event.session_id,
                    SessionState.WAITING,
                    "所有連接已斷開"
                )
        
        return True
    
    async def _handle_connection_error(self, event: ConnectionErrorEvent) -> bool:
        """處理連接錯誤事件"""
        logger.error(f"處理連接錯誤事件: {event.connection_id} - {event.error_message}")
        
        # 更新連接狀態為錯誤
        await self.state_manager.update_connection_state(
            event.connection_id,
            ConnectionState.ERROR,
            f"連接錯誤: {event.error_message}"
        )
        
        return True


class SessionEventHandler(EventHandler):
    """會話事件處理器"""
    
    def __init__(self, state_manager: StateManager, connection_pool: ConnectionPool):
        self.state_manager = state_manager
        self.connection_pool = connection_pool
    
    def can_handle(self, event_type: Type[Event]) -> bool:
        """檢查是否能處理指定類型的事件"""
        return event_type in [
            SessionCreatedEvent,
            SessionAssignedEvent,
            SessionUpdatedEvent,
            SessionTimeoutEvent
        ]
    
    async def handle(self, event: Event) -> bool:
        """處理會話相關事件"""
        try:
            if isinstance(event, SessionCreatedEvent):
                return await self._handle_session_created(event)
            elif isinstance(event, SessionAssignedEvent):
                return await self._handle_session_assigned(event)
            elif isinstance(event, SessionUpdatedEvent):
                return await self._handle_session_updated(event)
            elif isinstance(event, SessionTimeoutEvent):
                return await self._handle_session_timeout(event)
            
            return False
        except Exception as e:
            logger.error(f"會話事件處理失敗: {e}")
            return False
    
    async def _handle_session_created(self, event: SessionCreatedEvent) -> bool:
        """處理會話創建事件"""
        logger.info(f"處理會話創建事件: {event.session_id}")
        
        # 創建會話狀態
        await self.state_manager.create_session_state(
            event.session_id,
            event.project_directory,
            event.summary,
            event.timeout
        )
        
        return True
    
    async def _handle_session_assigned(self, event: SessionAssignedEvent) -> bool:
        """處理會話分配事件"""
        logger.info(f"處理會話分配事件: {event.session_id} -> {event.connection_id}")
        
        # 更新連接的會話關聯
        connection = await self.connection_pool.get_connection(event.connection_id)
        if connection:
            connection.session_id = event.session_id
            
            # 更新連接狀態
            await self.state_manager.update_connection_state(
                event.connection_id,
                ConnectionState.AUTHENTICATED,
                f"分配到會話: {event.session_id}"
            )
        
        return True
    
    async def _handle_session_updated(self, event: SessionUpdatedEvent) -> bool:
        """處理會話更新事件"""
        logger.info(f"處理會話更新事件: {event.session_id}")
        
        # 向會話的所有連接廣播更新通知
        message = {
            "type": "session_updated",
            "session_id": event.session_id,
            "update_type": event.update_type,
            "changes": event.changes,
            "timestamp": event.timestamp.isoformat()
        }
        
        await self.connection_pool.broadcast_to_session(event.session_id, message)
        
        return True
    
    async def _handle_session_timeout(self, event: SessionTimeoutEvent) -> bool:
        """處理會話超時事件"""
        logger.warning(f"處理會話超時事件: {event.session_id}")
        
        # 更新會話狀態為超時
        await self.state_manager.update_session_state(
            event.session_id,
            SessionState.TIMEOUT,
            f"會話超時: {event.timeout_duration}秒"
        )
        
        # 通知所有相關連接
        message = {
            "type": "session_timeout",
            "session_id": event.session_id,
            "timeout_duration": event.timeout_duration,
            "message": "會話已超時，請重新開始"
        }
        
        await self.connection_pool.broadcast_to_session(event.session_id, message)
        
        return True


class FeedbackEventHandler(EventHandler):
    """回饋事件處理器"""
    
    def __init__(self, state_manager: StateManager, connection_pool: ConnectionPool):
        self.state_manager = state_manager
        self.connection_pool = connection_pool
    
    def can_handle(self, event_type: Type[Event]) -> bool:
        """檢查是否能處理指定類型的事件"""
        return event_type in [
            FeedbackSubmittedEvent,
            FeedbackProcessedEvent,
            LatestSummaryRequestedEvent
        ]
    
    async def handle(self, event: Event) -> bool:
        """處理回饋相關事件"""
        try:
            if isinstance(event, FeedbackSubmittedEvent):
                return await self._handle_feedback_submitted(event)
            elif isinstance(event, FeedbackProcessedEvent):
                return await self._handle_feedback_processed(event)
            elif isinstance(event, LatestSummaryRequestedEvent):
                return await self._handle_latest_summary_requested(event)
            
            return False
        except Exception as e:
            logger.error(f"回饋事件處理失敗: {e}")
            return False
    
    async def _handle_feedback_submitted(self, event: FeedbackSubmittedEvent) -> bool:
        """處理回饋提交事件"""
        logger.info(f"處理回饋提交事件: {event.session_id}")
        
        # 更新會話狀態
        await self.state_manager.update_session_state(
            event.session_id,
            SessionState.FEEDBACK_SUBMITTED,
            f"回饋已提交 (圖片: {event.image_count})"
        )
        
        # 向所有連接廣播回饋已收到
        message = {
            "type": "feedback_received",
            "session_id": event.session_id,
            "has_images": event.has_images,
            "image_count": event.image_count,
            "message": "回饋已成功提交"
        }
        
        await self.connection_pool.broadcast_to_session(event.session_id, message)
        
        return True
    
    async def _handle_feedback_processed(self, event: FeedbackProcessedEvent) -> bool:
        """處理回饋處理完成事件"""
        logger.info(f"處理回饋處理完成事件: {event.session_id}")
        
        # 更新會話狀態
        new_state = SessionState.COMPLETED if event.success else SessionState.ERROR
        await self.state_manager.update_session_state(
            event.session_id,
            new_state,
            f"回饋處理{'成功' if event.success else '失敗'} (耗時: {event.processing_time:.2f}s)"
        )
        
        return True
    
    async def _handle_latest_summary_requested(self, event: LatestSummaryRequestedEvent) -> bool:
        """處理最新摘要請求事件"""
        logger.info(f"處理最新摘要請求事件: {event.session_id}")
        
        # 獲取會話狀態
        session_state = await self.state_manager.get_session_state(event.session_id)
        if not session_state:
            return False
        
        # 發送最新摘要
        message = {
            "type": "latest_summary",
            "session_id": event.session_id,
            "summary": session_state.summary,
            "project_directory": session_state.project_directory,
            "request_type": event.request_type
        }
        
        # 如果指定了連接 ID，只發送給該連接
        if event.connection_id:
            connection = await self.connection_pool.get_connection(event.connection_id)
            if connection:
                try:
                    await connection.websocket.send_json(message)
                except Exception as e:
                    logger.error(f"發送最新摘要失敗: {e}")
                    return False
        else:
            # 廣播給會話的所有連接
            await self.connection_pool.broadcast_to_session(event.session_id, message)
        
        return True


class StateChangeEventHandler(EventHandler):
    """狀態變更事件處理器"""
    
    def __init__(self, connection_pool: ConnectionPool):
        self.connection_pool = connection_pool
    
    def can_handle(self, event_type: Type[Event]) -> bool:
        """檢查是否能處理指定類型的事件"""
        return event_type == StateChangedEvent
    
    async def handle(self, event: Event) -> bool:
        """處理狀態變更事件"""
        if not isinstance(event, StateChangedEvent):
            return False
        
        try:
            logger.debug(f"處理狀態變更事件: {event.entity_type} {event.entity_id} "
                        f"{event.old_state} -> {event.new_state}")
            
            # 如果是會話狀態變更，通知相關連接
            if event.entity_type == "session":
                message = {
                    "type": "state_changed",
                    "entity_type": event.entity_type,
                    "entity_id": event.entity_id,
                    "old_state": event.old_state,
                    "new_state": event.new_state,
                    "reason": event.reason,
                    "timestamp": event.timestamp.isoformat()
                }
                
                await self.connection_pool.broadcast_to_session(event.entity_id, message)
            
            return True
        except Exception as e:
            logger.error(f"狀態變更事件處理失敗: {e}")
            return False


class SystemEventHandler(EventHandler):
    """系統事件處理器"""
    
    def __init__(self):
        pass
    
    def can_handle(self, event_type: Type[Event]) -> bool:
        """檢查是否能處理指定類型的事件"""
        return event_type in [SystemHealthCheckEvent, ErrorEvent]
    
    async def handle(self, event: Event) -> bool:
        """處理系統相關事件"""
        try:
            if isinstance(event, SystemHealthCheckEvent):
                return await self._handle_health_check(event)
            elif isinstance(event, ErrorEvent):
                return await self._handle_error(event)
            
            return False
        except Exception as e:
            logger.error(f"系統事件處理失敗: {e}")
            return False
    
    async def _handle_health_check(self, event: SystemHealthCheckEvent) -> bool:
        """處理健康檢查事件"""
        logger.debug(f"健康檢查: {event.component} - {event.status}")
        
        # 這裡可以添加健康檢查的具體邏輯
        # 例如記錄到監控系統、發送告警等
        
        return True
    
    async def _handle_error(self, event: ErrorEvent) -> bool:
        """處理錯誤事件"""
        logger.error(f"系統錯誤: {event.error_type} - {event.error_message}")
        
        # 這裡可以添加錯誤處理的具體邏輯
        # 例如發送告警、記錄到錯誤追蹤系統等
        
        return True
