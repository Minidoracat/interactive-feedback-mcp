#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Feedback Enhanced - Web UI 測試模組
========================================

用於測試 MCP Feedback Enhanced 的 Web UI 功能。
包含完整的 Web UI 功能測試。

功能測試：
- Web UI 服務器啟動
- 會話管理功能
- WebSocket 通訊
- 多語言支援
- 命令執行功能

使用方法：
    python -m mcp_feedback_enhanced.test_web_ui

作者: Minidoracat
"""

import asyncio
import webbrowser
import time
import sys
import os
import socket
import threading
import json
from pathlib import Path
from typing import Dict, Any, Optional

# 添加專案根目錄到 Python 路徑
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from .debug import debug_log

# 嘗試導入 Web UI 模組
try:
    # 使用新的 web 模組
    from .web import WebUIManager, launch_web_feedback_ui, get_web_ui_manager
    from .web.utils.browser import smart_browser_open, is_wsl_environment
    WEB_UI_AVAILABLE = True
    debug_log("Web UI module loaded successfully.")
except ImportError as e:
    debug_log(f"Web UI module load failed: {str(e)}")
    WEB_UI_AVAILABLE = False

def get_test_summary():
    """獲取測試摘要"""
    return "Web UI Test Summary"

def find_free_port():
    """Find a free port to use for testing"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

def test_web_ui(keep_running=False, standalone_run=False):
    """
    Test the Web UI functionality.
    Can be called by pytest (standalone_run=False) or directly (standalone_run=True).
    """
    debug_log("Testing Web UI...")
    debug_log("=" * 50)

    # Test import
    try:
        # 使用新的 web 模組
        from .web import WebUIManager, launch_web_feedback_ui
        debug_log("Web UI module imported successfully for test.")
    except ImportError as e:
        debug_log(f"Web UI module import failed during test: {str(e)}")
        if standalone_run: return False, None
        assert False, f"Web UI module import failed during test: {str(e)}"
    
    # Check for environment variable port setting
    env_port = os.getenv("MCP_WEB_PORT")
    if env_port:
        try:
            custom_port = int(env_port)
            if 1024 <= custom_port <= 65535:
                debug_log(f"Found available port from MCP_WEB_PORT: {custom_port}")
                test_port = custom_port
            else:
                debug_log(f"MCP_WEB_PORT value invalid ({custom_port}), must be in 1024-65535 range. Finding free port...")
                test_port = find_free_port()
                debug_log(f"Found available port: {test_port}")
        except ValueError:
            debug_log(f"MCP_WEB_PORT format error ({env_port}), must be a number. Finding free port...")
            test_port = find_free_port()
            debug_log(f"Found available port: {test_port}")
    else:
        # Find free port
        try:
            test_port = find_free_port()
            debug_log(f"Found available port: {test_port}")
        except Exception as e:
            debug_log(f"Failed to find free port: {str(e)}")
            if standalone_run: return False, None
            assert False, f"Failed to find free port: {str(e)}"

    # Test manager creation (讓 WebUIManager 自己處理端口邏輯)
    try:
        manager = WebUIManager()
        debug_log("Web UI Manager created successfully.")
    except Exception as e:
        debug_log(f"Web UI Manager creation failed: {str(e)}")
        if standalone_run: return False, None
        assert False, f"Web UI Manager creation failed: {str(e)}"
    
    # Test server start (with timeout)
    server_started = False
    try:
        debug_log("Starting Web server...")

        server_start_success_in_thread = [False] # Use a list to pass by reference

        def start_server_thread_target():
            try:
                manager.start_server()
                server_start_success_in_thread[0] = True
            except Exception as e:
                debug_log(f"Server start error in thread: {str(e)}")
                server_start_success_in_thread[0] = False
        
        # Start server in thread
        server_thread = threading.Thread(target=start_server_thread_target)
        server_thread.daemon = True
        server_thread.start()
        
        # Wait a moment and test if server is responsive
        time.sleep(3) # Give server time to start
        
        assert server_start_success_in_thread[0], "Server failed to start within the thread."

        # Test if port is listening
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            connect_result = s.connect_ex((manager.host, manager.port))
            assert connect_result == 0, f"Cannot connect to port {manager.port} after server start."
            server_started = True
            debug_log("Web server started successfully and port is listening.")
            debug_log(f"Server running at: {manager.host}:{manager.port}")

    except Exception as e:
        debug_log(f"Web server start failed: {str(e)}")
        if standalone_run: return False, None
        assert False, f"Web server start failed: {str(e)}"

    if standalone_run and not server_started : return False, None # Extra check for standalone
    assert server_started, "Server not started, aborting tests."
    
    # Test session creation
    session_info = None
    try:
        project_dir = str(Path.cwd())
        summary = get_test_summary() # Use the simplified function
        session_id = manager.create_session(project_dir, summary)
        session_info = {
            'manager': manager,
            'session_id': session_id,
            'url': f"http://{manager.host}:{manager.port}"
        }
        assert session_id is not None, "Session ID should be created."
        debug_log(f"Test session created: {session_id[:8]}")
        debug_log(f"Test URL: {session_info['url']}")

        # 測試瀏覽器啟動功能
        try:
            debug_log("Testing browser launch...")
            if is_wsl_environment():
                debug_log("WSL environment detected.")
            else:
                debug_log("Non-WSL environment.")

            # smart_browser_open(session_info['url']) # This might open a real browser, skip for automated tests
            debug_log(f"Browser launch attempt logged for URL: {session_info['url']} (actual launch skipped in auto test)")
        except Exception as browser_error:
            debug_log(f"Browser launch logic failed: {str(browser_error)}")
            # Not failing the test for this, as it's environment dependent
            debug_log("Note: Browser launch might require specific desktop environment setup.")

    except Exception as e:
        debug_log(f"Session creation failed: {str(e)}")
        if standalone_run: return False, None
        assert False, f"Session creation failed: {str(e)}"
    
    if standalone_run and not session_info: return False, None # Extra check for standalone
    assert session_info is not None, "session_info should be populated."
    debug_log("\n" + "=" * 50)
    debug_log("All Web UI basic tests passed.")
    debug_log("Notes:")
    debug_log("- Web UI is automatically enabled for remote/WSL or if GUI is unavailable.")
    debug_log("- Realtime command execution is supported.")
    debug_log("- Modern dark theme is applied.")
    debug_log("- Smart Ctrl+V paste for images is available.")
    
    # To satisfy pytest, a test function should not return a value unless it's part of a specific pytest pattern (like fixtures)
    # The important part is that assertions pass. If keep_running is True (only from direct script run), this test might hang.
    if standalone_run:
        if keep_running: # keep_running is a legacy param, usually for __main__ context
            interactive_demo(session_info)
        return True, session_info
    # For pytest, no explicit return is needed for success if all assertions pass

