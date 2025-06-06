#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主要路由處理
============

設置 Web UI 的主要路由和處理邏輯。
"""

import json
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse

from ...debug import web_debug_log as debug_log
from ... import __version__

if TYPE_CHECKING:
    from ..main import WebUIManager


def load_user_layout_settings() -> str:
    """載入用戶的佈局模式設定"""
    try:
        # 使用與 GUI 版本相同的設定檔案路徑
        config_dir = Path.home() / ".config" / "mcp-feedback-enhanced"
        settings_file = config_dir / "ui_settings.json"

        if settings_file.exists():
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                layout_mode = settings.get('layoutMode', 'separate')
                debug_log(f"從設定檔案載入佈局模式: {layout_mode}")
                return layout_mode
        else:
            debug_log("設定檔案不存在，使用預設佈局模式: separate")
            return 'separate'
    except Exception as e:
        debug_log(f"載入佈局設定失敗: {e}，使用預設佈局模式: separate")
        return 'separate'


def setup_routes(manager: 'WebUIManager'):
    """設置路由"""

    @manager.app.get("/", response_class=HTMLResponse)
    async def index(request: Request):
        """統一回饋頁面 - 重構後的主頁面"""
        # 獲取當前活躍會話
        current_session = manager.get_current_session()

        if not current_session:
            # 沒有活躍會話時顯示等待頁面
            return manager.templates.TemplateResponse("index.html", {
                "request": request,
                "title": "MCP Feedback Enhanced",
                "has_session": False,
                "version": __version__
            })

        # 有活躍會話時顯示回饋頁面
        # 載入用戶的佈局模式設定
        layout_mode = load_user_layout_settings()

        return manager.templates.TemplateResponse("feedback.html", {
            "request": request,
            "project_directory": current_session.project_directory,
            "summary": current_session.summary,
            "title": "Interactive Feedback - 回饋收集",
            "version": __version__,
            "has_session": True,
            "layout_mode": layout_mode,
            "i18n": manager.i18n
        })

    @manager.app.get("/api/translations")
    async def get_translations():
        """獲取翻譯數據 - 從 Web 專用翻譯檔案載入"""
        translations = {}
        
        # 獲取 Web 翻譯檔案目錄
        web_locales_dir = Path(__file__).parent.parent / "locales"
        supported_languages = ["zh-TW", "zh-CN", "en"]
        
        for lang_code in supported_languages:
            lang_dir = web_locales_dir / lang_code
            translation_file = lang_dir / "translation.json"
            
            try:
                if translation_file.exists():
                    with open(translation_file, 'r', encoding='utf-8') as f:
                        lang_data = json.load(f)
                        translations[lang_code] = lang_data
                        debug_log(f"成功載入 Web 翻譯: {lang_code}")
                else:
                    debug_log(f"Web 翻譯檔案不存在: {translation_file}")
                    translations[lang_code] = {}
            except Exception as e:
                debug_log(f"載入 Web 翻譯檔案失敗 {lang_code}: {e}")
                translations[lang_code] = {}
        
        debug_log(f"Web 翻譯 API 返回 {len(translations)} 種語言的數據")
        return JSONResponse(content=translations)

    @manager.app.get("/api/session-status")
    async def get_session_status():
        """獲取當前會話狀態"""
        current_session = manager.get_current_session()

        if not current_session:
            return JSONResponse(content={
                "has_session": False,
                "status": "no_session",
                "message": "沒有活躍會話"
            })

        return JSONResponse(content={
            "has_session": True,
            "status": "active",
            "session_info": {
                "project_directory": current_session.project_directory,
                "summary": current_session.summary,
                "feedback_completed": current_session.feedback_completed.is_set()
            }
        })

    @manager.app.get("/api/current-session")
    async def get_current_session():
        """獲取當前會話詳細信息"""
        current_session = manager.get_current_session()

        if not current_session:
            return JSONResponse(
                status_code=404,
                content={"error": "沒有活躍會話"}
            )

        return JSONResponse(content={
            "project_directory": current_session.project_directory,
            "summary": current_session.summary,
            "feedback_completed": current_session.feedback_completed.is_set(),
            "command_logs": current_session.command_logs,
            "images_count": len(current_session.images)
        })

    # 🗑️ 傳統 WebSocket 端點已移除，請使用事件驅動端點 /ws/v2
    # 參見 event_driven_routes.py 中的實現

    @manager.app.post("/api/save-settings")
    async def save_settings(request: Request):
        """保存設定到檔案"""
        try:
            data = await request.json()

            # 使用與 GUI 版本相同的設定檔案路徑
            config_dir = Path.home() / ".config" / "mcp-feedback-enhanced"
            config_dir.mkdir(parents=True, exist_ok=True)
            settings_file = config_dir / "ui_settings.json"

            # 保存設定到檔案
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            debug_log(f"設定已保存到: {settings_file}")

            return JSONResponse(content={"status": "success", "message": "設定已保存"})

        except Exception as e:
            debug_log(f"保存設定失敗: {e}")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": f"保存失敗: {str(e)}"}
            )

    @manager.app.get("/api/load-settings")
    async def load_settings():
        """從檔案載入設定"""
        try:
            # 使用與 GUI 版本相同的設定檔案路徑
            config_dir = Path.home() / ".config" / "mcp-feedback-enhanced"
            settings_file = config_dir / "ui_settings.json"

            if settings_file.exists():
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)

                debug_log(f"設定已從檔案載入: {settings_file}")
                return JSONResponse(content=settings)
            else:
                debug_log("設定檔案不存在，返回空設定")
                return JSONResponse(content={})

        except Exception as e:
            debug_log(f"載入設定失敗: {e}")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": f"載入失敗: {str(e)}"}
            )

    @manager.app.post("/api/clear-settings")
    async def clear_settings():
        """清除設定檔案"""
        try:
            # 使用與 GUI 版本相同的設定檔案路徑
            config_dir = Path.home() / ".config" / "mcp-feedback-enhanced"
            settings_file = config_dir / "ui_settings.json"

            if settings_file.exists():
                settings_file.unlink()
                debug_log(f"設定檔案已刪除: {settings_file}")
            else:
                debug_log("設定檔案不存在，無需刪除")

            return JSONResponse(content={"status": "success", "message": "設定已清除"})

        except Exception as e:
            debug_log(f"清除設定失敗: {e}")
            return JSONResponse(
                status_code=500,
                content={"status": "error", "message": f"清除失敗: {str(e)}"}
            )

    @manager.app.get("/api/active-tabs")
    async def get_active_tabs():
        """獲取活躍標籤頁信息 - 優先使用全局狀態"""
        current_time = time.time()
        expired_threshold = 60

        # 清理過期的全局標籤頁
        valid_global_tabs = {}
        for tab_id, tab_info in manager.global_active_tabs.items():
            if current_time - tab_info.get('last_seen', 0) <= expired_threshold:
                valid_global_tabs[tab_id] = tab_info

        manager.global_active_tabs = valid_global_tabs

        # 如果有當前會話，也更新會話的標籤頁狀態
        current_session = manager.get_current_session()
        if current_session:
            # 合併會話標籤頁到全局（如果有的話）
            session_tabs = getattr(current_session, 'active_tabs', {})
            for tab_id, tab_info in session_tabs.items():
                if current_time - tab_info.get('last_seen', 0) <= expired_threshold:
                    valid_global_tabs[tab_id] = tab_info

            # 更新會話的活躍標籤頁
            current_session.active_tabs = valid_global_tabs.copy()
            manager.global_active_tabs = valid_global_tabs

        return JSONResponse(content={
            "has_session": current_session is not None,
            "active_tabs": valid_global_tabs,
            "count": len(valid_global_tabs)
        })

    @manager.app.post("/api/register-tab")
    async def register_tab(request: Request):
        """註冊新標籤頁"""
        try:
            data = await request.json()
            tab_id = data.get("tabId")

            if not tab_id:
                return JSONResponse(
                    status_code=400,
                    content={"error": "缺少 tabId"}
                )

            current_session = manager.get_current_session()
            if not current_session:
                return JSONResponse(
                    status_code=404,
                    content={"error": "沒有活躍會話"}
                )

            # 註冊標籤頁
            tab_info = {
                'timestamp': time.time() * 1000,  # 毫秒時間戳
                'last_seen': time.time(),
                'registered_at': time.time()
            }

            if not hasattr(current_session, 'active_tabs'):
                current_session.active_tabs = {}

            current_session.active_tabs[tab_id] = tab_info

            # 同時更新全局標籤頁狀態
            manager.global_active_tabs[tab_id] = tab_info

            debug_log(f"標籤頁已註冊: {tab_id}")

            return JSONResponse(content={
                "status": "success",
                "tabId": tab_id,
                "registered": True
            })

        except Exception as e:
            debug_log(f"註冊標籤頁失敗: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": f"註冊失敗: {str(e)}"}
            )


    # 🗑️ 傳統 WebSocket 消息處理函數已移除
    # 事件驅動消息處理請參見 websocket_handler.py