#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
端口管理器
==========

智能端口管理器，借鑒參考項目的端口管理策略。
提供端口檢測、分配、衝突處理和進程清理功能。
"""

import asyncio
import socket
import psutil
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class PortManager:
    """智能端口管理器 - 借鑒參考項目"""
    
    def __init__(self):
        self.preferred_ports = [8765, 8766, 8767, 8768, 8769]
        self.cleanup_enabled = True
        self._allocated_ports: List[int] = []
    
    async def find_available_port(self, preferred_port: int = 8765) -> int:
        """
        智能端口檢測
        
        Args:
            preferred_port: 首選端口號
            
        Returns:
            int: 可用的端口號
        """
        logger.info(f"開始尋找可用端口，首選端口: {preferred_port}")
        
        # 首先嘗試首選端口
        if await self.is_port_available(preferred_port):
            logger.info(f"首選端口 {preferred_port} 可用")
            self._allocated_ports.append(preferred_port)
            return preferred_port
        
        logger.warning(f"首選端口 {preferred_port} 不可用，嘗試預定義端口列表")
        
        # 嘗試預定義端口列表
        for port in self.preferred_ports:
            if await self.is_port_available(port):
                logger.info(f"找到可用端口: {port}")
                self._allocated_ports.append(port)
                return port
        
        # 動態分配端口
        logger.info("預定義端口都不可用，開始動態分配")
        dynamic_port = await self.get_dynamic_port()
        self._allocated_ports.append(dynamic_port)
        return dynamic_port
    
    async def is_port_available(self, port: int) -> bool:
        """
        檢查端口是否可用
        
        Args:
            port: 要檢查的端口號
            
        Returns:
            bool: 端口是否可用
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind(('127.0.0.1', port))
                return True
        except OSError as e:
            logger.debug(f"端口 {port} 不可用: {e}")
            return False
    
    async def get_dynamic_port(self) -> int:
        """
        獲取動態分配的端口
        
        Returns:
            int: 動態分配的端口號
        """
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', 0))
            port = s.getsockname()[1]
            logger.info(f"動態分配端口: {port}")
            return port
    
    async def cleanup_port_processes(self, port: int) -> bool:
        """
        清理占用端口的進程
        
        Args:
            port: 要清理的端口號
            
        Returns:
            bool: 是否成功清理
        """
        if not self.cleanup_enabled:
            logger.info("端口清理功能已禁用")
            return False
        
        logger.info(f"開始清理端口 {port} 的占用進程")
        
        try:
            killed_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'connections']):
                try:
                    connections = proc.info.get('connections') or []
                    for conn in connections:
                        if hasattr(conn, 'laddr') and conn.laddr.port == port:
                            logger.warning(f"發現占用端口 {port} 的進程: PID={proc.pid}, Name={proc.info['name']}")
                            proc.terminate()
                            killed_processes.append(proc.pid)
                            
                            # 等待進程正常終止
                            await asyncio.sleep(1)
                            
                            # 如果進程仍在運行，強制終止
                            if proc.is_running():
                                logger.warning(f"強制終止進程 PID={proc.pid}")
                                proc.kill()
                                
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # 忽略無法訪問的進程
                    continue
            
            if killed_processes:
                logger.info(f"已清理進程: {killed_processes}")
                return True
            else:
                logger.info(f"端口 {port} 沒有發現占用進程")
                return False
                
        except Exception as e:
            logger.error(f"清理端口 {port} 時發生錯誤: {e}")
            return False
    
    def release_port(self, port: int):
        """
        釋放已分配的端口
        
        Args:
            port: 要釋放的端口號
        """
        if port in self._allocated_ports:
            self._allocated_ports.remove(port)
            logger.info(f"已釋放端口: {port}")
    
    def get_allocated_ports(self) -> List[int]:
        """
        獲取已分配的端口列表
        
        Returns:
            List[int]: 已分配的端口列表
        """
        return self._allocated_ports.copy()
    
    async def check_port_health(self, port: int) -> bool:
        """
        檢查端口健康狀態
        
        Args:
            port: 要檢查的端口號
            
        Returns:
            bool: 端口是否健康
        """
        try:
            # 嘗試連接到端口
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection('127.0.0.1', port),
                timeout=5.0
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception as e:
            logger.debug(f"端口 {port} 健康檢查失敗: {e}")
            return False
    
    def enable_cleanup(self, enabled: bool = True):
        """
        啟用或禁用端口清理功能
        
        Args:
            enabled: 是否啟用清理功能
        """
        self.cleanup_enabled = enabled
        logger.info(f"端口清理功能已{'啟用' if enabled else '禁用'}")
