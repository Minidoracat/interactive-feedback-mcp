#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
圖片預覽元件
============

提供圖片預覽和刪除功能的自定義元件。
"""

import os
from PySide6.QtWidgets import QLabel, QPushButton, QFrame, QMessageBox
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap

# 導入多語系支援
from ...i18n import t


class ImagePreviewWidget(QLabel):
    """圖片預覽元件"""
    remove_clicked = Signal(str)
    
    def __init__(self, image_path: str, image_id: str, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.image_id = image_id
        self._setup_widget()
        self._load_image()
        self._create_delete_button()
    
    def _setup_widget(self) -> None:
        """設置元件基本屬性"""
        self.setFixedSize(100, 100)
        self.setFrameStyle(QFrame.Box)
        self.setStyleSheet("""
            QLabel {
                border: 2px solid #464647;
                border-radius: 8px;
                background-color: #2d2d30;
                padding: 2px;
            }
            QLabel:hover {
                border-color: #007acc;
                background-color: #383838;
            }
        """)
        self.setToolTip(t('imagePreview.tooltip', filename=os.path.basename(self.image_path)))
    
    def _load_image(self) -> None:
        """載入並顯示圖片"""
        try:
            pixmap = QPixmap(self.image_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(96, 96, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.setPixmap(scaled_pixmap)
                self.setAlignment(Qt.AlignCenter)
            else:
                self.setText(t('imagePreview.loadError'))
                self.setAlignment(Qt.AlignCenter)
        except Exception:
            self.setText(t('imagePreview.generalError'))
            self.setAlignment(Qt.AlignCenter)
    
    def _create_delete_button(self) -> None:
        """創建刪除按鈕"""
        self.delete_button = QPushButton("×", self)
        self.delete_button.setFixedSize(20, 20)
        self.delete_button.move(78, 2)
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: #ffffff;
                border: none;
                border-radius: 10px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { 
                background-color: #d32f2f; 
                color: #ffffff;
            }
        """)
        self.delete_button.clicked.connect(self._on_delete_clicked)
        self.delete_button.setToolTip(t('images.clear'))
        
    def _on_delete_clicked(self) -> None:
        """處理刪除按鈕點擊事件"""
        reply = QMessageBox.question(
            self, t('images.deleteTitle'), 
            t('images.deleteConfirm', filename=os.path.basename(self.image_path)),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.remove_clicked.emit(self.image_id) 