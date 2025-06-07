#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理器
===========

負責處理用戶配置的載入、保存和管理。
"""

import json
from pathlib import Path
from typing import Dict, Any

from ...debug import gui_debug_log as debug_log


class ConfigManager:
    """配置管理器"""

    def __init__(self):
        self._config_file = self._get_config_file_path()
        self._config_cache = {}
        self._load_config()

    def _get_config_file_path(self) -> Path:
        """獲取配置文件路徑"""
        config_dir = Path.home() / ".config" / "mcp-feedback-enhanced"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / "ui_settings.json"

    def _load_config(self) -> None:
        """載入配置"""
        try:
            if self._config_file.exists():
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    self._config_cache = json.load(f)
                debug_log("配置文件載入成功")
            else:
                self._config_cache = {}
                debug_log("配置文件不存在，使用預設配置")
        except Exception as e:
            debug_log(f"載入配置失敗: {e}")
            self._config_cache = {}

    def _save_config(self) -> None:
        """保存配置"""
        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config_cache, f, ensure_ascii=False, indent=2)
            debug_log("配置文件保存成功")
        except Exception as e:
            debug_log(f"保存配置失敗: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """獲取配置值"""
        return self._config_cache.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """設置配置值"""
        self._config_cache[key] = value
        self._save_config()

    def update_partial_config(self, updates: Dict[str, Any]) -> None:
        """批量更新配置項目，只保存指定的設定而不影響其他參數"""
        try:
            # 重新載入當前磁碟上的配置，確保我們有最新的數據
            current_config = {}
            if self._config_file.exists():
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    current_config = json.load(f)

            # 只更新指定的項目
            for key, value in updates.items():
                current_config[key] = value
                # 同時更新內存緩存
                self._config_cache[key] = value

            # 保存到文件
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(current_config, f, ensure_ascii=False, indent=2)

            debug_log(f"部分配置已更新: {list(updates.keys())}")

        except Exception as e:
            debug_log(f"更新部分配置失敗: {e}")

    def get_layout_mode(self) -> bool:
        """獲取佈局模式（False=分離模式，True=合併模式）"""
        return self.get('combined_mode', False)

    def set_layout_mode(self, combined_mode: bool) -> None:
        """設置佈局模式"""
        self.update_partial_config({'combined_mode': combined_mode})
        debug_log(f"佈局模式設置: {'合併模式' if combined_mode else '分離模式'}")

    def get_layout_orientation(self) -> str:
        """獲取佈局方向（vertical=垂直（上下），horizontal=水平（左右））"""
        return self.get('layout_orientation', 'vertical')

    def set_layout_orientation(self, orientation: str) -> None:
        """設置佈局方向"""
        if orientation not in ['vertical', 'horizontal']:
            orientation = 'vertical'
        self.update_partial_config({'layout_orientation': orientation})
        debug_log(f"佈局方向設置: {'垂直（上下）' if orientation == 'vertical' else '水平（左右）'}")

    def get_language(self) -> str:
        """獲取語言設置"""
        return self.get('language', 'zh-TW')

    def set_language(self, language: str) -> None:
        """設置語言"""
        self.update_partial_config({'language': language})
        debug_log(f"語言設置: {language}")

    def get_splitter_sizes(self, splitter_name: str) -> list:
        """獲取分割器尺寸"""
        sizes = self.get(f'splitter_sizes.{splitter_name}', [])
        if sizes:
            debug_log(f"載入分割器 {splitter_name} 尺寸: {sizes}")
        return sizes

    def set_splitter_sizes(self, splitter_name: str, sizes: list) -> None:
        """設置分割器尺寸"""
        self.update_partial_config({f'splitter_sizes.{splitter_name}': sizes})
        debug_log(f"保存分割器 {splitter_name} 尺寸: {sizes}")

    def get_window_geometry(self) -> dict:
        """獲取窗口幾何信息"""
        geometry = self.get('window_geometry', {})
        if geometry:
            debug_log(f"載入窗口幾何信息: {geometry}")
        return geometry

    def set_window_geometry(self, geometry: dict) -> None:
        """設置窗口幾何信息（使用部分更新避免覆蓋其他設定）"""
        self.update_partial_config({'window_geometry': geometry})
        debug_log(f"保存窗口幾何信息: {geometry}")

    def get_always_center_window(self) -> bool:
        """獲取總是在主螢幕中心顯示視窗的設置"""
        return self.get('always_center_window', False)

    def set_always_center_window(self, always_center: bool) -> None:
        """設置總是在主螢幕中心顯示視窗"""
        self.update_partial_config({'always_center_window': always_center})
        debug_log(f"視窗定位設置: {'總是中心顯示' if always_center else '智能定位'}")

    def get_image_size_limit(self) -> int:
        """獲取圖片大小限制（bytes），0 表示無限制"""
        return self.get('image_size_limit', 0)

    def set_image_size_limit(self, size_bytes: int) -> None:
        """設置圖片大小限制（bytes），0 表示無限制"""
        # 處理 None 值
        if size_bytes is None:
            size_bytes = 0

        self.update_partial_config({'image_size_limit': size_bytes})
        size_mb = size_bytes / (1024 * 1024) if size_bytes > 0 else 0
        debug_log(f"圖片大小限制設置: {'無限制' if size_bytes == 0 else f'{size_mb:.1f}MB'}")

    def get_enable_base64_detail(self) -> bool:
        """獲取是否啟用 Base64 詳細模式"""
        return self.get('enable_base64_detail', False)

    def set_enable_base64_detail(self, enabled: bool) -> None:
        """設置是否啟用 Base64 詳細模式"""
        self.update_partial_config({'enable_base64_detail': enabled})
        debug_log(f"Base64 詳細模式設置: {'啟用' if enabled else '停用'}")

    def get_timeout_enabled(self) -> bool:
        """獲取是否啟用超時自動關閉"""
        return self.get('timeout_enabled', False)

    def set_timeout_enabled(self, enabled: bool) -> None:
        """設置是否啟用超時自動關閉"""
        self.update_partial_config({'timeout_enabled': enabled})
        debug_log(f"超時自動關閉設置: {'啟用' if enabled else '停用'}")

    def get_timeout_duration(self) -> int:
        """獲取超時時間（秒）"""
        return self.get('timeout_duration', 600)  # 預設10分鐘

    def set_timeout_duration(self, seconds: int) -> None:
        """設置超時時間（秒）"""
        self.update_partial_config({'timeout_duration': seconds})
        debug_log(f"超時時間設置: {seconds} 秒")

    def get_timeout_settings(self) -> tuple[bool, int]:
        """獲取超時設置（啟用狀態, 超時時間）"""
        return self.get_timeout_enabled(), self.get_timeout_duration()

    def set_timeout_settings(self, enabled: bool, seconds: int) -> None:
        """設置超時設置"""
        self.update_partial_config({
            'timeout_enabled': enabled,
            'timeout_duration': seconds
        })
        debug_log(f"超時設置: {'啟用' if enabled else '停用'}, {seconds} 秒")

    def get_auto_focus_enabled(self) -> bool:
        """獲取是否啟用自動聚焦到輸入框"""
        return self.get('auto_focus_enabled', True)  # 預設啟用

    def set_auto_focus_enabled(self, enabled: bool) -> None:
        """設置是否啟用自動聚焦到輸入框"""
        self.update_partial_config({'auto_focus_enabled': enabled})
        debug_log(f"自動聚焦設置: {'啟用' if enabled else '停用'}")

    def reset_settings(self) -> None:
        """重置所有設定到預設值"""
        try:
            # 清空配置緩存
            self._config_cache = {}

            # 刪除配置文件
            if self._config_file.exists():
                self._config_file.unlink()
                debug_log("配置文件已刪除")

            debug_log("所有設定已重置到預設值")

        except Exception as e:
            debug_log(f"重置設定失敗: {e}")
            raise
