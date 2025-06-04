#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP 伺服器主程式
================

MCP Feedback Enhanced 的核心伺服器程式，提供用戶互動回饋功能。
支援智能環境檢測，自動選擇 Qt GUI 或 Web UI 介面。

主要功能：
- 環境檢測（本地/遠端）
- 介面選擇（GUI/Web UI）
- 圖片處理和 MCP 整合
- 回饋結果標準化

作者: Fábio Ferreira (原作者)
增強: Minidoracat (Web UI, 圖片支援, 環境檢測)
重構: 模塊化設計
"""

import os
import sys
import json
import tempfile
import asyncio
import base64
from typing import Annotated, List
import io
import time

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.types import Image as MCPImage
from mcp.types import TextContent
from pydantic import Field

# 導入多語系支援
from .i18n import get_i18n_manager

# 導入統一的調試功能
from .debug import server_debug_log as debug_log

# Import the new connection manager
from .connection_manager import get_connection_manager, with_persistent_connection

# Import performance optimizer
from .performance_optimizer import get_performance_optimizer, enable_performance_optimizations

# ===== 編碼初始化 =====
def init_encoding():
    """初始化編碼設置，確保正確處理中文字符"""
    try:
        # Windows 特殊處理
        if sys.platform == 'win32':
            import msvcrt
            # 設置為二進制模式
            msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
            msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)

            # 重新包裝為 UTF-8 文本流，並禁用緩衝
            sys.stdin = io.TextIOWrapper(
                sys.stdin.detach(),
                encoding='utf-8',
                errors='replace',
                newline=None
            )
            sys.stdout = io.TextIOWrapper(
                sys.stdout.detach(),
                encoding='utf-8',
                errors='replace',
                newline='',
                write_through=True  # 關鍵：禁用寫入緩衝
            )
        else:
            # 非 Windows 系統的標準設置
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            if hasattr(sys.stdin, 'reconfigure'):
                sys.stdin.reconfigure(encoding='utf-8', errors='replace')

        # 設置 stderr 編碼（用於調試訊息）
        if hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')

        return True
    except Exception as e:
        # 如果編碼設置失敗，嘗試基本設置
        try:
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            if hasattr(sys.stdin, 'reconfigure'):
                sys.stdin.reconfigure(encoding='utf-8', errors='replace')
            if hasattr(sys.stderr, 'reconfigure'):
                sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except:
            pass
        return False

# 初始化編碼（在導入時就執行）
_encoding_initialized = init_encoding()

# ===== 常數定義 =====
SERVER_NAME = "互動式回饋收集 MCP"
SSH_ENV_VARS = ['SSH_CONNECTION', 'SSH_CLIENT', 'SSH_TTY']
REMOTE_ENV_VARS = ['REMOTE_CONTAINERS', 'CODESPACES']

# 初始化 MCP 服務器
from . import __version__

# 確保 log_level 設定為正確的大寫格式
fastmcp_settings = {}

# 檢查環境變數並設定正確的 log_level
env_log_level = os.getenv("FASTMCP_LOG_LEVEL", "").upper()
if env_log_level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
    fastmcp_settings["log_level"] = env_log_level
else:
    # 預設使用 INFO 等級
    fastmcp_settings["log_level"] = "INFO"

mcp = FastMCP(SERVER_NAME, version=__version__, **fastmcp_settings)


# ===== 工具函數 =====
def is_remote_environment() -> bool:
    """
    檢測是否在遠端環境中運行

    Returns:
        bool: True 表示遠端環境，False 表示本地環境
    """
    # 檢查 SSH 連線指標
    for env_var in SSH_ENV_VARS:
        if os.getenv(env_var):
            debug_log(f"偵測到 SSH 環境變數: {env_var}")
            return True

    # 檢查遠端開發環境
    for env_var in REMOTE_ENV_VARS:
        if os.getenv(env_var):
            debug_log(f"偵測到遠端開發環境: {env_var}")
            return True

    # 檢查 Docker 容器
    if os.path.exists('/.dockerenv'):
        debug_log("偵測到 Docker 容器環境")
        return True

    # Windows 遠端桌面檢查
    if sys.platform == 'win32':
        session_name = os.getenv('SESSIONNAME', '')
        if session_name and 'RDP' in session_name:
            debug_log(f"偵測到 Windows 遠端桌面: {session_name}")
            return True

    # Linux 無顯示環境檢查
    if sys.platform.startswith('linux') and not os.getenv('DISPLAY'):
        debug_log("偵測到 Linux 無顯示環境")
        return True

    return False


def can_use_gui() -> bool:
    """
    檢測是否可以使用圖形介面

    Returns:
        bool: True 表示可以使用 GUI，False 表示只能使用 Web UI
    """
    if is_remote_environment():
        return False

    try:
        from PySide6.QtWidgets import QApplication
        debug_log("成功載入 PySide6，可使用 GUI")
        return True
    except ImportError:
        debug_log("無法載入 PySide6，使用 Web UI")
        return False
    except Exception as e:
        debug_log(f"GUI 初始化失敗: {e}")
        return False


def save_feedback_to_file(feedback_data: dict, file_path: str = None) -> str:
    """
    將回饋資料儲存到 JSON 文件

    Args:
        feedback_data: 回饋資料字典
        file_path: 儲存路徑，若為 None 則自動產生臨時文件

    Returns:
        str: 儲存的文件路徑
    """
    if file_path is None:
        temp_fd, file_path = tempfile.mkstemp(suffix='.json', prefix='feedback_')
        os.close(temp_fd)

    # 確保目錄存在
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    # 複製數據以避免修改原始數據
    json_data = feedback_data.copy()

    # 處理圖片數據：將 bytes 轉換為 base64 字符串以便 JSON 序列化
    if "images" in json_data and isinstance(json_data["images"], list):
        processed_images = []
        for img in json_data["images"]:
            if isinstance(img, dict) and "data" in img:
                processed_img = img.copy()
                # 如果 data 是 bytes，轉換為 base64 字符串
                if isinstance(img["data"], bytes):
                    processed_img["data"] = base64.b64encode(img["data"]).decode('utf-8')
                    processed_img["data_type"] = "base64"
                processed_images.append(processed_img)
            else:
                processed_images.append(img)
        json_data["images"] = processed_images

    # 儲存資料
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    debug_log(f"回饋資料已儲存至: {file_path}")
    return file_path


def create_feedback_text(feedback_data: dict) -> str:
    """
    建立格式化的回饋文字

    Args:
        feedback_data: 回饋資料字典

    Returns:
        str: 格式化後的回饋文字
    """
    text_parts = []

    # 基本回饋內容
    if feedback_data.get("interactive_feedback"):
        text_parts.append(f"=== 用戶回饋 ===\n{feedback_data['interactive_feedback']}")

    # 命令執行日誌
    if feedback_data.get("command_logs"):
        text_parts.append(f"=== 命令執行日誌 ===\n{feedback_data['command_logs']}")

    # 圖片附件概要
    if feedback_data.get("images"):
        images = feedback_data["images"]
        text_parts.append(f"=== 圖片附件概要 ===\n用戶提供了 {len(images)} 張圖片：")

        for i, img in enumerate(images, 1):
            size = img.get("size", 0)
            name = img.get("name", "unknown")

            # 智能單位顯示
            if size < 1024:
                size_str = f"{size} B"
            elif size < 1024 * 1024:
                size_kb = size / 1024
                size_str = f"{size_kb:.1f} KB"
            else:
                size_mb = size / (1024 * 1024)
                size_str = f"{size_mb:.1f} MB"

            img_info = f"  {i}. {name} ({size_str})"

            # 為提高兼容性，添加 base64 預覽信息
            if img.get("data"):
                try:
                    if isinstance(img["data"], bytes):
                        img_base64 = base64.b64encode(img["data"]).decode('utf-8')
                    elif isinstance(img["data"], str):
                        img_base64 = img["data"]
                    else:
                        img_base64 = None

                    if img_base64:
                        # 只顯示前50個字符的預覽
                        preview = img_base64[:50] + "..." if len(img_base64) > 50 else img_base64
                        img_info += f"\n     Base64 預覽: {preview}"
                        img_info += f"\n     完整 Base64 長度: {len(img_base64)} 字符"

                        # 如果 AI 助手不支援 MCP 圖片，可以提供完整 base64
                        debug_log(f"圖片 {i} Base64 已準備，長度: {len(img_base64)}")

                        # 可選：根據環境變數決定是否包含完整 base64
                        include_full_base64 = os.getenv("INCLUDE_BASE64_DETAIL", "").lower() in ("true", "1", "yes", "on")
                        if include_full_base64:
                            img_info += f"\n     完整 Base64: data:image/png;base64,{img_base64}"

                except Exception as e:
                    debug_log(f"圖片 {i} Base64 處理失敗: {e}")

            text_parts.append(img_info)

        # 添加兼容性說明
        text_parts.append("\n💡 注意：如果 AI 助手無法顯示圖片，圖片數據已包含在上述 Base64 信息中。")

    return "\n\n".join(text_parts) if text_parts else "用戶未提供任何回饋內容。"


def process_images(images_data: List[dict]) -> List[MCPImage]:
    """
    處理圖片資料，轉換為 MCP 圖片對象

    Args:
        images_data: 圖片資料列表

    Returns:
        List[MCPImage]: MCP 圖片對象列表
    """
    mcp_images = []

    for i, img in enumerate(images_data, 1):
        try:
            if not img.get("data"):
                debug_log(f"圖片 {i} 沒有資料，跳過")
                continue

            # 檢查數據類型並相應處理
            if isinstance(img["data"], bytes):
                # 如果是原始 bytes 數據，直接使用
                image_bytes = img["data"]
                debug_log(f"圖片 {i} 使用原始 bytes 數據，大小: {len(image_bytes)} bytes")
            elif isinstance(img["data"], str):
                # 如果是 base64 字符串，進行解碼
                image_bytes = base64.b64decode(img["data"])
                debug_log(f"圖片 {i} 從 base64 解碼，大小: {len(image_bytes)} bytes")
            else:
                debug_log(f"圖片 {i} 數據類型不支援: {type(img['data'])}")
                continue

            if len(image_bytes) == 0:
                debug_log(f"圖片 {i} 數據為空，跳過")
                continue

            # 根據文件名推斷格式
            file_name = img.get("name", "image.png")
            if file_name.lower().endswith(('.jpg', '.jpeg')):
                image_format = 'jpeg'
            elif file_name.lower().endswith('.gif'):
                image_format = 'gif'
            else:
                image_format = 'png'  # 默認使用 PNG

            # 創建 MCPImage 對象
            mcp_image = MCPImage(data=image_bytes, format=image_format)
            mcp_images.append(mcp_image)

            debug_log(f"圖片 {i} ({file_name}) 處理成功，格式: {image_format}")

        except Exception as e:
            debug_log(f"圖片 {i} 處理失敗: {e}")
            import traceback
            debug_log(f"詳細錯誤: {traceback.format_exc()}")

    debug_log(f"共處理 {len(mcp_images)} 張圖片")
    return mcp_images


async def launch_gui_with_timeout(project_dir: str, summary: str, timeout: int) -> dict:
    """
    啟動 GUI 模式並處理超時
    """
    debug_log(f"啟動 GUI 模式（超時：{timeout}秒）")

    try:
        from .gui import feedback_ui_with_timeout

        # 直接調用帶超時的 GUI 函數
        result = feedback_ui_with_timeout(project_dir, summary, timeout)

        if result:
            return {
                "logs": f"GUI 模式回饋收集完成",
                "interactive_feedback": result.get("interactive_feedback", ""),
                "images": result.get("images", [])
            }
        else:
            return {
                "logs": "用戶取消了回饋收集",
                "interactive_feedback": "",
                "images": []
            }

    except TimeoutError as e:
        # 超時異常 - 這是預期的行為
        raise e
    except Exception as e:
        debug_log(f"GUI 啟動失败: {e}")
        raise Exception(f"GUI 啟動失败: {e}")


# ===== MCP 工具定義 =====
@mcp.tool()
async def interactive_feedback(
    project_directory: Annotated[str, Field(description="專案目錄路徑")] = ".",
    summary: Annotated[str, Field(description="AI 工作完成的摘要說明")] = "我已完成了您請求的任務。",
    timeout: Annotated[int, Field(description="等待用戶回饋的超時時間（秒）")] = 600
) -> List:
    """
    收集用戶的互動回饋，支援文字和圖片

    此工具會自動偵測運行環境：
    - 遠端環境：使用 Web UI
    - 本地環境：使用 Qt GUI
    - 可透過 FORCE_WEB 環境變數強制使用 Web UI

    用戶可以：
    1. 執行命令來驗證結果
    2. 提供文字回饋
    3. 上傳圖片作為回饋
    4. 查看 AI 的工作摘要

    介面控制（按優先級排序）：
    1. **FORCE_WEB 環境變數**：在 mcp.json 中設置 "FORCE_WEB": "true"
    2. 自動檢測：根據運行環境自動選擇

    調試模式：
    - 設置環境變數 MCP_DEBUG=true 可啟用詳細調試輸出
    - 生產環境建議關閉調試模式以避免輸出干擾

    持久連接模式：
    - 設置環境變數 MCP_PERSISTENT=true 可啟用持久連接
    - 支援網路斷線自動重連和會話狀態恢復

    性能優化：
    - 設置環境變數 MCP_FAST_LAUNCH=true 可啟用快速啟動
    - 包含組件預載入和環境檢測緩存

    Args:
        project_directory: 專案目錄路徑
        summary: AI 工作完成的摘要說明
        timeout: 等待用戶回饋的超時時間（秒），預設為 600 秒（10 分鐘）

    Returns:
        List: 包含 TextContent 和 MCPImage 對象的列表
    """
    # Get connection manager and performance optimizer
    connection_manager = get_connection_manager()
    performance_optimizer = get_performance_optimizer()

    # Start heartbeat if in persistent mode (equivalent to the decorator)
    if connection_manager.is_persistent_mode and not connection_manager.heartbeat_task:
        await connection_manager.start_heartbeat()

    # Check for performance optimization mode
    fast_launch = os.getenv("MCP_FAST_LAUNCH", "").lower() in ("true", "1", "yes", "on")
    if fast_launch:
        enable_performance_optimizations()
        debug_log("Performance optimizations enabled")

    # Check if persistent mode is enabled
    persistent_mode = os.getenv("MCP_PERSISTENT", "").lower() in ("true", "1", "yes", "on")
    if persistent_mode and not connection_manager.is_persistent_mode:
        connection_manager.enable_persistent_mode()
        debug_log("Persistent mode enabled via environment variable")

    # 檢查環境變數 FORCE_WEB
    force_web = False
    env_force_web = os.getenv("FORCE_WEB", "").lower()
    if env_force_web in ("true", "1", "yes", "on"):
        force_web = True
        debug_log("環境變數 FORCE_WEB 已啟用，強制使用 Web UI")
    elif env_force_web in ("false", "0", "no", "off"):
        force_web = False
        debug_log("環境變數 FORCE_WEB 已停用，使用預設邏輯")

    # Fast interface selection using optimizer
    if fast_launch:
        interface_type = performance_optimizer.get_optimal_interface_choice(force_web)
        debug_log(f"快速介面選擇: {interface_type}")
    else:
        # 原始環境偵測
        is_remote = is_remote_environment()
        can_gui = can_use_gui()
        interface_type = "web" if (is_remote or not can_gui or force_web) else "gui"
        debug_log(f"環境偵測結果 - 遠端: {is_remote}, GUI 可用: {can_gui}, 強制 Web UI: {force_web}")

    debug_log(f"決定使用介面: {interface_type}")
    debug_log(f"持久連接模式: {connection_manager.is_persistent_mode}")
    debug_log(f"性能優化模式: {fast_launch}")

    try:
        # 確保專案目錄存在
        if not os.path.exists(project_directory):
            project_directory = os.getcwd()
        project_directory = os.path.abspath(project_directory)

        # Create persistent session if in persistent mode
        if connection_manager.is_persistent_mode:
            session_id = await connection_manager.create_persistent_session(project_directory, summary)
            debug_log(f"Created persistent session: {session_id}")

        # Extend timeout for persistent mode
        if connection_manager.is_persistent_mode:
            # Use much longer timeout for persistent sessions (24 hours)
            extended_timeout = max(timeout, 86400)  # At least 24 hours
            debug_log(f"Extended timeout for persistent mode: {extended_timeout} seconds")
        else:
            extended_timeout = timeout

        # Launch interface with optimization
        if fast_launch:
            # Use optimized launcher
            result = await performance_optimizer.fast_launch_interface(
                interface_type, project_directory, summary, extended_timeout
            )
        else:
            # Use standard launcher
            if interface_type == "web":
                result = await launch_web_ui_with_timeout(project_directory, summary, extended_timeout)
            else:
                result = await launch_gui_with_timeout(project_directory, summary, extended_timeout)

        # Update persistent session with results
        if connection_manager.is_persistent_mode and result:
            await connection_manager.update_session_feedback(
                result.get("interactive_feedback", ""),
                result.get("images", [])
            )

        # 處理取消情況
        if not result:
            return [TextContent(type="text", text="用戶取消了回饋。")]

        # 儲存詳細結果
        save_feedback_to_file(result)

        # 建立回饋項目列表
        feedback_items = []

        # 添加文字回饋
        if result.get("interactive_feedback") or result.get("command_logs") or result.get("images"):
            feedback_text = create_feedback_text(result)
            feedback_items.append(TextContent(type="text", text=feedback_text))
            debug_log("文字回饋已添加")

        # 添加圖片回饋
        if result.get("images"):
            mcp_images = process_images(result["images"])
            feedback_items.extend(mcp_images)
            debug_log(f"已添加 {len(mcp_images)} 張圖片")

        # 確保至少有一個回饋項目
        if not feedback_items:
            feedback_items.append(TextContent(type="text", text="用戶未提供任何回饋內容。"))

        debug_log(f"回饋收集完成，共 {len(feedback_items)} 個項目")
        return feedback_items

    except TimeoutError as e:
        # Handle timeout with persistent session restoration
        if connection_manager.is_persistent_mode:
            debug_log("Timeout in persistent mode - session preserved for later restoration")
            return [TextContent(type="text", text=f"會話已保存，可稍後恢復。{str(e)}")]
        else:
            error_msg = f"回饋收集超時: {str(e)}"
            debug_log(f"超時錯誤: {error_msg}")
            return [TextContent(type="text", text=error_msg)]
    except Exception as e:
        error_msg = f"回饋收集錯誤: {str(e)}"
        debug_log(f"錯誤: {error_msg}")
        return [TextContent(type="text", text=error_msg)]


async def launch_web_ui_with_timeout(project_dir: str, summary: str, timeout: int) -> dict:
    """
    啟動 Web UI 收集回饋，支援自訂超時時間

    Args:
        project_dir: 專案目錄路徑
        summary: AI 工作摘要
        timeout: 超時時間（秒）

    Returns:
        dict: 收集到的回饋資料
    """
    debug_log(f"啟動 Web UI 介面，超時時間: {timeout} 秒")

    try:
        # 使用新的 web 模組
        from .web import launch_web_feedback_ui

        # 傳遞 timeout 參數給 Web UI
        return await launch_web_feedback_ui(project_dir, summary, timeout)
    except ImportError as e:
        debug_log(f"無法導入 Web UI 模組: {e}")
        return {
            "command_logs": "",
            "interactive_feedback": f"Web UI 模組導入失敗: {str(e)}",
            "images": []
        }
    except TimeoutError as e:
        debug_log(f"Web UI 超時: {e}")
        return {
            "command_logs": "",
            "interactive_feedback": f"回饋收集超時（{timeout}秒），介面已自動關閉。",
            "images": []
        }
    except Exception as e:
        error_msg = f"Web UI 錯誤: {e}"
        debug_log(f"❌ {error_msg}")
        return {
            "command_logs": "",
            "interactive_feedback": f"錯誤: {str(e)}",
            "images": []
        }


@mcp.tool()
def get_system_info() -> str:
    """
    獲取系統環境資訊

    Returns:
        str: JSON 格式的系統資訊
    """
    is_remote = is_remote_environment()
    can_gui = can_use_gui()
    connection_manager = get_connection_manager()
    performance_optimizer = get_performance_optimizer()

    system_info = {
        "平台": sys.platform,
        "Python 版本": sys.version.split()[0],
        "遠端環境": is_remote,
        "GUI 可用": can_gui,
        "建議介面": "Web UI" if is_remote or not can_gui else "Qt GUI",
        "持久連接模式": connection_manager.is_persistent_mode,
        "活躍會話數": len(connection_manager.get_active_sessions()),
        "性能優化狀態": performance_optimizer.get_performance_stats(),
        "環境變數": {
            "SSH_CONNECTION": os.getenv("SSH_CONNECTION"),
            "SSH_CLIENT": os.getenv("SSH_CLIENT"),
            "DISPLAY": os.getenv("DISPLAY"),
            "VSCODE_INJECTION": os.getenv("VSCODE_INJECTION"),
            "SESSIONNAME": os.getenv("SESSIONNAME"),
            "MCP_PERSISTENT": os.getenv("MCP_PERSISTENT"),
            "MCP_FAST_LAUNCH": os.getenv("MCP_FAST_LAUNCH"),
            "FORCE_WEB": os.getenv("FORCE_WEB"),
        }
    }

    return json.dumps(system_info, ensure_ascii=False, indent=2)


@mcp.tool()
async def manage_persistent_sessions(
    action: Annotated[str, Field(description="操作類型: list(列出會話), restore(恢復會話), cleanup(清理舊會話)")] = "list",
    session_id: Annotated[str, Field(description="會話ID (restore操作時需要)")] = "",
    max_age_hours: Annotated[int, Field(description="清理超過指定小時數的會話 (cleanup操作時使用)")] = 24
) -> str:
    """
    管理持久連接會話

    此工具允許管理和恢復持久連接會話，支援：
    - 列出活躍會話
    - 恢復中斷的會話
    - 清理舊會話文件

    Args:
        action: 操作類型 (list/restore/cleanup)
        session_id: 會話ID (恢復會話時需要)
        max_age_hours: 清理舊會話的最大年齡（小時）

    Returns:
        str: 操作結果的JSON格式字符串
    """
    connection_manager = get_connection_manager()

    try:
        if action == "list":
            # 列出活躍會話
            sessions = connection_manager.get_active_sessions()
            result = {
                "action": "list",
                "success": True,
                "active_sessions": len(sessions),
                "sessions": []
            }

            for session in sessions:
                session_info = {
                    "session_id": session.get("session_id", "unknown"),
                    "project_directory": session.get("project_directory", ""),
                    "created_at": session.get("created_at", 0),
                    "last_heartbeat": session.get("last_heartbeat", 0),
                    "status": session.get("status", "unknown"),
                    "has_feedback": bool(session.get("feedback_result"))
                }
                result["sessions"].append(session_info)

            debug_log(f"Listed {len(sessions)} active sessions")
            return json.dumps(result, ensure_ascii=False, indent=2)

        elif action == "restore":
            # 恢復指定會話
            if not session_id:
                return json.dumps({
                    "action": "restore",
                    "success": False,
                    "error": "需要提供會話ID"
                }, ensure_ascii=False, indent=2)

            session_data = await connection_manager.restore_session(session_id)
            if session_data:
                result = {
                    "action": "restore",
                    "success": True,
                    "session_id": session_id,
                    "project_directory": session_data.get("project_directory", ""),
                    "summary": session_data.get("summary", ""),
                    "feedback_result": session_data.get("feedback_result", ""),
                    "status": session_data.get("status", "unknown")
                }
                debug_log(f"Restored session: {session_id}")
            else:
                result = {
                    "action": "restore",
                    "success": False,
                    "error": f"會話 {session_id} 未找到或已過期"
                }
                debug_log(f"Failed to restore session: {session_id}")

            return json.dumps(result, ensure_ascii=False, indent=2)

        elif action == "cleanup":
            # 清理舊會話
            connection_manager.cleanup_old_sessions(max_age_hours)
            result = {
                "action": "cleanup",
                "success": True,
                "max_age_hours": max_age_hours,
                "message": f"已清理超過 {max_age_hours} 小時的舊會話"
            }
            debug_log(f"Cleaned up sessions older than {max_age_hours} hours")
            return json.dumps(result, ensure_ascii=False, indent=2)

        else:
            return json.dumps({
                "action": action,
                "success": False,
                "error": f"不支援的操作: {action}。支援的操作: list, restore, cleanup"
            }, ensure_ascii=False, indent=2)

    except Exception as e:
        error_result = {
            "action": action,
            "success": False,
            "error": str(e)
        }
        debug_log(f"Session management error: {e}")
        return json.dumps(error_result, ensure_ascii=False, indent=2)


@mcp.tool()
async def optimize_performance(
    action: Annotated[str, Field(description="優化操作: preload(預載入組件), benchmark(性能測試), clear_cache(清除緩存), status(狀態檢查)")] = "status"
) -> str:
    """
    性能優化和診斷工具

    此工具用於優化 MCP Feedback Enhanced 的性能和診斷慢啟動問題：
    - 預載入 GUI/Web 組件減少啟動延遲
    - 緩存環境檢測結果避免重複檢查
    - 性能測試和基準測量
    - 清除緩存解決問題

    Args:
        action: 優化操作類型 (preload/benchmark/clear_cache/status)

    Returns:
        str: 優化結果的JSON格式字符串
    """
    performance_optimizer = get_performance_optimizer()

    try:
        if action == "preload":
            # 預載入組件
            start_time = time.time()
            enable_performance_optimizations()

            # 等待預載入完成
            await asyncio.sleep(2)  # 給予組件預載入時間

            preload_time = time.time() - start_time
            result = {
                "action": "preload",
                "success": True,
                "preload_time": round(preload_time, 2),
                "status": performance_optimizer.get_performance_stats(),
                "message": "組件預載入完成，下次啟動將更快"
            }
            debug_log(f"Performance preload completed in {preload_time:.2f}s")
            return json.dumps(result, ensure_ascii=False, indent=2)

        elif action == "benchmark":
            # 性能基準測試
            start_time = time.time()

            # 測試環境檢測速度
            env_start = time.time()
            is_remote = is_remote_environment()
            can_gui = can_use_gui()
            env_time = time.time() - env_start

            # 測試介面選擇速度
            choice_start = time.time()
            interface_type = performance_optimizer.get_optimal_interface_choice()
            choice_time = time.time() - choice_start

            total_time = time.time() - start_time

            result = {
                "action": "benchmark",
                "success": True,
                "timings": {
                    "environment_detection": round(env_time, 3),
                    "interface_choice": round(choice_time, 3),
                    "total_startup_overhead": round(total_time, 3)
                },
                "environment": {
                    "is_remote": is_remote,
                    "can_gui": can_gui,
                    "selected_interface": interface_type
                },
                "performance_status": performance_optimizer.get_performance_stats()
            }
            debug_log(f"Performance benchmark completed: {total_time:.3f}s total")
            return json.dumps(result, ensure_ascii=False, indent=2)

        elif action == "clear_cache":
            # 清除性能緩存
            cache_file = performance_optimizer.cache_file
            cache_existed = cache_file.exists()

            if cache_existed:
                cache_file.unlink()

            # 重新初始化優化器
            performance_optimizer.cache_data = {}
            performance_optimizer.gui_preloaded = False
            performance_optimizer.web_manager_ready = False

            result = {
                "action": "clear_cache",
                "success": True,
                "cache_existed": cache_existed,
                "cache_file": str(cache_file),
                "message": "性能緩存已清除，下次啟動將重新檢測環境"
            }
            debug_log("Performance cache cleared")
            return json.dumps(result, ensure_ascii=False, indent=2)

        elif action == "status":
            # 狀態檢查
            stats = performance_optimizer.get_performance_stats()
            cache_age = 0

            if performance_optimizer.cache_file.exists():
                cache_age = time.time() - performance_optimizer.cache_file.stat().st_mtime

            result = {
                "action": "status",
                "success": True,
                "performance_stats": stats,
                "cache_age_seconds": round(cache_age, 2),
                "recommendations": []
            }

            # 添加建議
            if not stats["gui_preloaded"] and not stats["web_manager_ready"]:
                result["recommendations"].append("運行 preload 操作以預載入組件加速啟動")

            if cache_age > 1800:  # 30 minutes
                result["recommendations"].append("緩存已過期，考慮運行 clear_cache 重新檢測環境")

            debug_log("Performance status checked")
            return json.dumps(result, ensure_ascii=False, indent=2)

        else:
            return json.dumps({
                "action": action,
                "success": False,
                "error": f"不支援的操作: {action}。支援的操作: preload, benchmark, clear_cache, status"
            }, ensure_ascii=False, indent=2)

    except Exception as e:
        error_result = {
            "action": action,
            "success": False,
            "error": str(e)
        }
        debug_log(f"Performance optimization error: {e}")
        return json.dumps(error_result, ensure_ascii=False, indent=2)


# ===== 主程式入口 =====
def main():
    """主要入口點，用於套件執行"""
    # 檢查是否啟用調試模式
    debug_enabled = os.getenv("MCP_DEBUG", "").lower() in ("true", "1", "yes", "on")

    if debug_enabled:
        debug_log("🚀 啟動互動式回饋收集 MCP 服務器")
        debug_log(f"   服務器名稱: {SERVER_NAME}")
        debug_log(f"   版本: {__version__}")
        debug_log(f"   平台: {sys.platform}")
        debug_log(f"   編碼初始化: {'成功' if _encoding_initialized else '失敗'}")
        debug_log(f"   遠端環境: {is_remote_environment()}")
        debug_log(f"   GUI 可用: {can_use_gui()}")
        debug_log(f"   建議介面: {'Web UI' if is_remote_environment() or not can_use_gui() else 'Qt GUI'}")
        debug_log("   等待來自 AI 助手的調用...")
        debug_log("準備啟動 MCP 伺服器...")
        debug_log("調用 mcp.run()...")

    try:
        # 使用正確的 FastMCP API
        mcp.run()
    except KeyboardInterrupt:
        if debug_enabled:
            debug_log("收到中斷信號，正常退出")
        sys.exit(0)
    except Exception as e:
        if debug_enabled:
            debug_log(f"MCP 服務器啟動失敗: {e}")
            import traceback
            debug_log(f"詳細錯誤: {traceback.format_exc()}")
        sys.exit(1)


if __name__ == "__main__":
    main()
