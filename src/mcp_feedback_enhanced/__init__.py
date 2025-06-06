#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Interactive Feedback Enhanced
==================================

互動式用戶回饋 MCP 伺服器，提供 AI 輔助開發中的回饋收集功能。

作者: Fábio Ferreira
增強功能: Web UI 支援、圖片上傳、現代化界面設計

特色：
- Web UI 介面支援
- 智慧環境檢測
- 命令執行功能
- 圖片上傳支援
- 現代化深色主題
- 重構的模組化架構
"""

__version__ = "2.2.5"
__author__ = "Minidoracat"
__email__ = "minidora0702@gmail.com"

import os

from .server import main as run_server

# 導入新的 Web UI 模組
from .web import WebUIManager, launch_web_feedback_ui, get_web_ui_manager, stop_web_ui

# 主要導出介面
__all__ = [
    "run_server",
    "WebUIManager",
    "launch_web_feedback_ui",
    "get_web_ui_manager",
    "stop_web_ui",
    "__version__",
    "__author__",
]

def main():
    """主要入口點，用於 uvx 執行"""
    from .__main__ import main as cli_main
    return cli_main() 