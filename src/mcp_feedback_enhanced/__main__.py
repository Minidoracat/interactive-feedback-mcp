#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP Interactive Feedback Enhanced - 主程式入口
==============================================

此檔案允許套件透過 `python -m mcp_feedback_enhanced` 執行。

使用方法:
  python -m mcp_feedback_enhanced        # 啟動 MCP 伺服器
  python -m mcp_feedback_enhanced test   # 執行測試
"""

import sys
import argparse
import os

def main():
    """主程式入口點"""
    parser = argparse.ArgumentParser(
        description="MCP Feedback Enhanced Enhanced - 互動式回饋收集 MCP 伺服器"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 伺服器命令（預設）
    server_parser = subparsers.add_parser('server', help='啟動 MCP 伺服器（預設）')
    
    # 測試命令
    test_parser = subparsers.add_parser('test', help='執行測試 (預設為 Web UI 測試)')
    test_parser.add_argument('--enhanced', action='store_true', help='執行增強 MCP 測試 (推薦)')
    test_parser.add_argument('--scenario', help='運行特定的測試場景')
    test_parser.add_argument('--tags', help='根據標籤運行測試場景 (逗號分隔)')
    test_parser.add_argument('--list-scenarios', action='store_true', help='列出所有可用的測試場景')
    test_parser.add_argument('--report-format', choices=['html', 'json', 'markdown'], help='報告格式')
    test_parser.add_argument('--timeout', type=int, help='測試超時時間 (秒)')
    
    # 版本命令
    version_parser = subparsers.add_parser('version', help='顯示版本資訊')
    
    args = parser.parse_args()
    
    if args.command == 'test':
        run_tests(args)
    elif args.command == 'version':
        show_version()
    elif args.command == 'server':
        run_server()
    elif args.command is None:
        run_server()
    else:
        # 不應該到達這裡
        parser.print_help()
        sys.exit(1)

def run_server():
    """啟動 MCP 伺服器"""
    from .server import main as server_main
    return server_main()

def run_tests(args):
    """執行測試"""
    # 啟用調試模式以顯示測試過程
    os.environ["MCP_DEBUG"] = "true"

    if args.enhanced or args.scenario or args.tags or args.list_scenarios:
        # 使用新的增強測試系統
        print("🚀 執行增強 MCP 測試系統...")
        import asyncio
        from .test_mcp_enhanced import MCPTestRunner, TestConfig

        # 創建配置
        config = TestConfig.from_env()
        if args.timeout:
            config.test_timeout = args.timeout
        if args.report_format:
            config.report_format = args.report_format

        runner = MCPTestRunner(config)

        async def run_enhanced_tests():
            try:
                if args.list_scenarios:
                    # 列出測試場景
                    tags = args.tags.split(',') if args.tags else None
                    runner.list_scenarios(tags)
                    return True

                success = False

                if args.scenario:
                    # 運行特定場景
                    success = await runner.run_single_scenario(args.scenario)
                elif args.tags:
                    # 根據標籤運行
                    tags = [tag.strip() for tag in args.tags.split(',')]
                    success = await runner.run_scenarios_by_tags(tags)
                else:
                    # 運行所有場景
                    success = await runner.run_all_scenarios()

                return success

            except Exception as e:
                print(f"❌ 增強測試執行失敗: {e}")
                return False

        success = asyncio.run(run_enhanced_tests())
        if not success:
            sys.exit(1)
    # Default to Web UI test if no specific test flags are provided
    else:
        print("🧪 執行 Web UI 測試 (預設)...")
        from .test_web_ui import test_web_ui, interactive_demo
        # The test_web_ui function itself should handle assertions and exit on failure.
        # We expect it to return a tuple (success_boolean, session_info_or_none)
        # For pytest compatibility, test_web_ui itself uses asserts.
        # Here, we might just call it. If it fails, it will internally assert or sys.exit.
        # However, the original structure checked success. Let's adapt.

        # Assuming test_web_ui now correctly uses asserts and will raise an error on failure,
        # or we adapt its return if necessary for this script's context.
        # For simplicity in this refactor, let's assume test_web_ui handles its own exit/error reporting.
        # If test_web_ui is meant to be called by pytest, it shouldn't sys.exit().
        # The original script structure implies test_web_ui returns success status.
        success, session_info = test_web_ui(standalone_run=True) # Pass the flag here
        if not success:
            print("❌ Web UI 測試失敗。")
            sys.exit(1)

        if session_info: # If test_web_ui starts a server for interactive demo
            print("📝 Web UI 測試完成，進入持續模式...")
            print("💡 提示：服務器將持續運行，可在瀏覽器中測試互動功能")
            print("💡 按 Ctrl+C 停止服務器")
            interactive_demo(session_info)
        else:
            print("✅ Web UI 測試通過！")


def show_version():
    """顯示版本資訊"""
    from . import __version__, __author__
    print(f"MCP Feedback Enhanced Enhanced v{__version__}")
    print(f"作者: {__author__}")
    print("GitHub: https://github.com/Minidoracat/mcp-feedback-enhanced")

if __name__ == "__main__":
    main() 