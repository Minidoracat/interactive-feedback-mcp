#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理器
==========

統一配置管理器，支援環境變數、配置文件和默認值的層級載入。
借鑒參考項目的配置管理策略。
"""

import os
import json
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class WebConfig:
    """Web 服務配置"""
    # 基礎配置
    port: int = 8765
    host: str = "127.0.0.1"
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    
    # 會話配置
    session_timeout: int = 3600  # 1小時
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_types: List[str] = field(default_factory=lambda: ["jpg", "jpeg", "png", "gif", "webp"])
    
    # 安全配置
    rate_limit_window: int = 900  # 15分鐘
    rate_limit_max: int = 100
    enable_security: bool = True
    
    # 性能配置
    max_connections: int = 100
    heartbeat_interval: int = 30
    connection_timeout: int = 60
    
    # 日誌配置
    log_level: str = "INFO"
    log_format: str = "standard"  # standard, json
    log_file: Optional[str] = None
    
    # 開發配置
    debug_mode: bool = False
    auto_reload: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'port': self.port,
            'host': self.host,
            'cors_origins': self.cors_origins,
            'session_timeout': self.session_timeout,
            'max_file_size': self.max_file_size,
            'allowed_file_types': self.allowed_file_types,
            'rate_limit_window': self.rate_limit_window,
            'rate_limit_max': self.rate_limit_max,
            'enable_security': self.enable_security,
            'max_connections': self.max_connections,
            'heartbeat_interval': self.heartbeat_interval,
            'connection_timeout': self.connection_timeout,
            'log_level': self.log_level,
            'log_format': self.log_format,
            'log_file': self.log_file,
            'debug_mode': self.debug_mode,
            'auto_reload': self.auto_reload
        }


class ConfigManager:
    """統一配置管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config = WebConfig()
        self.config_file = config_file or os.getenv('MCP_CONFIG_FILE', 'config.json')
        self.load_config()
    
    def load_config(self):
        """按優先級載入配置：環境變數 > 配置文件 > 默認值"""
        logger.info("開始載入配置")
        
        # 1. 載入默認配置（已在 WebConfig 中定義）
        logger.debug("使用默認配置")
        
        # 2. 從配置文件載入
        if os.path.exists(self.config_file):
            logger.info(f"從配置文件載入: {self.config_file}")
            self._load_from_file(self.config_file)
        else:
            logger.info(f"配置文件不存在: {self.config_file}")
        
        # 3. 從環境變數載入（最高優先級）
        logger.info("從環境變數載入配置")
        self._load_from_env()
        
        logger.info(f"配置載入完成: {self.config.to_dict()}")
    
    def _load_from_env(self):
        """從環境變數載入配置"""
        env_mappings = {
            # 基礎配置
            'MCP_WEB_PORT': ('port', int),
            'MCP_WEB_HOST': ('host', str),
            
            # 會話配置
            'MCP_SESSION_TIMEOUT': ('session_timeout', int),
            'MCP_MAX_FILE_SIZE': ('max_file_size', int),
            
            # 安全配置
            'MCP_RATE_LIMIT_MAX': ('rate_limit_max', int),
            'MCP_RATE_LIMIT_WINDOW': ('rate_limit_window', int),
            'MCP_ENABLE_SECURITY': ('enable_security', self._parse_bool),
            
            # 性能配置
            'MCP_MAX_CONNECTIONS': ('max_connections', int),
            'MCP_HEARTBEAT_INTERVAL': ('heartbeat_interval', int),
            'MCP_CONNECTION_TIMEOUT': ('connection_timeout', int),
            
            # 日誌配置
            'MCP_LOG_LEVEL': ('log_level', str),
            'MCP_LOG_FORMAT': ('log_format', str),
            'MCP_LOG_FILE': ('log_file', str),
            
            # 開發配置
            'MCP_DEBUG_MODE': ('debug_mode', self._parse_bool),
            'MCP_AUTO_RELOAD': ('auto_reload', self._parse_bool),
        }
        
        for env_key, (attr_name, type_func) in env_mappings.items():
            value = os.getenv(env_key)
            if value is not None:
                try:
                    parsed_value = type_func(value)
                    setattr(self.config, attr_name, parsed_value)
                    logger.debug(f"從環境變數載入: {attr_name} = {parsed_value}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"環境變數 {env_key} 解析失敗: {e}")
        
        # 處理列表類型的環境變數
        cors_origins = os.getenv('MCP_CORS_ORIGINS')
        if cors_origins:
            self.config.cors_origins = [origin.strip() for origin in cors_origins.split(',')]
            logger.debug(f"從環境變數載入 CORS origins: {self.config.cors_origins}")
        
        allowed_types = os.getenv('MCP_ALLOWED_FILE_TYPES')
        if allowed_types:
            self.config.allowed_file_types = [ftype.strip() for ftype in allowed_types.split(',')]
            logger.debug(f"從環境變數載入允許的文件類型: {self.config.allowed_file_types}")
    
    def _load_from_file(self, config_file: str):
        """從配置文件載入配置"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 更新配置對象
            for key, value in config_data.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                    logger.debug(f"從配置文件載入: {key} = {value}")
                else:
                    logger.warning(f"未知的配置項: {key}")
                    
        except (FileNotFoundError, json.JSONDecodeError, PermissionError) as e:
            logger.error(f"載入配置文件失敗: {e}")
    
    def _parse_bool(self, value: str) -> bool:
        """解析布林值"""
        return value.lower() in ('true', '1', 'yes', 'on', 'enabled')
    
    def save_config(self, config_file: Optional[str] = None):
        """保存配置到文件"""
        target_file = config_file or self.config_file
        
        try:
            config_dict = self.config.to_dict()
            with open(target_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            logger.info(f"配置已保存到: {target_file}")
        except Exception as e:
            logger.error(f"保存配置文件失敗: {e}")
    
    def get_config(self) -> WebConfig:
        """獲取配置對象"""
        return self.config
    
    def update_config(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"配置已更新: {key} = {value}")
            else:
                logger.warning(f"嘗試更新未知配置項: {key}")
    
    def validate_config(self) -> bool:
        """驗證配置的有效性"""
        errors = []
        
        # 驗證端口範圍
        if not (1 <= self.config.port <= 65535):
            errors.append(f"端口號無效: {self.config.port}")
        
        # 驗證文件大小
        if self.config.max_file_size <= 0:
            errors.append(f"最大文件大小無效: {self.config.max_file_size}")
        
        # 驗證超時設置
        if self.config.session_timeout <= 0:
            errors.append(f"會話超時時間無效: {self.config.session_timeout}")
        
        # 驗證連接數限制
        if self.config.max_connections <= 0:
            errors.append(f"最大連接數無效: {self.config.max_connections}")
        
        # 驗證日誌級別
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.config.log_level.upper() not in valid_log_levels:
            errors.append(f"日誌級別無效: {self.config.log_level}")
        
        if errors:
            for error in errors:
                logger.error(f"配置驗證失敗: {error}")
            return False
        
        logger.info("配置驗證通過")
        return True
