#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
狀態管理器
==========

統一狀態管理器，管理會話狀態、連接狀態和系統狀態。
支援狀態變更通知、狀態持久化和狀態同步。
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from enum import Enum
import logging

from .events import Event, EventBus, StateChangedEvent, SessionTimeoutEvent

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """會話狀態枚舉"""
    CREATED = "created"
    WAITING = "waiting"
    ACTIVE = "active"
    FEEDBACK_SUBMITTED = "feedback_submitted"
    PROCESSING = "processing"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    ERROR = "error"
    CLEANUP = "cleanup"


class ConnectionState(Enum):
    """連接狀態枚舉"""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    ACTIVE = "active"
    IDLE = "idle"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class SessionStateInfo:
    """會話狀態信息"""
    session_id: str
    state: SessionState
    created_at: datetime
    last_updated: datetime
    last_activity: datetime
    project_directory: str = ""
    summary: str = ""
    timeout: int = 600
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self, timeout_seconds: int = None) -> bool:
        """檢查會話是否過期"""
        timeout = timeout_seconds or self.timeout
        return (datetime.now() - self.last_activity).total_seconds() > timeout
    
    def update_activity(self):
        """更新活動時間"""
        self.last_activity = datetime.now()
        self.last_updated = datetime.now()


@dataclass
class ConnectionStateInfo:
    """連接狀態信息"""
    connection_id: str
    state: ConnectionState
    session_id: Optional[str]
    created_at: datetime
    last_updated: datetime
    last_heartbeat: datetime
    client_info: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_stale(self, heartbeat_timeout: int = 60) -> bool:
        """檢查連接是否過期"""
        return (datetime.now() - self.last_heartbeat).total_seconds() > heartbeat_timeout
    
    def update_heartbeat(self):
        """更新心跳時間"""
        self.last_heartbeat = datetime.now()
        self.last_updated = datetime.now()


