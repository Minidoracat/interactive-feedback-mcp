#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
連接池管理器
============

WebSocket 連接池管理器，提供連接註冊、健康監控、負載均衡等功能。
借鑒參考項目的連接管理策略。
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from enum import Enum
import logging

from fastapi import WebSocket
from .events import EventBus, ConnectionEstablishedEvent, ConnectionClosedEvent, ConnectionErrorEvent
from .state_manager import StateManager, ConnectionState

logger = logging.getLogger(__name__)


class ConnectionStatus(Enum):
    """連接狀態"""
    PENDING = "pending"
    ACTIVE = "active"
    IDLE = "idle"
    UNHEALTHY = "unhealthy"
    CLOSED = "closed"


@dataclass
class WebSocketConnection:
    """WebSocket 連接包裝器"""
    connection_id: str
    websocket: WebSocket
    session_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)
    status: ConnectionStatus = ConnectionStatus.PENDING
    client_info: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_activity(self):
        """更新活動時間"""
        self.last_activity = datetime.now()
    
    def update_heartbeat(self):
        """更新心跳時間"""
        self.last_heartbeat = datetime.now()
        self.update_activity()
    
    def is_stale(self, timeout: int = 60) -> bool:
        """檢查連接是否過期"""
        return (datetime.now() - self.last_heartbeat).total_seconds() > timeout
    
    def get_info(self) -> Dict[str, Any]:
        """獲取連接信息"""
        return {
            'connection_id': self.connection_id,
            'session_id': self.session_id,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat(),
            'last_heartbeat': self.last_heartbeat.isoformat(),
            'client_info': self.client_info,
            'metadata': self.metadata
        }


class HealthMonitor:
    """連接健康監控器"""
    
    def __init__(self, heartbeat_interval: int = 30):
        self.heartbeat_interval = heartbeat_interval
        self.monitoring_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        
        logger.info(f"健康監控器初始化，心跳間隔: {heartbeat_interval}秒")
    
    async def start_monitoring(self, connection: WebSocketConnection):
        """開始監控連接"""
        if connection.connection_id in self.monitoring_tasks:
            await self.stop_monitoring(connection.connection_id)
        
        task = asyncio.create_task(self._monitor_connection(connection))
        self.monitoring_tasks[connection.connection_id] = task
        
        logger.debug(f"開始監控連接: {connection.connection_id}")
    
    async def stop_monitoring(self, connection_id: str):
        """停止監控連接"""
        if connection_id in self.monitoring_tasks:
            task = self.monitoring_tasks[connection_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self.monitoring_tasks[connection_id]
            
            logger.debug(f"停止監控連接: {connection_id}")
    
    async def _monitor_connection(self, connection: WebSocketConnection):
        """監控單個連接"""
        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                # 檢查連接是否過期
                if connection.is_stale(self.heartbeat_interval * 2):
                    logger.warning(f"連接心跳超時: {connection.connection_id}")
                    connection.status = ConnectionStatus.UNHEALTHY
                    break
                
                # 發送心跳檢查
                if connection.websocket and connection.status == ConnectionStatus.ACTIVE:
                    try:
                        await connection.websocket.send_json({
                            "type": "health_check",
                            "timestamp": time.time()
                        })
                    except Exception as e:
                        logger.warning(f"心跳檢查失敗: {connection.connection_id} - {e}")
                        connection.status = ConnectionStatus.UNHEALTHY
                        break
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"連接監控錯誤: {connection.connection_id} - {e}")
                break


