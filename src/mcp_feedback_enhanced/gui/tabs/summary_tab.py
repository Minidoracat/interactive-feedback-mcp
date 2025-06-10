#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
摘要分頁組件
============

專門顯示AI工作摘要的分頁組件。
"""

import json
import markdown
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit

from ...i18n import t


class SummaryTab(QWidget):
    """摘要分頁組件"""

    def __init__(self, summary: str, parent=None):
        super().__init__(parent)
        self.summary = self._process_summary(summary)
        self._setup_ui()

    def _process_summary(self, summary: str) -> str:
        """處理摘要內容，如果是JSON格式則提取實際內容"""
        try:
            # 嘗試解析JSON
            if summary.strip().startswith("{") and summary.strip().endswith("}"):
                json_data = json.loads(summary)
                # 如果是JSON格式，提取summary字段的內容
                if isinstance(json_data, dict) and "summary" in json_data:
                    return json_data["summary"]
                # 如果JSON中沒有summary字段，返回原始內容
                return summary
            else:
                return summary
        except (json.JSONDecodeError, TypeError):
            # 如果不是有效的JSON，返回原始內容
            return summary

    def _render_markdown(self, text: str) -> str:
        """Convert markdown text to HTML"""
        try:
            # Convert markdown to HTML with safe settings
            html = markdown.markdown(
                text,
                extensions=["fenced_code", "tables", "nl2br"],
                output_format="html5",
            )
            return html
        except Exception as e:
            # Fallback to plain text if markdown parsing fails
            print(f"Markdown rendering failed: {e}")
            return text.replace("\n", "<br>")

    def _setup_ui(self) -> None:
        """設置用戶介面"""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 16, 0, 0)  # 只保留上邊距，移除左右和底部邊距

        # 說明文字容器
        description_wrapper = QWidget()
        description_layout = QVBoxLayout(description_wrapper)
        description_layout.setContentsMargins(16, 0, 16, 0)  # 只對說明文字設置左右邊距
        description_layout.setSpacing(0)

        # 說明文字
        if self._is_test_summary():
            self.summary_description_label = QLabel(t("summary.testDescription"))
        else:
            self.summary_description_label = QLabel(t("summary.description"))

        self.summary_description_label.setStyleSheet(
            "color: #9e9e9e; font-size: 12px; margin-bottom: 10px;"
        )
        self.summary_description_label.setWordWrap(True)
        description_layout.addWidget(self.summary_description_label)

        layout.addWidget(description_wrapper)

        # 摘要顯示區域容器
        summary_wrapper = QWidget()
        summary_layout = QVBoxLayout(summary_wrapper)
        summary_layout.setContentsMargins(16, 0, 16, 0)  # 只對摘要區域設置左右邊距
        summary_layout.setSpacing(0)

        # 摘要顯示區域
        self.summary_display = QTextEdit()
        # 檢查是否為測試摘要，如果是則使用翻譯的內容
        if self._is_test_summary():
            test_content = t("test.qtGuiSummary")
            self.summary_display.setHtml(self._render_markdown(test_content))
        else:
            self.summary_display.setHtml(self._render_markdown(self.summary))

        self.summary_display.setReadOnly(True)
        self.summary_display.setStyleSheet(
            """
            QTextEdit {
                background-color: #2d2d30;
                border: 1px solid #464647;
                border-radius: 4px;
                padding: 10px;
                color: #ffffff;
                font-size: 12px;
                line-height: 1.4;
            }
        """
        )
        summary_layout.addWidget(self.summary_display, 1)

        layout.addWidget(summary_wrapper, 1)

    def _is_test_summary(self) -> bool:
        """檢查是否為測試摘要"""
        # 更精確的測試摘要檢測 - 必須包含特定的測試指標組合
        test_patterns = [
            # Qt GUI 測試特徵組合 - 必須同時包含多個特徵
            ("圖片預覽和視窗調整測試", "功能測試項目", "🎯"),
            ("圖片預覽和窗口調整測試", "功能測試項目", "🎯"),
            ("图片预览和窗口调整测试", "功能测试项目", "🎯"),
            ("Image Preview and Window Adjustment Test", "Test Items", "🎯"),
            # Web UI 測試特徵組合
            ("測試 Web UI 功能", "🎯 **功能測試項目", "WebSocket 即時通訊"),
            ("测试 Web UI 功能", "🎯 **功能测试项目", "WebSocket 即时通讯"),
            (
                "Test Web UI Functionality",
                "🎯 **Test Items",
                "WebSocket real-time communication",
            ),
            # 具體的測試步驟特徵
            ("智能 Ctrl+V 圖片貼上功能", "📋 測試步驟", "請測試這些功能並提供回饋"),
            ("智能 Ctrl+V 图片粘贴功能", "📋 测试步骤", "请测试这些功能并提供回馈"),
            ("Smart Ctrl+V image paste", "📋 Test Steps", "Please test these features"),
        ]

        # 檢查是否匹配任何一個測試模式（必須同時包含模式中的所有關鍵詞）
        for pattern in test_patterns:
            if all(keyword in self.summary for keyword in pattern):
                return True

        return False

    def update_texts(self) -> None:
        """更新界面文字（用於語言切換）"""
        if self._is_test_summary():
            self.summary_description_label.setText(t("summary.testDescription"))
            # 更新測試摘要的內容
            test_content = t("test.qtGuiSummary")
            self.summary_display.setHtml(self._render_markdown(test_content))
        else:
            self.summary_description_label.setText(t("summary.description"))
