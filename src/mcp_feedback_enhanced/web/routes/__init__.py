#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web UI 路由模組
==============

提供 Web UI 的路由設置和處理。
"""

from .main_routes import setup_routes
from .event_driven_routes import setup_event_driven_routes

__all__ = ['setup_routes', 'setup_event_driven_routes']