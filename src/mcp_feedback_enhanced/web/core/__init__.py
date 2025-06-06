#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
核心架構模組
============

事件驅動架構的核心組件，包括：
- 端口管理器
- 配置管理器
- 安全管理器
- 事件系統
- 狀態管理器
- 連接池
- 事件處理器
"""

from .port_manager import PortManager
from .config_manager import ConfigManager, WebConfig
from .security_manager import SecurityManager, RateLimiter, InputValidator
from .events import EventBus, Event, EventHandler, EventPriority
from .state_manager import StateManager, SessionState, ConnectionState, SessionStateInfo, ConnectionStateInfo
from .connection_pool import ConnectionPool, WebSocketConnection, HealthMonitor
from .event_handlers import (
    ConnectionEventHandler, SessionEventHandler, FeedbackEventHandler,
    StateChangeEventHandler, SystemEventHandler
)
from .architecture_manager import ArchitectureManager, get_architecture_manager, initialize_architecture, shutdown_architecture

__all__ = [
    # 基礎設施
    'PortManager',
    'ConfigManager',
    'WebConfig',
    'SecurityManager',
    'RateLimiter',
    'InputValidator',

    # 事件系統
    'EventBus',
    'Event',
    'EventHandler',
    'EventPriority',

    # 狀態管理
    'StateManager',
    'SessionState',
    'ConnectionState',
    'SessionStateInfo',
    'ConnectionStateInfo',

    # 連接池
    'ConnectionPool',
    'WebSocketConnection',
    'HealthMonitor',

    # 事件處理器
    'ConnectionEventHandler',
    'SessionEventHandler',
    'FeedbackEventHandler',
    'StateChangeEventHandler',
    'SystemEventHandler',

    # 架構管理器
    'ArchitectureManager',
    'get_architecture_manager',
    'initialize_architecture',
    'shutdown_architecture'
]
