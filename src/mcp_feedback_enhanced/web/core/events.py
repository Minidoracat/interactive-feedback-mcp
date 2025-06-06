#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
事件系統核心
============

事件驅動架構的核心組件，定義事件類型、事件總線和事件處理器。
借鑒參考項目的事件命名規範和處理模式。
"""

import asyncio
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Type
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """事件優先級"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Event:
    """基礎事件類"""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    priority: EventPriority = EventPriority.NORMAL
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'event_id': self.event_id,
            'event_type': self.__class__.__name__,
            'timestamp': self.timestamp.isoformat(),
            'priority': self.priority.value,
            'source': self.source,
            'metadata': self.metadata
        }


# ==================== 連接相關事件 ====================

@dataclass
class ConnectionEstablishedEvent(Event):
    """WebSocket 連接建立事件 - 借鑒參考項目"""
    connection_id: str = ""
    session_id: str = ""
    client_info: Dict[str, Any] = field(default_factory=dict)
    websocket_url: str = ""


@dataclass
class ConnectionClosedEvent(Event):
    """WebSocket 連接關閉事件"""
    connection_id: str = ""
    session_id: str = ""
    close_code: int = 1000
    close_reason: str = ""


@dataclass
class ConnectionErrorEvent(Event):
    """WebSocket 連接錯誤事件"""
    connection_id: str = ""
    session_id: str = ""
    error_message: str = ""
    error_type: str = ""


# ==================== 會話相關事件 ====================

@dataclass
class SessionCreatedEvent(Event):
    """會話創建事件"""
    session_id: str = ""
    project_directory: str = ""
    summary: str = ""
    timeout: int = 600


@dataclass
class SessionAssignedEvent(Event):
    """會話分配事件 - 借鑒參考項目"""
    session_id: str = ""
    connection_id: str = ""
    assignment_type: str = "new"  # new, reassign, inherit


@dataclass
class SessionUpdatedEvent(Event):
    """會話更新事件"""
    session_id: str = ""
    old_session_id: Optional[str] = None
    update_type: str = "content"  # content, status, metadata
    changes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionTimeoutEvent(Event):
    """會話超時事件"""
    session_id: str = ""
    timeout_duration: int = 0
    last_activity: datetime = field(default_factory=datetime.now)


# ==================== 回饋相關事件 ====================

@dataclass
class FeedbackSubmittedEvent(Event):
    """回饋提交事件 - 借鑒參考項目"""
    session_id: str = ""
    connection_id: str = ""
    feedback_data: Dict[str, Any] = field(default_factory=dict)
    has_images: bool = False
    image_count: int = 0


@dataclass
class FeedbackProcessedEvent(Event):
    """回饋處理完成事件"""
    session_id: str = ""
    processing_time: float = 0.0
    success: bool = True
    result_data: Dict[str, Any] = field(default_factory=dict)


# ==================== 狀態相關事件 ====================

@dataclass
class StateChangedEvent(Event):
    """狀態變更事件"""
    entity_type: str = ""  # session, connection, system
    entity_id: str = ""
    old_state: str = ""
    new_state: str = ""
    reason: str = ""


@dataclass
class LatestSummaryRequestedEvent(Event):
    """最新摘要請求事件 - 借鑒參考項目"""
    session_id: str = ""
    connection_id: str = ""
    request_type: str = "manual"  # manual, auto, refresh


# ==================== 系統相關事件 ====================

@dataclass
class SystemHealthCheckEvent(Event):
    """系統健康檢查事件"""
    component: str = ""
    status: str = "healthy"  # healthy, warning, error
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ErrorEvent(Event):
    """錯誤事件"""
    error_type: str = ""
    error_message: str = ""
    stack_trace: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


# ==================== 事件處理器接口 ====================

class EventHandler(ABC):
    """事件處理器抽象基類"""
    
    @abstractmethod
    async def handle(self, event: Event) -> bool:
        """
        處理事件
        
        Args:
            event: 要處理的事件
            
        Returns:
            bool: 是否成功處理
        """
        pass
    
    @abstractmethod
    def can_handle(self, event_type: Type[Event]) -> bool:
        """
        檢查是否能處理指定類型的事件
        
        Args:
            event_type: 事件類型
            
        Returns:
            bool: 是否能處理
        """
        pass


