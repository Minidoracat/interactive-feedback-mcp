#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安全管理器
==========

提供速率限制、輸入驗證、會話安全等功能。
借鑒參考項目的安全策略。
"""

import time
import hashlib
import secrets
import re
from typing import Dict, List, Optional, Set
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """速率限制器"""
    
    def __init__(self, window_size: int = 900, max_requests: int = 100):
        """
        初始化速率限制器
        
        Args:
            window_size: 時間窗口大小（秒）
            max_requests: 最大請求數
        """
        self.window_size = window_size
        self.max_requests = max_requests
        self.requests = defaultdict(deque)
        self._blocked_clients: Set[str] = set()
        
        logger.info(f"速率限制器初始化: 窗口={window_size}秒, 最大請求={max_requests}")
    
    def is_allowed(self, client_id: str) -> bool:
        """
        檢查是否允許請求
        
        Args:
            client_id: 客戶端標識
            
        Returns:
            bool: 是否允許請求
        """
        # 檢查是否被永久封鎖
        if client_id in self._blocked_clients:
            logger.warning(f"客戶端 {client_id} 已被封鎖")
            return False
        
        now = time.time()
        client_requests = self.requests[client_id]
        
        # 清理過期請求
        while client_requests and client_requests[0] < now - self.window_size:
            client_requests.popleft()
        
        # 檢查是否超過限制
        if len(client_requests) >= self.max_requests:
            logger.warning(f"客戶端 {client_id} 超過速率限制: {len(client_requests)}/{self.max_requests}")
            return False
        
        # 記錄新請求
        client_requests.append(now)
        return True
    
    def block_client(self, client_id: str):
        """封鎖客戶端"""
        self._blocked_clients.add(client_id)
        logger.warning(f"客戶端 {client_id} 已被封鎖")
    
    def unblock_client(self, client_id: str):
        """解除封鎖客戶端"""
        self._blocked_clients.discard(client_id)
        logger.info(f"客戶端 {client_id} 已解除封鎖")
    
    def get_remaining_requests(self, client_id: str) -> int:
        """獲取剩餘請求數"""
        now = time.time()
        client_requests = self.requests[client_id]
        
        # 清理過期請求
        while client_requests and client_requests[0] < now - self.window_size:
            client_requests.popleft()
        
        return max(0, self.max_requests - len(client_requests))


class InputValidator:
    """輸入驗證器"""
    
    def __init__(self):
        self.allowed_file_types = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.max_text_length = 10000  # 最大文本長度
        
        # 危險字符模式
        self.dangerous_patterns = [
            r'<script[^>]*>.*?</script>',  # JavaScript
            r'javascript:',  # JavaScript URL
            r'on\w+\s*=',  # 事件處理器
            r'<iframe[^>]*>.*?</iframe>',  # iframe
            r'<object[^>]*>.*?</object>',  # object
            r'<embed[^>]*>.*?</embed>',  # embed
        ]
        
        logger.info("輸入驗證器初始化完成")
    
    def validate_file_upload(self, file_data: bytes, filename: str) -> tuple[bool, str]:
        """
        驗證文件上傳
        
        Args:
            file_data: 文件數據
            filename: 文件名
            
        Returns:
            tuple[bool, str]: (是否有效, 錯誤信息)
        """
        # 檢查文件大小
        if len(file_data) > self.max_file_size:
            return False, f"文件大小超過限制: {len(file_data)} > {self.max_file_size}"
        
        # 檢查文件名
        if not filename or len(filename) > 255:
            return False, "文件名無效"
        
        # 檢查文件類型
        file_ext = filename.lower().split('.')[-1] if '.' in filename else ''
        if file_ext not in self.allowed_file_types:
            return False, f"不支援的文件類型: {file_ext}"
        
        # 檢查文件頭（簡單的 MIME 類型檢查）
        if not self._check_file_header(file_data, file_ext):
            return False, "文件格式驗證失敗"
        
        return True, ""
    
    def _check_file_header(self, data: bytes, ext: str) -> bool:
        """檢查文件頭部"""
        if not data:
            return False
        
        # JPEG
        if ext in ['jpg', 'jpeg'] and data.startswith(b'\xff\xd8\xff'):
            return True
        # PNG
        if ext == 'png' and data.startswith(b'\x89PNG\r\n\x1a\n'):
            return True
        # GIF
        if ext == 'gif' and (data.startswith(b'GIF87a') or data.startswith(b'GIF89a')):
            return True
        # WebP
        if ext == 'webp' and b'WEBP' in data[:12]:
            return True
        
        return False
    
    def validate_text_input(self, text: str) -> tuple[bool, str]:
        """
        驗證文本輸入
        
        Args:
            text: 輸入文本
            
        Returns:
            tuple[bool, str]: (是否有效, 錯誤信息)
        """
        if not isinstance(text, str):
            return False, "輸入必須是字符串"
        
        # 檢查長度
        if len(text) > self.max_text_length:
            return False, f"文本長度超過限制: {len(text)} > {self.max_text_length}"
        
        # 檢查危險模式
        for pattern in self.dangerous_patterns:
            if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
                return False, f"檢測到潛在的安全威脅"
        
        return True, ""
    
    def sanitize_text(self, text: str) -> str:
        """
        清理文本輸入
        
        Args:
            text: 原始文本
            
        Returns:
            str: 清理後的文本
        """
        if not isinstance(text, str):
            return ""
        
        # 移除潛在的 XSS 內容
        dangerous_chars = ['<', '>', '"', "'", '&']
        for char in dangerous_chars:
            text = text.replace(char, '')
        
        # 移除控制字符
        text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
        
        return text.strip()
    
    def validate_session_id(self, session_id: str) -> bool:
        """
        驗證會話 ID 格式
        
        Args:
            session_id: 會話 ID
            
        Returns:
            bool: 是否有效
        """
        if not session_id:
            return False
        
        # 檢查格式：feedback_timestamp_randompart
        pattern = r'^feedback_\d+_[a-f0-9]{16}$'
        return bool(re.match(pattern, session_id))


class SecurityManager:
    """安全管理器"""
    
    def __init__(self, config):
        """
        初始化安全管理器
        
        Args:
            config: 配置對象
        """
        self.config = config
        self.rate_limiter = RateLimiter(
            window_size=config.rate_limit_window,
            max_requests=config.rate_limit_max
        )
        self.input_validator = InputValidator()
        self._session_secrets: Dict[str, str] = {}
        
        logger.info("安全管理器初始化完成")
    
    def check_rate_limit(self, client_id: str) -> bool:
        """檢查速率限制"""
        if not self.config.enable_security:
            return True
        return self.rate_limiter.is_allowed(client_id)
    
    def validate_file(self, file_data: bytes, filename: str) -> tuple[bool, str]:
        """驗證文件"""
        return self.input_validator.validate_file_upload(file_data, filename)
    
    def validate_text(self, text: str) -> tuple[bool, str]:
        """驗證文本"""
        return self.input_validator.validate_text_input(text)
    
    def sanitize_text(self, text: str) -> str:
        """清理文本輸入"""
        return self.input_validator.sanitize_text(text)
    
    def generate_session_id(self) -> str:
        """生成安全的會話 ID"""
        timestamp = int(time.time())
        random_part = secrets.token_hex(8)
        session_id = f"feedback_{timestamp}_{random_part}"
        
        # 生成會話密鑰
        session_secret = secrets.token_hex(32)
        self._session_secrets[session_id] = session_secret
        
        logger.info(f"生成新會話 ID: {session_id}")
        return session_id
    
    def validate_session(self, session_id: str) -> bool:
        """驗證會話"""
        if not self.input_validator.validate_session_id(session_id):
            return False
        
        return session_id in self._session_secrets
    
    def get_session_secret(self, session_id: str) -> Optional[str]:
        """獲取會話密鑰"""
        return self._session_secrets.get(session_id)
    
    def revoke_session(self, session_id: str):
        """撤銷會話"""
        if session_id in self._session_secrets:
            del self._session_secrets[session_id]
            logger.info(f"會話已撤銷: {session_id}")
    
    def get_client_id(self, request_info: dict) -> str:
        """生成客戶端 ID"""
        # 使用 IP 地址和 User-Agent 生成客戶端 ID
        ip = request_info.get('client_ip', 'unknown')
        user_agent = request_info.get('user_agent', 'unknown')
        
        client_string = f"{ip}:{user_agent}"
        return hashlib.sha256(client_string.encode()).hexdigest()[:16]