class StateManager:
    """統一狀態管理器"""
    
    def __init__(self, config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        
        # 狀態存儲
        self._session_states: Dict[str, SessionStateInfo] = {}
        self._connection_states: Dict[str, ConnectionStateInfo] = {}
        self._pending_updates: Dict[str, List[Dict]] = {}
        
        # 同步鎖
        self._session_lock = asyncio.Lock()
        self._connection_lock = asyncio.Lock()
        
        # 清理任務
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
        logger.info("狀態管理器初始化完成")
    
    async def start(self):
        """啟動狀態管理器"""
        if self._running:
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_states())
        logger.info("狀態管理器已啟動")
    
    async def stop(self):
        """停止狀態管理器"""
        if not self._running:
            return
        
        self._running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("狀態管理器已停止")
    
    # ==================== 會話狀態管理 ====================
    
    async def create_session_state(self, session_id: str, project_directory: str, 
                                 summary: str, timeout: int = 600) -> SessionStateInfo:
        """創建會話狀態"""
        async with self._session_lock:
            now = datetime.now()
            state_info = SessionStateInfo(
                session_id=session_id,
                state=SessionState.CREATED,
                created_at=now,
                last_updated=now,
                last_activity=now,
                project_directory=project_directory,
                summary=summary,
                timeout=timeout
            )
            
            self._session_states[session_id] = state_info
            logger.info(f"會話狀態已創建: {session_id}")
            
            # 發布狀態變更事件
            await self._publish_state_change("session", session_id, "", "created", "會話創建")
            
            return state_info
    
    async def update_session_state(self, session_id: str, new_state: SessionState, 
                                 reason: str = "", metadata: Dict[str, Any] = None):
        """更新會話狀態"""
        async with self._session_lock:
            if session_id not in self._session_states:
                logger.warning(f"嘗試更新不存在的會話狀態: {session_id}")
                return
            
            state_info = self._session_states[session_id]
            old_state = state_info.state
            
            state_info.state = new_state
            state_info.last_updated = datetime.now()
            state_info.update_activity()
            
            if metadata:
                state_info.metadata.update(metadata)
            
            logger.info(f"會話狀態已更新: {session_id} {old_state.value} -> {new_state.value}")
            
            # 發布狀態變更事件
            await self._publish_state_change("session", session_id, old_state.value, 
                                           new_state.value, reason)
    
    async def get_session_state(self, session_id: str) -> Optional[SessionStateInfo]:
        """獲取會話狀態"""
        async with self._session_lock:
            return self._session_states.get(session_id)
    
    async def remove_session_state(self, session_id: str):
        """移除會話狀態"""
        async with self._session_lock:
            if session_id in self._session_states:
                del self._session_states[session_id]
                logger.info(f"會話狀態已移除: {session_id}")
                
                # 清理相關的待更新數據
                if session_id in self._pending_updates:
                    del self._pending_updates[session_id]
    
    async def get_active_sessions(self) -> List[SessionStateInfo]:
        """獲取活躍會話列表"""
        async with self._session_lock:
            active_states = [
                SessionState.WAITING, SessionState.ACTIVE, 
                SessionState.FEEDBACK_SUBMITTED, SessionState.PROCESSING
            ]
            return [
                state for state in self._session_states.values()
                if state.state in active_states
            ]
    
    # ==================== 連接狀態管理 ====================
    
    async def create_connection_state(self, connection_id: str, session_id: Optional[str] = None,
                                    client_info: Dict[str, Any] = None) -> ConnectionStateInfo:
        """創建連接狀態"""
        async with self._connection_lock:
            now = datetime.now()
            state_info = ConnectionStateInfo(
                connection_id=connection_id,
                state=ConnectionState.CONNECTING,
                session_id=session_id,
                created_at=now,
                last_updated=now,
                last_heartbeat=now,
                client_info=client_info or {}
            )
            
            self._connection_states[connection_id] = state_info
            logger.info(f"連接狀態已創建: {connection_id}")
            
            # 發布狀態變更事件
            await self._publish_state_change("connection", connection_id, "", "connecting", "連接創建")
            
            return state_info
    
    async def update_connection_state(self, connection_id: str, new_state: ConnectionState,
                                    reason: str = "", metadata: Dict[str, Any] = None):
        """更新連接狀態"""
        async with self._connection_lock:
            if connection_id not in self._connection_states:
                logger.warning(f"嘗試更新不存在的連接狀態: {connection_id}")
                return
            
            state_info = self._connection_states[connection_id]
            old_state = state_info.state
            
            state_info.state = new_state
            state_info.last_updated = datetime.now()
            
            if metadata:
                state_info.metadata.update(metadata)
            
            logger.info(f"連接狀態已更新: {connection_id} {old_state.value} -> {new_state.value}")
            
            # 發布狀態變更事件
            await self._publish_state_change("connection", connection_id, old_state.value,
                                           new_state.value, reason)
    
    async def update_connection_heartbeat(self, connection_id: str):
        """更新連接心跳"""
        async with self._connection_lock:
            if connection_id in self._connection_states:
                self._connection_states[connection_id].update_heartbeat()
    
    async def get_connection_state(self, connection_id: str) -> Optional[ConnectionStateInfo]:
        """獲取連接狀態"""
        async with self._connection_lock:
            return self._connection_states.get(connection_id)
    
    async def remove_connection_state(self, connection_id: str):
        """移除連接狀態"""
        async with self._connection_lock:
            if connection_id in self._connection_states:
                del self._connection_states[connection_id]
                logger.info(f"連接狀態已移除: {connection_id}")
    
    async def get_active_connections(self) -> List[ConnectionStateInfo]:
        """獲取活躍連接列表"""
        async with self._connection_lock:
            active_states = [
                ConnectionState.CONNECTED, ConnectionState.AUTHENTICATED, 
                ConnectionState.ACTIVE, ConnectionState.IDLE
            ]
            return [
                state for state in self._connection_states.values()
                if state.state in active_states
            ]
    
    # ==================== 待更新管理 ====================
    
    async def add_pending_update(self, session_id: str, update_data: Dict[str, Any]):
        """添加待更新數據"""
        if session_id not in self._pending_updates:
            self._pending_updates[session_id] = []
        
        self._pending_updates[session_id].append({
            'timestamp': datetime.now(),
            'data': update_data
        })
        
        logger.debug(f"已添加待更新數據: {session_id}")
    
    async def get_pending_updates(self, session_id: str) -> List[Dict[str, Any]]:
        """獲取待更新數據"""
        return self._pending_updates.get(session_id, [])
    
    async def clear_pending_updates(self, session_id: str):
        """清理待更新數據"""
        if session_id in self._pending_updates:
            del self._pending_updates[session_id]
            logger.debug(f"已清理待更新數據: {session_id}")
    
    # ==================== 清理和維護 ====================
    
    async def _cleanup_expired_states(self):
        """定時清理過期狀態 - 借鑒參考項目"""
        while self._running:
            try:
                await asyncio.sleep(300)  # 每5分鐘檢查一次
                await self._cleanup_expired_sessions()
                await self._cleanup_stale_connections()
            except Exception as e:
                logger.error(f"狀態清理任務錯誤: {e}")
    
    async def _cleanup_expired_sessions(self):
        """清理過期會話"""
        async with self._session_lock:
            expired_sessions = []
            
            for session_id, state in self._session_states.items():
                if state.is_expired(self.config.session_timeout):
                    expired_sessions.append(session_id)
                    
                    # 發布超時事件
                    timeout_event = SessionTimeoutEvent(
                        session_id=session_id,
                        timeout_duration=self.config.session_timeout,
                        last_activity=state.last_activity
                    )
                    await self.event_bus.publish(timeout_event)
            
            for session_id in expired_sessions:
                del self._session_states[session_id]
                if session_id in self._pending_updates:
                    del self._pending_updates[session_id]
                logger.info(f"已清理過期會話: {session_id}")
    
    async def _cleanup_stale_connections(self):
        """清理過期連接"""
        async with self._connection_lock:
            stale_connections = []
            
            for connection_id, state in self._connection_states.items():
                if state.is_stale(self.config.heartbeat_interval * 2):
                    stale_connections.append(connection_id)
            
            for connection_id in stale_connections:
                del self._connection_states[connection_id]
                logger.info(f"已清理過期連接: {connection_id}")
    
    async def _publish_state_change(self, entity_type: str, entity_id: str, 
                                  old_state: str, new_state: str, reason: str):
        """發布狀態變更事件"""
        event = StateChangedEvent(
            entity_type=entity_type,
            entity_id=entity_id,
            old_state=old_state,
            new_state=new_state,
            reason=reason
        )
        await self.event_bus.publish(event)
    
    # ==================== 統計和監控 ====================
    
    def get_statistics(self) -> Dict[str, Any]:
        """獲取狀態管理器統計信息"""
        return {
            'running': self._running,
            'session_count': len(self._session_states),
            'connection_count': len(self._connection_states),
            'pending_updates_count': sum(len(updates) for updates in self._pending_updates.values()),
            'active_sessions': len([s for s in self._session_states.values() 
                                  if s.state in [SessionState.WAITING, SessionState.ACTIVE]]),
            'active_connections': len([c for c in self._connection_states.values() 
                                     if c.state in [ConnectionState.CONNECTED, ConnectionState.ACTIVE]])
        }