# ==================== 事件總線 ====================

class EventBus:
    """事件總線 - 事件驅動架構的核心"""
    
    def __init__(self):
        self._handlers: Dict[Type[Event], List[EventHandler]] = {}
        self._middleware: List[Callable] = []
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._event_history: List[Event] = []
        self._max_history = 1000
        
        logger.info("事件總線初始化完成")
    
    def subscribe(self, event_type: Type[Event], handler: EventHandler):
        """
        訂閱事件
        
        Args:
            event_type: 事件類型
            handler: 事件處理器
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        self._handlers[event_type].append(handler)
        logger.info(f"事件處理器已訂閱: {event_type.__name__} -> {handler.__class__.__name__}")
    
    def unsubscribe(self, event_type: Type[Event], handler: EventHandler):
        """
        取消訂閱事件
        
        Args:
            event_type: 事件類型
            handler: 事件處理器
        """
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                logger.info(f"事件處理器已取消訂閱: {event_type.__name__} -> {handler.__class__.__name__}")
            except ValueError:
                logger.warning(f"嘗試取消訂閱不存在的處理器: {event_type.__name__}")
    
    async def publish(self, event: Event):
        """
        發布事件
        
        Args:
            event: 要發布的事件
        """
        # 添加發布時間戳
        if not event.timestamp:
            event.timestamp = datetime.now()
        
        # 添加到事件隊列
        await self._event_queue.put(event)
        
        # 記錄事件歷史
        self._add_to_history(event)
        
        logger.debug(f"事件已發布: {event.__class__.__name__} (ID: {event.event_id})")
    
    async def start(self):
        """啟動事件總線"""
        if self._running:
            logger.warning("事件總線已在運行")
            return
        
        self._running = True
        self._worker_task = asyncio.create_task(self._event_worker())
        logger.info("事件總線已啟動")
    
    async def stop(self):
        """停止事件總線"""
        if not self._running:
            return
        
        self._running = False
        
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        
        logger.info("事件總線已停止")
    
    async def _event_worker(self):
        """事件處理工作線程"""
        while self._running:
            try:
                # 等待事件，設置超時避免無限等待
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self._process_event(event)
            except asyncio.TimeoutError:
                # 超時是正常的，繼續循環
                continue
            except Exception as e:
                logger.error(f"事件處理工作線程錯誤: {e}")
    
    async def _process_event(self, event: Event):
        """
        處理單個事件
        
        Args:
            event: 要處理的事件
        """
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])
        
        if not handlers:
            logger.debug(f"沒有找到事件處理器: {event_type.__name__}")
            return
        
        # 按優先級處理事件
        start_time = time.time()
        
        for handler in handlers:
            try:
                success = await handler.handle(event)
                if not success:
                    logger.warning(f"事件處理失敗: {handler.__class__.__name__} -> {event_type.__name__}")
            except Exception as e:
                logger.error(f"事件處理器異常: {handler.__class__.__name__} -> {e}")
        
        processing_time = time.time() - start_time
        logger.debug(f"事件處理完成: {event_type.__name__} (耗時: {processing_time:.3f}s)")
    
    def _add_to_history(self, event: Event):
        """添加事件到歷史記錄"""
        self._event_history.append(event)
        
        # 限制歷史記錄大小
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]
    
    def get_event_history(self, limit: int = 100) -> List[Event]:
        """
        獲取事件歷史
        
        Args:
            limit: 返回的事件數量限制
            
        Returns:
            List[Event]: 事件歷史列表
        """
        return self._event_history[-limit:]
    
    def get_statistics(self) -> Dict[str, Any]:
        """獲取事件總線統計信息"""
        handler_count = sum(len(handlers) for handlers in self._handlers.values())
        
        return {
            'running': self._running,
            'total_handlers': handler_count,
            'event_types': len(self._handlers),
            'queue_size': self._event_queue.qsize(),
            'history_size': len(self._event_history),
            'registered_events': list(self._handlers.keys())
        }