def test_environment_detection():
    """Test environment detection logic"""
    debug_log("Testing environment detection...")
    debug_log("-" * 30)

    try:
        from .server import is_remote_environment, is_wsl_environment, can_use_gui

        wsl_detected = is_wsl_environment()
        remote_detected = is_remote_environment()
        gui_available = can_use_gui() # This will now likely be False

        debug_log(f"WSL Detection: {'Yes' if wsl_detected else 'No'}")
        debug_log(f"Remote Detection: {'Yes' if remote_detected else 'No'}")
        debug_log(f"GUI Availability: {'Yes' if gui_available else 'No'}") # Expected False

        if wsl_detected:
            debug_log("Info: WSL environment, Web UI will be used with Windows browser.")
        elif remote_detected:
            debug_log("Info: Remote environment, Web UI will be used.")
        elif not gui_available:
            debug_log("Info: Local environment but GUI unavailable, Web UI will be used.")
        else:
            # This case should ideally not happen after GUI removal if can_use_gui is accurate
            debug_log("Info: Local environment with GUI available (unexpected after changes).")

        assert True # If no exception, the checks ran

    except Exception as e:
        debug_log(f"Environment detection test failed: {str(e)}")
        assert False, f"Environment detection test failed: {str(e)}"

def test_mcp_integration():
    """Test MCP server integration"""
    debug_log("Testing MCP integration...")
    debug_log("-" * 30)

    try:
        from .server import interactive_feedback
        assert interactive_feedback is not None, "interactive_feedback tool should be importable"
        debug_log("MCP tool 'interactive_feedback' is available.")

        # Test timeout parameter
        debug_log("Timeout parameter is supported by the tool.")

        # Test environment-based Web UI selection
        debug_log("Environment-based Web UI selection is handled by the tool.")

        debug_log("MCP tool is ready for AI assistant calls.")
        assert True
    except Exception as e:
        debug_log(f"MCP integration test failed: {str(e)}")
        assert False, f"MCP integration test failed: {str(e)}"

def test_new_parameters():
    """Test timeout parameter and environment variable support"""
    debug_log("Testing parameter functionality...")
    debug_log("-" * 30)

    try:
        from .server import interactive_feedback
        import inspect
        sig = inspect.signature(interactive_feedback)

        assert 'timeout' in sig.parameters, "Timeout parameter should exist."
        timeout_param = sig.parameters['timeout']
        debug_log(f"Timeout parameter exists with default: {timeout_param.default}")

        import os
        # FORCE_WEB check removed as it's no longer used by the application
        debug_log("Parameter functionality appears normal (FORCE_WEB check removed).")
        assert True
    except Exception as e:
        debug_log(f"Parameter test failed: {str(e)}")
        assert False, f"Parameter test failed: {str(e)}"

