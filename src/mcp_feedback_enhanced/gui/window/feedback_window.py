#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
回饋收集主窗口（重構版）
========================

簡化的主窗口，專注於主要職責：窗口管理和協調各組件。
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTabWidget, QPushButton, QMessageBox, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Signal, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut

from .config_manager import ConfigManager
from .tab_manager import TabManager
from ..utils import apply_widget_styles
from ...i18n import t, get_i18n_manager
from ...debug import gui_debug_log as debug_log


class FeedbackWindow(QMainWindow):
    """回饋收集主窗口（重構版）"""
    language_changed = Signal()
    timeout_occurred = Signal()  # 超時發生信號

    def __init__(self, project_dir: str, summary: str, timeout_seconds: int = None):
        super().__init__()
        self.project_dir = project_dir
        self.summary = summary
        self.result = None
        self.i18n = get_i18n_manager()
        self.mcp_timeout_seconds = timeout_seconds  # MCP 傳入的超時時間

        # 初始化組件
        self.config_manager = ConfigManager()

        # 載入保存的語言設定
        saved_language = self.config_manager.get_language()
        if saved_language:
            self.i18n.set_language(saved_language)

        self.combined_mode = self.config_manager.get_layout_mode()
        self.layout_orientation = self.config_manager.get_layout_orientation()

        # 設置窗口狀態保存的防抖計時器
        self._save_timer = QTimer()
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._delayed_save_window_position)
        self._save_delay = 500  # 500ms 延遲，避免過於頻繁的保存

        # 設置UI
        self._setup_ui()
        self._setup_shortcuts()
        self._connect_signals()

        debug_log("主窗口初始化完成")

        # 如果啟用了超時，自動開始倒數計時
        self.start_timeout_if_enabled()

        # 設置定時器在窗口顯示後自動聚焦到輸入框（如果啟用）
        if self.config_manager.get_auto_focus_enabled():
            self._focus_timer = QTimer()
            self._focus_timer.setSingleShot(True)
            self._focus_timer.timeout.connect(self._auto_focus_input)
            self._focus_timer.start(300)  # 延遲300ms確保窗口和UI元素完全加載
        else:
            debug_log("自動聚焦已停用")

    def _setup_ui(self) -> None:
        """設置用戶介面"""
        self.setWindowTitle(t('app.title'))
        self.setMinimumSize(400, 300)  # 大幅降低最小窗口大小限制，允許用戶自由調整
        self.resize(1200, 900)

        # 智能視窗定位
        self._apply_window_positioning()

        # 中央元件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(16, 8, 16, 12)

        # 頂部專案目錄信息
        self._create_project_header(main_layout)

        # 分頁區域
        self._create_tab_area(main_layout)

        # 操作按鈕
        self._create_action_buttons(main_layout)

        # 應用深色主題
        self._apply_dark_style()

    def _create_project_header(self, layout: QVBoxLayout) -> None:
        """創建專案目錄頭部信息"""
        # 創建水平布局來放置專案目錄和倒數計時器
        header_layout = QHBoxLayout()

        self.project_label = QLabel(f"{t('app.projectDirectory')}: {self.project_dir}")
        self.project_label.setStyleSheet("color: #9e9e9e; font-size: 12px; padding: 4px 0;")
        header_layout.addWidget(self.project_label)

        # 添加彈性空間
        header_layout.addStretch()

        # 添加倒數計時器顯示（僅顯示部分）
        self._create_countdown_display(header_layout)

        # 將水平布局添加到主布局
        header_widget = QWidget()
        header_widget.setLayout(header_layout)
        layout.addWidget(header_widget)

    def _create_countdown_display(self, layout: QHBoxLayout) -> None:
        """創建倒數計時器顯示組件（僅顯示）"""
        # 倒數計時器標籤
        self.countdown_label = QLabel(t('timeout.remaining'))
        self.countdown_label.setStyleSheet("color: #cccccc; font-size: 12px;")
        self.countdown_label.setVisible(False)  # 預設隱藏
        layout.addWidget(self.countdown_label)

        # 倒數計時器顯示
        self.countdown_display = QLabel("--:--")
        self.countdown_display.setStyleSheet("""
            color: #ffa500;
            font-size: 14px;
            font-weight: bold;
            font-family: 'Consolas', 'Monaco', monospace;
            min-width: 50px;
            margin-left: 8px;
        """)
        self.countdown_display.setVisible(False)  # 預設隱藏
        layout.addWidget(self.countdown_display)

        # 初始化超時控制邏輯
        self._init_timeout_logic()

    def _init_timeout_logic(self) -> None:
        """初始化超時控制邏輯"""
        # 載入保存的超時設置
        timeout_enabled, timeout_duration = self.config_manager.get_timeout_settings()

        # 如果有 MCP 超時參數，且用戶設置的時間大於 MCP 時間，則使用 MCP 時間
        if self.mcp_timeout_seconds is not None:
            if timeout_duration > self.mcp_timeout_seconds:
                timeout_duration = self.mcp_timeout_seconds
                debug_log(f"用戶設置的超時時間 ({timeout_duration}s) 大於 MCP 超時時間 ({self.mcp_timeout_seconds}s)，使用 MCP 時間")

        # 保存超時設置
        self.timeout_enabled = timeout_enabled
        self.timeout_duration = timeout_duration
        self.remaining_seconds = 0

        # 創建計時器
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self._update_countdown)

        # 更新顯示狀態
        self._update_countdown_visibility()



    def _create_tab_area(self, layout: QVBoxLayout) -> None:
        """創建分頁區域"""
        # 創建滾動區域來包裝整個分頁組件
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setMinimumHeight(150)  # 降低滾動區域最小高度，支持小窗口
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #464647;
                border-radius: 4px;
                background-color: #2b2b2b;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #2b2b2b;
            }
            QScrollArea QScrollBar:vertical {
                background-color: #2a2a2a;
                width: 8px;
                border-radius: 4px;
                margin: 0;
            }
            QScrollArea QScrollBar::handle:vertical {
                background-color: #555;
                border-radius: 4px;
                min-height: 20px;
                margin: 1px;
            }
            QScrollArea QScrollBar::handle:vertical:hover {
                background-color: #777;
            }
            QScrollArea QScrollBar::add-line:vertical,
            QScrollArea QScrollBar::sub-line:vertical {
                border: none;
                background: none;
                height: 0px;
            }
            QScrollArea QScrollBar:horizontal {
                background-color: #2a2a2a;
                height: 8px;
                border-radius: 4px;
                margin: 0;
            }
            QScrollArea QScrollBar::handle:horizontal {
                background-color: #555;
                border-radius: 4px;
                min-width: 20px;
                margin: 1px;
            }
            QScrollArea QScrollBar::handle:horizontal:hover {
                background-color: #777;
            }
            QScrollArea QScrollBar::add-line:horizontal,
            QScrollArea QScrollBar::sub-line:horizontal {
                border: none;
                background: none;
                width: 0px;
            }
        """)

        self.tab_widget = QTabWidget()
        self.tab_widget.setMinimumHeight(150)  # 降低分頁組件最小高度
        # 設置分頁組件的大小策略，確保能觸發滾動
        self.tab_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # 初始化分頁管理器
        self.tab_manager = TabManager(
            self.tab_widget,
            self.project_dir,
            self.summary,
            self.combined_mode,
            self.layout_orientation
        )

        # 創建分頁
        self.tab_manager.create_tabs()

        # 連接分頁信號
        self.tab_manager.connect_signals(self)

        # 將分頁組件放入滾動區域
        scroll_area.setWidget(self.tab_widget)

        layout.addWidget(scroll_area, 1)

    def _create_action_buttons(self, layout: QVBoxLayout) -> None:
        """創建操作按鈕"""
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # 取消按鈕
        self.cancel_button = QPushButton(t('buttons.cancel'))
        self.cancel_button.clicked.connect(self._cancel_feedback)
        self.cancel_button.setFixedSize(130, 40)
        apply_widget_styles(self.cancel_button, "secondary_button")
        button_layout.addWidget(self.cancel_button)

        # 提交按鈕
        self.submit_button = QPushButton(t('buttons.submit'))
        self.submit_button.clicked.connect(self._submit_feedback)
        self.submit_button.setFixedSize(160, 40)
        self.submit_button.setDefault(True)
        apply_widget_styles(self.submit_button, "success_button")
        button_layout.addWidget(self.submit_button)

        layout.addLayout(button_layout)

    def _setup_shortcuts(self) -> None:
        """設置快捷鍵"""
        # Ctrl+Enter (主鍵盤) 提交回饋
        submit_shortcut_main = QShortcut(QKeySequence("Ctrl+Return"), self)
        submit_shortcut_main.activated.connect(self._submit_feedback)

        # Ctrl+Enter (數字鍵盤) 提交回饋
        submit_shortcut_keypad = QShortcut(QKeySequence(Qt.Modifier.CTRL | Qt.Key.Key_Enter), self)
        submit_shortcut_keypad.activated.connect(self._submit_feedback)

        # macOS 支援 Cmd+Return (主鍵盤)
        submit_shortcut_mac_main = QShortcut(QKeySequence("Meta+Return"), self)
        submit_shortcut_mac_main.activated.connect(self._submit_feedback)

        # macOS 支援 Cmd+Enter (數字鍵盤)
        submit_shortcut_mac_keypad = QShortcut(QKeySequence(Qt.Modifier.META | Qt.Key.Key_Enter), self)
        submit_shortcut_mac_keypad.activated.connect(self._submit_feedback)

        # Escape 取消回饋
        cancel_shortcut = QShortcut(QKeySequence(Qt.Key_Escape), self)
        cancel_shortcut.activated.connect(self._cancel_feedback)

    def _connect_signals(self) -> None:
        """連接信號"""
        # 連接語言變更信號
        self.language_changed.connect(self._refresh_ui_texts)

        # 連接分頁管理器的信號
        self.tab_manager.connect_signals(self)

    def _apply_dark_style(self) -> None:
        """應用深色主題"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #464647;
                border-radius: 8px;
                margin-top: 1ex;
                padding: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QTextEdit {
                background-color: #2d2d30;
                border: 1px solid #464647;
                border-radius: 4px;
                padding: 8px;
                color: #ffffff;
            }
            QLineEdit {
                background-color: #2d2d30;
                border: 1px solid #464647;
                border-radius: 4px;
                padding: 8px;
                color: #ffffff;
            }
            QTabWidget::pane {
                border: 1px solid #464647;
                border-radius: 4px;
                background-color: #2b2b2b;
            }
            QTabBar::tab {
                background-color: #2d2d30;
                color: #ffffff;
                border: 1px solid #464647;
                padding: 8px 16px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #007acc;
            }
            QSplitter {
                background-color: #2b2b2b;
            }
            QSplitter::handle {
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 3px;
                margin: 0px;
            }
            QSplitter::handle:horizontal {
                width: 6px;
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 3px;
                margin: 0px;
            }
            QSplitter::handle:vertical {
                height: 6px;
                background-color: #3c3c3c;
                border: 1px solid #555555;
                border-radius: 3px;
                margin: 0px;
            }
            QSplitter::handle:hover {
                background-color: #606060;
                border-color: #808080;
            }
            QSplitter::handle:pressed {
                background-color: #007acc;
                border-color: #005a9e;
            }
        """)

    def _on_layout_change_requested(self, combined_mode: bool, orientation: str) -> None:
        """處理佈局變更請求（模式和方向同時變更）"""
        try:
            # 保存當前內容
            current_data = self.tab_manager.get_feedback_data()

            # 記住當前分頁索引
            current_tab_index = self.tab_widget.currentIndex()

            # 保存新設置
            self.combined_mode = combined_mode
            self.layout_orientation = orientation
            self.config_manager.set_layout_mode(combined_mode)
            self.config_manager.set_layout_orientation(orientation)

            # 重新創建分頁
            self.tab_manager.set_layout_mode(combined_mode)
            self.tab_manager.set_layout_orientation(orientation)
            self.tab_manager.create_tabs()

            # 恢復內容
            self.tab_manager.restore_content(
                current_data["interactive_feedback"],
                current_data["command_logs"],
                current_data["images"]
            )

            # 重新連接信號
            self.tab_manager.connect_signals(self)

            # 刷新UI文字
            self._refresh_ui_texts()

            # 恢復到設定頁面（通常是倒數第二個分頁）
            if self.combined_mode:
                # 合併模式：回饋、命令、設置、關於
                settings_tab_index = 2
            else:
                # 分離模式：回饋、摘要、命令、設置、關於
                settings_tab_index = 3

            # 確保索引在有效範圍內
            if settings_tab_index < self.tab_widget.count():
                self.tab_widget.setCurrentIndex(settings_tab_index)

            mode_text = "合併模式" if combined_mode else "分離模式"
            orientation_text = "（水平布局）" if orientation == "horizontal" else "（垂直布局）"
            if combined_mode:
                mode_text += orientation_text
            debug_log(f"佈局已切換到: {mode_text}")

        except Exception as e:
            debug_log(f"佈局變更失敗: {e}")
            QMessageBox.warning(self, t('errors.title'), t('errors.interfaceReloadError', error=str(e)))



    def _on_reset_settings_requested(self) -> None:
        """處理重置設定請求"""
        try:
            # 重置配置管理器的所有設定
            self.config_manager.reset_settings()

            # 重置應用程式狀態
            self.combined_mode = False  # 重置為分離模式
            self.layout_orientation = 'vertical'  # 重置為垂直布局

            # 重新設置語言為預設
            self.i18n.set_language('zh-TW')

            # 保存當前內容
            current_data = self.tab_manager.get_feedback_data()

            # 重新創建分頁
            self.tab_manager.set_layout_mode(self.combined_mode)
            self.tab_manager.set_layout_orientation(self.layout_orientation)
            self.tab_manager.create_tabs()

            # 恢復內容
            self.tab_manager.restore_content(
                current_data["interactive_feedback"],
                current_data["command_logs"],
                current_data["images"]
            )

            # 重新連接信號
            self.tab_manager.connect_signals(self)

            # 重新載入設定分頁的狀態
            if self.tab_manager.settings_tab:
                self.tab_manager.settings_tab.reload_settings_from_config()

            # 刷新UI文字
            self._refresh_ui_texts()

            # 重新應用視窗定位（使用重置後的設定）
            self._apply_window_positioning()

            # 切換到設定分頁顯示重置結果
            settings_tab_index = 3  # 分離模式下設定分頁是第4個（索引3）
            if settings_tab_index < self.tab_widget.count():
                self.tab_widget.setCurrentIndex(settings_tab_index)

            # 顯示成功訊息
            QMessageBox.information(
                self,
                t('settings.reset.successTitle'),
                t('settings.reset.successMessage'),
                QMessageBox.Ok
            )

            debug_log("設定重置成功")

        except Exception as e:
            debug_log(f"重置設定失敗: {e}")
            QMessageBox.critical(
                self,
                t('errors.title'),
                t('settings.reset.error', error=str(e)),
                QMessageBox.Ok
            )

    def _submit_feedback(self) -> None:
        """提交回饋"""
        # 獲取所有回饋數據
        data = self.tab_manager.get_feedback_data()

        self.result = data
        debug_log(f"回饋提交: 文字長度={len(data['interactive_feedback'])}, "
                  f"命令日誌長度={len(data['command_logs'])}, "
                  f"圖片數量={len(data['images'])}")

        # 關閉窗口
        self.close()

    def _cancel_feedback(self) -> None:
        """取消回饋收集"""
        debug_log("取消回饋收集")
        self.result = ""
        self.close()

    def force_close(self) -> None:
        """強制關閉視窗（用於超時處理）"""
        debug_log("強制關閉視窗（超時）")
        self.result = ""
        self.close()

    def _on_timeout_occurred(self) -> None:
        """處理超時事件"""
        debug_log("用戶設置的超時時間已到，自動關閉視窗")
        self._timeout_occurred = True
        self.timeout_occurred.emit()
        self.force_close()

    def start_timeout_if_enabled(self) -> None:
        """如果啟用了超時，自動開始倒數計時"""
        if hasattr(self, 'tab_manager') and self.tab_manager:
            timeout_widget = self.tab_manager.get_timeout_widget()
            if timeout_widget:
                enabled, _ = timeout_widget.get_timeout_settings()
                if enabled:
                    timeout_widget.start_countdown()
                    debug_log("窗口顯示時自動開始倒數計時")

    def _on_timeout_settings_changed(self, enabled: bool, seconds: int) -> None:
        """處理超時設置變更（從設置頁籤觸發）"""
        # 檢查是否超過 MCP 超時限制
        if self.mcp_timeout_seconds is not None and seconds > self.mcp_timeout_seconds:
            debug_log(f"用戶設置的超時時間 ({seconds}s) 超過 MCP 限制 ({self.mcp_timeout_seconds}s)，調整為 MCP 時間")
            seconds = self.mcp_timeout_seconds

        # 更新內部狀態
        self.timeout_enabled = enabled
        self.timeout_duration = seconds

        # 保存設置
        self.config_manager.set_timeout_settings(enabled, seconds)
        debug_log(f"超時設置已更新: {'啟用' if enabled else '停用'}, {seconds} 秒")

        # 更新倒數計時器顯示
        self._update_countdown_visibility()

        # 重新開始倒數計時
        if enabled:
            self.start_countdown()
        else:
            self.stop_countdown()

    def start_timeout_if_enabled(self) -> None:
        """如果啟用了超時，開始倒數計時"""
        if self.timeout_enabled:
            self.start_countdown()
            debug_log("超時倒數計時已開始")

    def stop_timeout(self) -> None:
        """停止超時倒數計時"""
        self.stop_countdown()
        debug_log("超時倒數計時已停止")

    def start_countdown(self) -> None:
        """開始倒數計時"""
        if not self.timeout_enabled:
            return

        self.remaining_seconds = self.timeout_duration
        self.countdown_timer.start(1000)  # 每秒更新
        self._update_countdown_display()
        debug_log(f"開始倒數計時：{self.timeout_duration} 秒")

    def stop_countdown(self) -> None:
        """停止倒數計時"""
        self.countdown_timer.stop()
        self.countdown_display.setText("--:--")
        debug_log("倒數計時已停止")

    def _update_countdown(self) -> None:
        """更新倒數計時"""
        self.remaining_seconds -= 1
        self._update_countdown_display()

        if self.remaining_seconds <= 0:
            self.countdown_timer.stop()
            self._on_timeout_occurred()
            debug_log("倒數計時結束，觸發超時事件")

    def _update_countdown_display(self) -> None:
        """更新倒數顯示"""
        if self.remaining_seconds <= 0:
            self.countdown_display.setText("00:00")
            self.countdown_display.setStyleSheet("""
                color: #ff4444;
                font-size: 14px;
                font-weight: bold;
                font-family: 'Consolas', 'Monaco', monospace;
                min-width: 50px;
                margin-left: 8px;
            """)
        else:
            minutes = self.remaining_seconds // 60
            seconds = self.remaining_seconds % 60
            time_text = f"{minutes:02d}:{seconds:02d}"
            self.countdown_display.setText(time_text)

            # 根據剩餘時間調整顏色
            if self.remaining_seconds <= 60:  # 最後1分鐘
                color = "#ff4444"  # 紅色
            elif self.remaining_seconds <= 300:  # 最後5分鐘
                color = "#ffaa00"  # 橙色
            else:
                color = "#ffa500"  # 黃色

            self.countdown_display.setStyleSheet(f"""
                color: {color};
                font-size: 14px;
                font-weight: bold;
                font-family: 'Consolas', 'Monaco', monospace;
                min-width: 50px;
                margin-left: 8px;
            """)

    def _update_countdown_visibility(self) -> None:
        """更新倒數計時器可見性"""
        # 倒數計時器只在啟用超時時顯示
        self.countdown_label.setVisible(self.timeout_enabled)
        self.countdown_display.setVisible(self.timeout_enabled)

    def _refresh_ui_texts(self) -> None:
        """刷新界面文字"""
        self.setWindowTitle(t('app.title'))
        self.project_label.setText(f"{t('app.projectDirectory')}: {self.project_dir}")

        # 更新按鈕文字
        self.submit_button.setText(t('buttons.submit'))
        self.cancel_button.setText(t('buttons.cancel'))

        # 更新倒數計時器文字
        if hasattr(self, 'countdown_label'):
            self.countdown_label.setText(t('timeout.remaining'))

        # 更新分頁文字
        self.tab_manager.update_tab_texts()

    def _apply_window_positioning(self) -> None:
        """根據用戶設置應用視窗定位策略"""
        always_center = self.config_manager.get_always_center_window()

        if always_center:
            # 總是中心顯示模式：使用保存的大小（如果有的話），然後置中
            self._restore_window_size_only()
            self._move_to_primary_screen_center()
        else:
            # 智能定位模式：先嘗試恢復上次完整的位置和大小
            if self._restore_last_position():
                # 檢查恢復的位置是否可見
                if not self._is_window_visible():
                    self._move_to_primary_screen_center()
            else:
                # 沒有保存的位置，移到中心
                self._move_to_primary_screen_center()

    def _is_window_visible(self) -> bool:
        """檢查視窗是否在任何螢幕的可見範圍內"""
        from PySide6.QtWidgets import QApplication

        window_rect = self.frameGeometry()

        for screen in QApplication.screens():
            if screen.availableGeometry().intersects(window_rect):
                return True
        return False

    def _move_to_primary_screen_center(self) -> None:
        """將視窗移到主螢幕中心"""
        from PySide6.QtWidgets import QApplication

        screen = QApplication.primaryScreen()
        if screen:
            screen_geometry = screen.availableGeometry()
            window_geometry = self.frameGeometry()
            center_point = screen_geometry.center()
            window_geometry.moveCenter(center_point)
            self.move(window_geometry.topLeft())
            debug_log("視窗已移到主螢幕中心")

    def _restore_window_size_only(self) -> bool:
        """只恢復視窗大小（不恢復位置）"""
        try:
            geometry = self.config_manager.get_window_geometry()
            if geometry and 'width' in geometry and 'height' in geometry:
                self.resize(geometry['width'], geometry['height'])
                debug_log(f"已恢復視窗大小: {geometry['width']}x{geometry['height']}")
                return True
        except Exception as e:
            debug_log(f"恢復視窗大小失敗: {e}")
        return False

    def _restore_last_position(self) -> bool:
        """嘗試恢復上次保存的視窗位置和大小"""
        try:
            geometry = self.config_manager.get_window_geometry()
            if geometry and 'x' in geometry and 'y' in geometry and 'width' in geometry and 'height' in geometry:
                self.move(geometry['x'], geometry['y'])
                self.resize(geometry['width'], geometry['height'])
                debug_log(f"已恢復視窗位置: ({geometry['x']}, {geometry['y']}) 大小: {geometry['width']}x{geometry['height']}")
                return True
        except Exception as e:
            debug_log(f"恢復視窗位置失敗: {e}")
        return False

    def _save_window_position(self) -> None:
        """保存當前視窗位置和大小"""
        try:
            always_center = self.config_manager.get_always_center_window()

            # 獲取當前幾何信息
            current_geometry = {
                'width': self.width(),
                'height': self.height()
            }

            if not always_center:
                # 智能定位模式：同時保存位置
                current_geometry['x'] = self.x()
                current_geometry['y'] = self.y()
                debug_log(f"已保存視窗位置: ({current_geometry['x']}, {current_geometry['y']}) 大小: {current_geometry['width']}x{current_geometry['height']}")
            else:
                # 總是中心顯示模式：只保存大小，不保存位置
                debug_log(f"已保存視窗大小: {current_geometry['width']}x{current_geometry['height']} (總是中心顯示模式)")

            # 獲取現有配置，只更新需要的部分
            saved_geometry = self.config_manager.get_window_geometry() or {}
            saved_geometry.update(current_geometry)

            self.config_manager.set_window_geometry(saved_geometry)

        except Exception as e:
            debug_log(f"保存視窗狀態失敗: {e}")

    def resizeEvent(self, event) -> None:
        """窗口大小變化事件"""
        super().resizeEvent(event)
        # 窗口大小變化時始終保存（無論是否設置為中心顯示）
        if hasattr(self, 'config_manager'):
            self._schedule_save_window_position()

    def moveEvent(self, event) -> None:
        """窗口位置變化事件"""
        super().moveEvent(event)
        # 窗口位置變化只在智能定位模式下保存
        if hasattr(self, 'config_manager') and not self.config_manager.get_always_center_window():
            self._schedule_save_window_position()

    def _schedule_save_window_position(self) -> None:
        """調度窗口位置保存（防抖機制）"""
        if hasattr(self, '_save_timer'):
            self._save_timer.start(self._save_delay)

    def _delayed_save_window_position(self) -> None:
        """延遲保存窗口位置（防抖機制的實際執行）"""
        self._save_window_position()

    def _auto_focus_input(self) -> None:
        """自動聚焦到輸入框"""
        try:
            # 確保窗口已經顯示並激活
            self.raise_()
            self.activateWindow()

            # 獲取回饋輸入框（修正邏輯）
            feedback_input = None

            # 檢查是否有tab_manager
            if not hasattr(self, 'tab_manager'):
                debug_log("tab_manager 不存在")
                return

            # 檢查 feedback_tab（無論是合併模式還是分離模式）
            if hasattr(self.tab_manager, 'feedback_tab') and self.tab_manager.feedback_tab:
                if hasattr(self.tab_manager.feedback_tab, 'feedback_input'):
                    feedback_input = self.tab_manager.feedback_tab.feedback_input
                    debug_log("找到feedback_tab中的輸入框")
                else:
                    debug_log("feedback_tab存在但沒有feedback_input屬性")
            else:
                debug_log("沒有找到feedback_tab")

            # 設置焦點到輸入框
            if feedback_input:
                feedback_input.setFocus()
                feedback_input.raise_()  # 確保輸入框可見
                debug_log("已自動聚焦到輸入框")
            else:
                debug_log("未找到回饋輸入框，無法自動聚焦")
                # 打印調試信息
                if hasattr(self, 'tab_manager'):
                    debug_log(f"tab_manager 屬性: {dir(self.tab_manager)}")

        except Exception as e:
            debug_log(f"自動聚焦失敗: {e}")
            import traceback
            debug_log(f"詳細錯誤: {traceback.format_exc()}")

    def closeEvent(self, event) -> None:
        """窗口關閉事件"""
        # 最終保存視窗狀態（大小始終保存，位置根據設置決定）
        self._save_window_position()

        # 清理分頁管理器
        self.tab_manager.cleanup()
        event.accept()
        debug_log("主窗口已關閉")
