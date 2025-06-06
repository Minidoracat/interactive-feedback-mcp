#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
架構管理器
==========

事件驅動架構的統一管理器，負責初始化、配置和協調所有核心組件。
提供簡單的 API 來啟動和管理整個事件驅動系統。
"""

import asyncio
import logging
from typing import Optional, Dict, Any

from .config_manager import ConfigManager, WebConfig
from .security_manager import SecurityManager
from .port_manager import PortManager
from .events import EventBus
from .state_manager import StateManager
from .connection_pool import ConnectionPool
from .event_handlers import (
    ConnectionEventHandler, SessionEventHandler, FeedbackEventHandler,
    StateChangeEventHandler, SystemEventHandler
)

logger = logging.getLogger(__name__)


class ArchitectureManager:
    """事件驅動架構統一管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化架構管理器
        
        Args:
            config_file: 配置文件路徑（可選）
        """
        # 基礎設施組件
        self.config_manager = ConfigManager(config_file)
        self.config = self.config_manager.get_config()
        self.security_manager = SecurityManager(self.config)
        self.port_manager = PortManager()
        
        # 核心架構組件
        self.event_bus = EventBus()
        self.state_manager = StateManager(self.config, self.event_bus)
        self.connection_pool = ConnectionPool(self.config, self.event_bus, self.state_manager)
        
        # 事件處理器
        self._setup_event_handlers()
        
        # 運行狀態
        self._running = False
        self._startup_tasks = []
        
        logger.info("架構管理器初始化完成")
    
    def _setup_event_handlers(self):
        """設置事件處理器"""
        # 創建事件處理器
        connection_handler = ConnectionEventHandler(self.state_manager, self.connection_pool)
        session_handler = SessionEventHandler(self.state_manager, self.connection_pool)
        feedback_handler = FeedbackEventHandler(self.state_manager, self.connection_pool)
        state_change_handler = StateChangeEventHandler(self.connection_pool)
        system_handler = SystemEventHandler()
        
        # 註冊事件處理器
        from .events import (
            ConnectionEstablishedEvent, ConnectionClosedEvent, ConnectionErrorEvent,
            SessionCreatedEvent, SessionAssignedEvent, SessionUpdatedEvent, SessionTimeoutEvent,
            FeedbackSubmittedEvent, FeedbackProcessedEvent, LatestSummaryRequestedEvent,
            StateChangedEvent, SystemHealthCheckEvent, ErrorEvent
        )
        
        # 連接事件
        self.event_bus.subscribe(ConnectionEstablishedEvent, connection_handler)
        self.event_bus.subscribe(ConnectionClosedEvent, connection_handler)
        self.event_bus.subscribe(ConnectionErrorEvent, connection_handler)
        
        # 會話事件
        self.event_bus.subscribe(SessionCreatedEvent, session_handler)
        self.event_bus.subscribe(SessionAssignedEvent, session_handler)
        self.event_bus.subscribe(SessionUpdatedEvent, session_handler)
        self.event_bus.subscribe(SessionTimeoutEvent, session_handler)
        
        # 回饋事件
        self.event_bus.subscribe(FeedbackSubmittedEvent, feedback_handler)
        self.event_bus.subscribe(FeedbackProcessedEvent, feedback_handler)
        self.event_bus.subscribe(LatestSummaryRequestedEvent, feedback_handler)
        
        # 狀態變更事件
        self.event_bus.subscribe(StateChangedEvent, state_change_handler)
        
        # 系統事件
        self.event_bus.subscribe(SystemHealthCheckEvent, system_handler)
        self.event_bus.subscribe(ErrorEvent, system_handler)
        
        logger.info("事件處理器設置完成")
    
    async def start(self):
        """啟動架構管理器"""
        if self._running:
            logger.warning("架構管理器已在運行")
            return
        
        logger.info("正在啟動事件驅動架構...")
        
        try:
            # 驗證配置
            if not self.config_manager.validate_config():
                raise RuntimeError("配置驗證失敗")
            
            # 啟動事件總線
            await self.event_bus.start()
            
            # 啟動狀態管理器
            await self.state_manager.start()
            
            # 標記為運行狀態
            self._running = True
            
            logger.info("事件驅動架構啟動成功")
            
        except Exception as e:
            logger.error(f"架構啟動失敗: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """停止架構管理器"""
        if not self._running:
            return
        
        logger.info("正在停止事件驅動架構...")
        
        try:
            # 停止狀態管理器
            await self.state_manager.stop()
            
            # 停止事件總線
            await self.event_bus.stop()
            
            # 標記為停止狀態
            self._running = False
            
            logger.info("事件驅動架構已停止")
            
        except Exception as e:
            logger.error(f"架構停止時發生錯誤: {e}")
    
    def is_running(self) -> bool:
        """檢查架構是否在運行"""
        return self._running
    
    async def find_available_port(self, preferred_port: int = None) -> int:
        """查找可用端口"""
        port = preferred_port or self.config.port
        return await self.port_manager.find_available_port(port)
    
    def check_rate_limit(self, client_id: str) -> bool:
        """檢查速率限制"""
        return self.security_manager.check_rate_limit(client_id)
    
    def validate_file(self, file_data: bytes, filename: str) -> tuple[bool, str]:
        """驗證文件上傳"""
        return self.security_manager.validate_file(file_data, filename)
    
    def sanitize_text(self, text: str) -> str:
        """清理文本輸入"""
        return self.security_manager.sanitize_text(text)
    
    def generate_session_id(self) -> str:
        """生成安全的會話 ID"""
        return self.security_manager.generate_session_id()
    
    async def create_session(self, session_id: str, project_directory: str, 
                           summary: str, timeout: int = None):
        """創建新會話"""
        timeout = timeout or self.config.session_timeout
        
        # 發布會話創建事件
        from .events import SessionCreatedEvent
        event = SessionCreatedEvent(
            session_id=session_id,
            project_directory=project_directory,
            summary=summary,
            timeout=timeout
        )
        await self.event_bus.publish(event)
        
        logger.info(f"會話創建事件已發布: {session_id}")
    
    async def register_websocket_connection(self, websocket, session_id: str = None, 
                                          client_info: Dict[str, Any] = None):
        """註冊 WebSocket 連接"""
        return await self.connection_pool.register_connection(websocket, session_id, client_info)
    
    async def unregister_websocket_connection(self, connection_id: str, 
                                            close_code: int = 1000, close_reason: str = "正常關閉"):
        """註銷 WebSocket 連接"""
        await self.connection_pool.unregister_connection(connection_id, close_code, close_reason)
    
    async def broadcast_to_session(self, session_id: str, message: Dict[str, Any]):
        """向會話廣播消息"""
        await self.connection_pool.broadcast_to_session(session_id, message)
    
    async def submit_feedback(self, session_id: str, connection_id: str, 
                            feedback_data: Dict[str, Any]):
        """提交回饋"""
        # 發布回饋提交事件
        from .events import FeedbackSubmittedEvent
        event = FeedbackSubmittedEvent(
            session_id=session_id,
            connection_id=connection_id,
            feedback_data=feedback_data,
            has_images=bool(feedback_data.get('images')),
            image_count=len(feedback_data.get('images', []))
        )
        await self.event_bus.publish(event)
        
        logger.info(f"回饋提交事件已發布: {session_id}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """獲取架構統計信息"""
        return {
            'running': self._running,
            'config': self.config.to_dict(),
            'event_bus': self.event_bus.get_statistics(),
            'state_manager': self.state_manager.get_statistics(),
            'connection_pool': self.connection_pool.get_statistics(),
            'port_manager': {
                'allocated_ports': self.port_manager.get_allocated_ports()
            }
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """健康檢查"""
        health_status = {
            'status': 'healthy',
            'components': {
                'architecture_manager': 'healthy' if self._running else 'stopped',
                'event_bus': 'healthy' if self.event_bus._running else 'stopped',
                'state_manager': 'healthy' if self.state_manager._running else 'stopped',
                'connection_pool': 'healthy',
                'config_manager': 'healthy',
                'security_manager': 'healthy',
                'port_manager': 'healthy'
            },
            'statistics': self.get_statistics()
        }
        
        # 檢查是否有組件不健康
        unhealthy_components = [
            name for name, status in health_status['components'].items() 
            if status != 'healthy'
        ]
        
        if unhealthy_components:
            health_status['status'] = 'degraded'
            health_status['issues'] = unhealthy_components
        
        # 發布健康檢查事件
        from .events import SystemHealthCheckEvent
        event = SystemHealthCheckEvent(
            component='architecture_manager',
            status=health_status['status'],
            metrics=health_status['statistics']
        )
        await self.event_bus.publish(event)
        
        return health_status
    
    async def __aenter__(self):
        """異步上下文管理器入口"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """異步上下文管理器出口"""
        await self.stop()


# 全局架構管理器實例
_architecture_manager: Optional[ArchitectureManager] = None


def get_architecture_manager(config_file: Optional[str] = None) -> ArchitectureManager:
    """獲取架構管理器實例（單例模式）"""
    global _architecture_manager
    if _architecture_manager is None:
        _architecture_manager = ArchitectureManager(config_file)
    return _architecture_manager


async def initialize_architecture(config_file: Optional[str] = None) -> ArchitectureManager:
    """初始化並啟動事件驅動架構"""
    manager = get_architecture_manager(config_file)
    await manager.start()
    return manager


async def shutdown_architecture():
    """關閉事件驅動架構"""
    global _architecture_manager
    if _architecture_manager:
        await _architecture_manager.stop()
        _architecture_manager = None
