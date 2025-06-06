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
            "layout_mode": layout_mode
        })

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

    @manager.app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """WebSocket 端點 - 重構後移除 session_id 依賴"""
        # 獲取當前活躍會話
        session = manager.get_current_session()
        if not session:
            await websocket.close(code=4004, reason="沒有活躍會話")
            return

        await websocket.accept()
        session.websocket = websocket

        debug_log(f"WebSocket 連接建立: 當前活躍會話")

        # 發送連接成功消息
        try:
            await websocket.send_json({
                "type": "connection_established",
                "message": "WebSocket 連接已建立"
            })

            # 檢查是否有待發送的會話更新
            if getattr(manager, '_pending_session_update', False):
                debug_log("檢測到待發送的會話更新，準備發送通知")
                await websocket.send_json({
                    "type": "session_updated",
                    "message": "新會話已創建，正在更新頁面內容",
                    "session_info": {
                        "project_directory": session.project_directory,
                        "summary": session.summary,
                        "session_id": session.session_id
                    }
                })
                manager._pending_session_update = False
                debug_log("✅ 已發送會話更新通知到前端")
            else:
                # 發送當前會話狀態
                await websocket.send_json({
                    "type": "status_update",
                    "status_info": session.get_status_info()
                })
                debug_log("已發送當前會話狀態到前端")

        except Exception as e:
            debug_log(f"發送連接確認失敗: {e}")

        try:
            while True:
                data = await websocket.receive_text()
                message = json.loads(data)
                await handle_websocket_message(manager, session, message)

        except WebSocketDisconnect:
            debug_log(f"WebSocket 連接正常斷開")
        except ConnectionResetError:
            debug_log(f"WebSocket 連接被重置")
        except Exception as e:
            debug_log(f"WebSocket 錯誤: {e}")
        finally:
            # 安全清理 WebSocket 連接
            if session.websocket == websocket:
                session.websocket = None
                debug_log("已清理會話中的 WebSocket 連接")

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


async def handle_websocket_message(manager: 'WebUIManager', session, data: dict):
    """處理 WebSocket 消息"""
    message_type = data.get("type")

    if message_type == "submit_feedback":
        # 提交回饋
        feedback = data.get("feedback", "")
        images = data.get("images", [])
        settings = data.get("settings", {})
        await session.submit_feedback(feedback, images, settings)

    elif message_type == "run_command":
        # 執行命令
        command = data.get("command", "")
        if command.strip():
            await session.run_command(command)

    elif message_type == "get_status":
        # 獲取會話狀態
        if session.websocket:
            try:
                await session.websocket.send_json({
                    "type": "status_update",
                    "status_info": session.get_status_info()
                })
            except Exception as e:
                debug_log(f"發送狀態更新失敗: {e}")

    elif message_type == "heartbeat":
        # WebSocket 心跳處理
        tab_id = data.get("tabId", "unknown")
        timestamp = data.get("timestamp", 0)

        tab_info = {
            'timestamp': timestamp,
            'last_seen': time.time()
        }

        # 更新會話的標籤頁信息
        if hasattr(session, 'active_tabs'):
            session.active_tabs[tab_id] = tab_info
        else:
            session.active_tabs = {tab_id: tab_info}

        # 同時更新全局標籤頁狀態
        manager.global_active_tabs[tab_id] = tab_info

        # 發送心跳回應
        if session.websocket:
            try:
                await session.websocket.send_json({
                    "type": "heartbeat_response",
                    "tabId": tab_id,
                    "timestamp": timestamp
                })
            except Exception as e:
                debug_log(f"發送心跳回應失敗: {e}")

    elif message_type == "user_timeout":
        # 用戶設置的超時已到
        debug_log(f"收到用戶超時通知: {session.session_id}")
        # 清理會話資源
        await session._cleanup_resources_on_timeout()
        # 重構：不再自動停止服務器，保持服務器運行以支援持久性

    else:
        debug_log(f"未知的消息類型: {message_type}")


async def _delayed_server_stop(manager: 'WebUIManager'):
    """延遲停止服務器"""
    import asyncio
    await asyncio.sleep(5)  # 等待 5 秒讓前端有時間關閉
    from ..main import stop_web_ui
    stop_web_ui()
    debug_log("Web UI 服務器已因用戶超時而停止")