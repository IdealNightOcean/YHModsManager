"""
主题管理模块
支持从JSON文件加载和切换主题
使用 JsonSerializeManager 统一管理 JSON 序列化

优化说明：
- 移除代码中的硬编码默认值，统一从主题JSON文件读取
- 所有默认值通过 _load_fallback_defaults() 从 default.json 加载
- 遵循 P3 规则：禁止硬编码，使用JSON配置
"""

import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from PyQt6.QtCore import pyqtSignal, QObject

from core.json_serializer import get_json_manager
from utils.file_utils import FileUtils, get_resource_path

logger = logging.getLogger(__name__)


@dataclass
class ThemeConfig:
    """主题配置"""
    id: str
    name: str
    version: str
    author: str
    colors: Dict[str, str] = field(default_factory=dict)
    border_radius: Dict[str, int] = field(default_factory=dict)
    badge: Dict[str, Dict[str, str]] = field(default_factory=list)
    dependency_colors: List[str] = field(default_factory=list)


_theme_manager: Optional["ThemeManager"] = None


class ThemeManager(QObject):
    """主题管理器
    
    优化说明：
    - 所有默认值从主题JSON文件加载，无硬编码
    - 当主题文件不存在时，使用最小化回退值
    - 回退颜色值从ui_constants.json读取，遵循P3/P4规则
    """

    theme_changed = pyqtSignal()

    _FALLBACK_BADGE_CONFIG = {
        "background": "surface_lighter",
        "text": "text_secondary",
        "border": "border",
        "font_weight": "normal"
    }

    def __init__(self, config_dir: str = "config", config_manager=None):
        super().__init__()
        self._config_dir = config_dir
        self._config_manager = config_manager
        self._themes_dir = os.path.join(config_dir, "themes")
        self._resource_themes_dir = get_resource_path(os.path.join("config", "themes"))
        self._current_theme: Optional[ThemeConfig] = None
        self._current_theme_key: str = "default"
        self._available_themes: Dict[str, str] = {}

        self._json = get_json_manager(config_dir)

        self._fallback_tag_default, self._fallback_dependency_colors = self._load_fallback_colors()

        self._default_colors, self._default_border_radius, self._default_badge, self._default_dependency_colors = self._load_default_theme_from_file()

        FileUtils.ensure_directory(self._themes_dir)
        self._scan_themes()

    @staticmethod
    def _load_fallback_colors() -> tuple:
        """从ui_constants.json加载回退颜色值"""
        from .styles import _load_ui_constants
        constants = _load_ui_constants()
        fallback = constants.get("fallback_colors", {})
        tag_default = fallback.get("tag_default", "#9CA3AF")
        dependency_colors = fallback.get("dependency_colors", ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4", "#FFEAA7"])
        return tag_default, dependency_colors

    def _load_default_theme_from_file(self) -> tuple:
        default_filepath = os.path.join(self._themes_dir, "default.json")
        if not os.path.exists(default_filepath):
            default_filepath = os.path.join(self._resource_themes_dir, "default.json")
        data = self._json.load_from_file(default_filepath, default=None)
        if data:
            return (
                data.get("colors", {}),
                data.get("border_radius", {}),
                data.get("badge", {}),
                data.get("dependency_colors", [])
            )
        return {}, {}, {}, []

    def _scan_themes(self):
        self._available_themes.clear()

        if os.path.exists(self._resource_themes_dir):
            for filename in os.listdir(self._resource_themes_dir):
                if filename.endswith(".json"):
                    filepath = os.path.join(self._resource_themes_dir, filename)
                    data = self._json.load_from_file(filepath, default=None)
                    if data:
                        theme_id = data.get("id", data.get("name", filename[:-5]).lower())
                        self._available_themes[theme_id] = filename

        if os.path.exists(self._themes_dir):
            for filename in os.listdir(self._themes_dir):
                if filename.endswith(".json"):
                    filepath = os.path.join(self._themes_dir, filename)
                    data = self._json.load_from_file(filepath, default=None)
                    if data:
                        theme_id = data.get("id", data.get("name", filename[:-5]).lower())
                        self._available_themes[theme_id] = filename

    @staticmethod
    def _deserialize_theme(data: dict) -> ThemeConfig:
        return ThemeConfig(
            id=data.get("id", data.get("name", "unknown").lower()),
            name=data.get("name", "Unknown"),
            version=data.get("version", "1.0.0"),
            author=data.get("author", ""),
            colors=data.get("colors", {}),
            border_radius=data.get("border_radius", {}),
            badge=data.get("badge", {}),
            dependency_colors=data.get("dependency_colors", [])
        )

    def get_theme_list(self) -> List[str]:
        return list(self._available_themes.keys())

    def get_theme_name(self, theme_id: str) -> str:
        if theme_id not in self._available_themes:
            return "Unknown"
        filename = self._available_themes[theme_id]
        filepath = os.path.join(self._themes_dir, filename)
        if not os.path.exists(filepath):
            filepath = os.path.join(self._resource_themes_dir, filename)
        data = self._json.load_from_file(filepath, default=None)
        if data:
            return data.get("name", theme_id)
        return theme_id

    def load_theme(self, theme_id: str) -> bool:
        if theme_id not in self._available_themes:
            return False

        filename = self._available_themes[theme_id]
        filepath = os.path.join(self._themes_dir, filename)
        if not os.path.exists(filepath):
            filepath = os.path.join(self._resource_themes_dir, filename)

        data = self._json.load_from_file(filepath, default=None)
        if data:
            self._current_theme = self._deserialize_theme(data)
            self._current_theme_key = theme_id
            if self._config_manager:
                self._config_manager.set_theme(theme_id)
            self.theme_changed.emit()
            return True
        return False

    def use_default_theme(self):
        if "light" in self._available_themes:
            self.load_theme("light")
        else:
            self._current_theme = ThemeConfig(
                id="default",
                name="Default",
                version="1.0.0",
                author="System",
                colors=self._default_colors.copy(),
                border_radius=self._default_border_radius.copy(),
                badge=self._default_badge.copy() if self._default_badge else self._FALLBACK_BADGE_CONFIG.copy()
            )
            self._current_theme_key = "default"
            self.theme_changed.emit()

    def get_color(self, key: str) -> str:
        if self._current_theme and key in self._current_theme.colors:
            return self._current_theme.colors[key]
        return self._default_colors.get(key, self.DEFAULT_COLOR)

    @property
    def DEFAULT_COLOR(self) -> str:
        if self._default_colors:
            return self._default_colors.get("tag_default", self._fallback_tag_default)
        return self._fallback_tag_default

    def get_border_radius(self, key: str) -> int:
        if self._current_theme and key in self._current_theme.border_radius:
            return self._current_theme.border_radius[key]
        return self._default_border_radius.get(key, 6)

    def get_badge_config(self, badge_type: str) -> Dict[str, str]:
        if self._current_theme and badge_type in self._current_theme.badge:
            return self._current_theme.badge[badge_type]
        if badge_type in self._default_badge:
            return self._default_badge[badge_type]
        return self._FALLBACK_BADGE_CONFIG.copy()

    def get_all_colors(self) -> Dict[str, str]:
        if self._current_theme:
            return self._current_theme.colors.copy()
        return self._default_colors.copy()

    def get_all_border_radius(self) -> Dict[str, int]:
        if self._current_theme:
            return self._current_theme.border_radius.copy()
        return self._default_border_radius.copy()

    def get_dependency_colors(self) -> List[str]:
        if self._current_theme and self._current_theme.dependency_colors:
            return self._current_theme.dependency_colors.copy()
        if self._default_dependency_colors:
            return self._default_dependency_colors.copy()
        return self._fallback_dependency_colors.copy()

    def get_tag_colors(self) -> Dict[str, str]:
        tag_keys = [
            "tag_important", "tag_recommended", "tag_testing", "tag_dependency",
            "tag_conflict", "tag_visual", "tag_gameplay", "tag_fix"
        ]
        return {key: self.get_color(key) for key in tag_keys}

    def get_color_options(self) -> Dict[str, str]:
        color_keys = [
            "color_red", "color_green", "color_blue", "color_yellow",
            "color_purple", "color_orange", "color_pink", "color_cyan"
        ]
        return {key: self.get_color(key) for key in color_keys}

    @property
    def current_theme_name(self) -> str:
        return self._current_theme.name if self._current_theme else "Default"

    @property
    def current_theme_id(self) -> str:
        return self._current_theme.id if self._current_theme else "default"

    @property
    def themes_dir(self) -> str:
        return self._themes_dir

    def refresh_themes(self):
        self._scan_themes()

    def load_saved_theme(self, config_manager):
        saved_theme = config_manager.get_theme()
        if saved_theme and saved_theme in self._available_themes:
            self.load_theme(saved_theme)
        else:
            self.use_default_theme()

    def init_app_theme(self, app, config_manager, font_size: int = 14):
        self.load_saved_theme(config_manager)
        from .styles import apply_theme
        apply_theme(app, font_size)

    def apply_theme_to_app(self) -> bool:
        """将当前主题应用到应用程序
        
        实现 SDK ThemeManagerProtocol 接口
        
        Returns:
            是否应用成功
        """
        try:
            from PyQt6.QtWidgets import QApplication
            from .styles import apply_theme

            app = QApplication.instance()
            if not app:
                return False

            font_size = 14
            if self._config_manager:
                font_size = self._config_manager.get_font_size()

            apply_theme(app, font_size)
            return True
        except Exception as e:
            logger.error(f"Failed to apply theme to app: {e}")
            return False


def init_theme_manager(config_dir: str = "config", config_manager=None) -> ThemeManager:
    global _theme_manager
    _theme_manager = ThemeManager(config_dir, config_manager)
    return _theme_manager


def get_theme_manager() -> ThemeManager:
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager


def get_color(key: str) -> str:
    return get_theme_manager().get_color(key)


def get_border_radius(key: str) -> int:
    return get_theme_manager().get_border_radius(key)


def get_dependency_colors() -> List[str]:
    return get_theme_manager().get_dependency_colors()


def get_tag_colors() -> Dict[str, str]:
    return get_theme_manager().get_tag_colors()


def get_color_options() -> Dict[str, str]:
    return get_theme_manager().get_color_options()