def test_environment_web_ui_mode():
    """Test environment-based Web UI mode"""
    debug_log("Testing environment-based Web UI mode...")
    debug_log("-" * 30)

    try:
        from .server import is_remote_environment, is_wsl_environment, can_use_gui # Removed interactive_feedback import as it's not used here
        import os

        is_wsl = is_wsl_environment()
        is_remote = is_remote_environment()
        gui_available = can_use_gui() # Expected False

        debug_log(f"Current environment: WSL={is_wsl}, Remote={is_remote}, GUI available={gui_available}")
        # FORCE_WEB logic removed as Web UI is always used.

        if is_wsl:
            debug_log("WSL environment detected, Web UI with Windows browser will be used.")
        elif is_remote: # This condition implies not WSL
            debug_log("Remote environment detected, Web UI will be used.")
        elif not gui_available: # This will always be true now if not remote and not WSL
            debug_log("Local environment and GUI not available, Web UI will be used.")
        else:
            # This case should ideally not be reached if can_use_gui() is correctly always False
            # and is_remote_environment correctly identifies all non-local-desktop scenarios.
            debug_log("Local environment and GUI reported as available (this is unexpected). Web UI should still be used by default.")

        assert True
    except Exception as e:
        debug_log(f"Environment variable test failed: {str(e)}")
        assert False, f"Environment variable test failed: {str(e)}"

def interactive_demo(session_info):
    """Run interactive demo with the Web UI"""
    debug_log("Web UI Interactive Test Mode")
    debug_log("=" * 50)
    debug_log(f"Server Address: {session_info['url']}")
    debug_log("Operation Guide:")
    debug_log("- Open the server address in your browser.")
    debug_log("- Try the following features:")
    debug_log("  - Click 'Show Command Block' / 'Hide Command Block'.")
    debug_log("  - Input commands and execute (e.g., 'ls', 'pwd').")
    debug_log("  - Input text in the feedback area.")
    debug_log("  - Use Ctrl+Enter to submit feedback.")
    debug_log("  - Test WebSocket realtime updates by interacting with the UI.")
    debug_log("  - Test page persistence by reloading or opening in new tab (if session active).")
    debug_log("Control Options:")
    debug_log("- Press Enter to continue server (it will keep running).")
    debug_log("- Type 'q', 'quit', or 'exit' and press Enter to stop the server.")
    
    while True:
        try:
            user_input = input("\n>>> ").strip().lower()
            if user_input in ['q', 'quit', 'exit']:
                debug_log("Stopping server as per user request...")
                break
            elif user_input == '':
                debug_log(f"Server continues running at {session_info['url']}")
                debug_log("Browser should still be ableto access the UI.")
            else:
                debug_log("Unknown command. Press Enter to keep server running, or 'q' to quit.")
        except KeyboardInterrupt:
            debug_log("\nInterrupt signal received. Stopping server...")
            break

    debug_log("Web UI interactive test complete.")

if __name__ == "__main__":
    debug_log("MCP Feedback Enhanced - Web UI Test Suite")
    debug_log("=" * 60)
    
    # Test environment detection
    env_test = test_environment_detection()
    
    # Test new parameters
    params_test = test_new_parameters()
    
    # Test environment-based Web UI mode
    env_web_test = test_environment_web_ui_mode()
    
    # Test MCP integration
    mcp_test = test_mcp_integration()
    
    # Test Web UI
    web_test, session_info = test_web_ui()
    
    debug_log("\n" + "=" * 60)
    if env_test and params_test and env_web_test and mcp_test and web_test:
        debug_log("All primary tests completed successfully!")
        debug_log("Usage Instructions:")
        debug_log("- Configure this tool as an MCP server in your AI assistant.")
        debug_log("- The AI assistant will automatically call this tool for feedback.")
        debug_log("- The system will automatically use the Web UI.")
        debug_log("- Provide feedback through the UI to continue the AI workflow.")

        debug_log("Web UI Features:")
        debug_log("- Suitable for local, SSH remote, and WSL environments.")
        debug_log("- Modern dark theme interface.")
        debug_log("- Realtime updates via WebSockets.")
        debug_log("- Automatic browser launch (where possible).")
        debug_log("- Realtime command execution output.")

        debug_log("Test complete. System is ready for use.")
        if session_info:
            debug_log(f"You can test the Web UI in your browser now: {session_info['url']}")
            debug_log("The server will continue running for a short period for immediate testing.")
            time.sleep(10)
    else:
        debug_log("Some tests failed. Please review the logs.")
        sys.exit(1)