class ConnectionPool:
    """WebSocket 連接池管理器"""
    
    def __init__(self, config, event_bus: EventBus, state_manager: StateManager):
        self.config = config
        self.event_bus = event_bus
        self.state_manager = state_manager
        
        # 連接存儲
        self.connections: Dict[str, WebSocketConnection] = {}
        self.session_connections: Dict[str, Set[str]] = {}  # session_id -> connection_ids
        
        # 健康監控
        self.health_monitor = HealthMonitor(config.heartbeat_interval)
        
        # 同步鎖
        self._lock = asyncio.Lock()
        
        logger.info(f"連接池初始化完成，最大連接數: {config.max_connections}")
    
    async def register_connection(self, websocket: WebSocket, session_id: Optional[str] = None,
                                client_info: Dict[str, Any] = None) -> Optional[WebSocketConnection]:
        """
        註冊新連接
        
        Args:
            websocket: WebSocket 連接
            session_id: 關聯的會話 ID
            client_info: 客戶端信息
            
        Returns:
            WebSocketConnection: 連接對象，如果註冊失敗則返回 None
        """
        async with self._lock:
            # 檢查連接數限制
            if len(self.connections) >= self.config.max_connections:
                logger.warning(f"連接數已達上限: {len(self.connections)}/{self.config.max_connections}")
                return None
            
            # 創建連接對象
            connection_id = str(uuid.uuid4())
            connection = WebSocketConnection(
                connection_id=connection_id,
                websocket=websocket,
                session_id=session_id,
                client_info=client_info or {}
            )
            
            # 註冊連接
            self.connections[connection_id] = connection
            
            # 關聯會話
            if session_id:
                if session_id not in self.session_connections:
                    self.session_connections[session_id] = set()
                self.session_connections[session_id].add(connection_id)
            
            # 更新狀態管理器
            await self.state_manager.create_connection_state(
                connection_id, session_id, client_info
            )
            
            # 開始健康監控
            await self.health_monitor.start_monitoring(connection)
            
            # 發布連接建立事件
            event = ConnectionEstablishedEvent(
                connection_id=connection_id,
                session_id=session_id or "",
                client_info=client_info or {}
            )
            await self.event_bus.publish(event)
            
            logger.info(f"連接已註冊: {connection_id} (會話: {session_id})")
            return connection
    
    async def activate_connection(self, connection_id: str):
        """激活連接"""
        async with self._lock:
            if connection_id in self.connections:
                connection = self.connections[connection_id]
                connection.status = ConnectionStatus.ACTIVE
                connection.update_activity()
                
                # 更新狀態管理器
                await self.state_manager.update_connection_state(
                    connection_id, ConnectionState.ACTIVE, "連接激活"
                )
                
                logger.info(f"連接已激活: {connection_id}")
    
    async def unregister_connection(self, connection_id: str, close_code: int = 1000, 
                                  close_reason: str = "正常關閉"):
        """
        註銷連接
        
        Args:
            connection_id: 連接 ID
            close_code: 關閉代碼
            close_reason: 關閉原因
        """
        async with self._lock:
            if connection_id not in self.connections:
                logger.warning(f"嘗試註銷不存在的連接: {connection_id}")
                return
            
            connection = self.connections[connection_id]
            
            # 停止健康監控
            await self.health_monitor.stop_monitoring(connection_id)
            
            # 從會話關聯中移除
            if connection.session_id:
                session_connections = self.session_connections.get(connection.session_id, set())
                session_connections.discard(connection_id)
                if not session_connections:
                    del self.session_connections[connection.session_id]
            
            # 移除連接
            del self.connections[connection_id]
            
            # 更新狀態管理器
            await self.state_manager.remove_connection_state(connection_id)
            
            # 發布連接關閉事件
            event = ConnectionClosedEvent(
                connection_id=connection_id,
                session_id=connection.session_id or "",
                close_code=close_code,
                close_reason=close_reason
            )
            await self.event_bus.publish(event)
            
            logger.info(f"連接已註銷: {connection_id} (原因: {close_reason})")
    
    async def get_connection(self, connection_id: str) -> Optional[WebSocketConnection]:
        """獲取連接"""
        async with self._lock:
            return self.connections.get(connection_id)
    
    async def get_session_connections(self, session_id: str) -> List[WebSocketConnection]:
        """獲取會話的所有連接"""
        async with self._lock:
            connection_ids = self.session_connections.get(session_id, set())
            return [self.connections[cid] for cid in connection_ids if cid in self.connections]
    
    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]):
        """向會話的所有連接廣播消息"""
        connections = await self.get_session_connections(session_id)
        
        if not connections:
            logger.debug(f"會話沒有活躍連接: {session_id}")
            return
        
        failed_connections = []
        
        for connection in connections:
            try:
                await connection.websocket.send_json(message)
                connection.update_activity()
                logger.debug(f"消息已發送到連接: {connection.connection_id}")
            except Exception as e:
                logger.error(f"發送消息失敗: {connection.connection_id} - {e}")
                failed_connections.append(connection.connection_id)
        
        # 清理失敗的連接
        for connection_id in failed_connections:
            await self.unregister_connection(connection_id, 1006, "發送消息失敗")
    
    async def update_heartbeat(self, connection_id: str):
        """更新連接心跳"""
        async with self._lock:
            if connection_id in self.connections:
                connection = self.connections[connection_id]
                connection.update_heartbeat()
                
                # 更新狀態管理器
                await self.state_manager.update_connection_heartbeat(connection_id)
    
    async def cleanup_stale_connections(self):
        """清理過期連接"""
        async with self._lock:
            stale_connections = []
            
            for connection_id, connection in self.connections.items():
                if connection.is_stale(self.config.heartbeat_interval * 2):
                    stale_connections.append(connection_id)
            
            for connection_id in stale_connections:
                await self.unregister_connection(connection_id, 1001, "連接超時")
    
    def get_statistics(self) -> Dict[str, Any]:
        """獲取連接池統計信息"""
        total_connections = len(self.connections)
        active_connections = len([c for c in self.connections.values() 
                                if c.status == ConnectionStatus.ACTIVE])
        
        return {
            'total_connections': total_connections,
            'active_connections': active_connections,
            'max_connections': self.config.max_connections,
            'utilization': total_connections / self.config.max_connections if self.config.max_connections > 0 else 0,
            'sessions_with_connections': len(self.session_connections),
            'monitoring_tasks': len(self.health_monitor.monitoring_tasks)
        }
    
    async def get_connection_list(self) -> List[Dict[str, Any]]:
        """獲取連接列表"""
        async with self._lock:
            return [connection.get_info() for connection in self.connections.values()]
