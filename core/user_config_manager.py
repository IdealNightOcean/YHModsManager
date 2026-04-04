"""
用户配置管理模块
管理用户自定义标签、颜色等配置
使用 JsonSerializeManager 统一管理 JSON 序列化
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .json_serializer import get_json_manager


@dataclass
class TagConfig:
    """标签配置"""
    name: str
    color: str
    enabled: bool = True


@dataclass
class ColorOption:
    """颜色选项"""
    name_key: str
    color: str
    enabled: bool = True
    custom_name: str = ""


def _get_default_tags_from_theme() -> List[TagConfig]:
    from ui.theme_manager import get_tag_colors
    tag_colors = get_tag_colors()
    return [TagConfig(name, color) for name, color in tag_colors.items()]


def _get_default_colors_from_theme() -> List[ColorOption]:
    from ui.theme_manager import get_color_options
    color_options = get_color_options()
    return [ColorOption(name, color) for name, color in color_options.items()]


class UserConfigManager:
    """用户配置管理器"""

    CONFIG_FILE = "user_config.json"

    @property
    def DEFAULT_TAGS(self) -> List[TagConfig]:
        return _get_default_tags_from_theme()

    @property
    def DEFAULT_COLORS(self) -> List[ColorOption]:
        return _get_default_colors_from_theme()

    def __init__(self, config_dir: str = "config"):
        self.config_dir = config_dir
        self.config_file_path = os.path.join(config_dir, self.CONFIG_FILE)

        self._json = get_json_manager(config_dir)

        self.tags: List[TagConfig] = []
        self.colors: List[ColorOption] = []
        self.custom_tag_colors: Dict[str, str] = {}

        self._load_config()

    def _load_config(self):
        data = self._json.load_from_file(self.config_file_path, default=None)

        if data:
            self.tags = [self._deserialize_tag(t) for t in data.get("tags", [])]
            self.colors = [self._deserialize_color(c) for c in data.get("colors", [])]
            self.custom_tag_colors = data.get("custom_tag_colors", {})
        else:
            self._reset_to_defaults()

        self._ensure_defaults()

    @staticmethod
    def _serialize_tag(tag: TagConfig) -> dict:
        return {"name": tag.name, "color": tag.color, "enabled": tag.enabled}

    @staticmethod
    def _deserialize_tag(data: dict) -> TagConfig:
        from ui.theme_manager import get_theme_manager
        default_color = get_theme_manager().DEFAULT_COLOR
        return TagConfig(
            name=data.get("name", ""),
            color=data.get("color", default_color),
            enabled=data.get("enabled", True)
        )

    @staticmethod
    def _serialize_color(color: ColorOption) -> dict:
        result = {"name_key": color.name_key, "color": color.color, "enabled": color.enabled}
        if color.custom_name:
            result["custom_name"] = color.custom_name
        return result

    @staticmethod
    def _deserialize_color(data: dict) -> ColorOption:
        from ui.theme_manager import get_theme_manager
        default_color = get_theme_manager().DEFAULT_COLOR
        return ColorOption(
            name_key=data.get("name_key", ""),
            color=data.get("color", default_color),
            enabled=data.get("enabled", True),
            custom_name=data.get("custom_name", "")
        )

    def _reset_to_defaults(self):
        self.tags = [TagConfig(t.name, t.color, t.enabled) for t in self.DEFAULT_TAGS]
        self.colors = [ColorOption(c.name_key, c.color, c.enabled) for c in self.DEFAULT_COLORS]
        self.custom_tag_colors = {}
        self.save_config()

    def _ensure_defaults(self):
        existing_color_names = {c.name_key for c in self.colors}
        for default_color in self.DEFAULT_COLORS:
            if default_color.name_key not in existing_color_names:
                self.colors.append(ColorOption(default_color.name_key, default_color.color, True))

        self.save_config()

    def save_config(self):
        data = {
            "tags": [self._serialize_tag(t) for t in self.tags],
            "colors": [self._serialize_color(c) for c in self.colors],
            "custom_tag_colors": self.custom_tag_colors,
        }
        self._json.save_to_file(data, self.config_file_path)

    def get_all_tags(self) -> List[TagConfig]:
        return self.tags.copy()

    def get_enabled_tags(self) -> List[TagConfig]:
        return [t for t in self.tags if t.enabled]

    def get_tag(self, name: str) -> Optional[TagConfig]:
        for tag in self.tags:
            if tag.name == name:
                return tag
        return None

    def get_tag_color(self, tag_name: str) -> Optional[str]:
        if tag_name in self.custom_tag_colors:
            return self.custom_tag_colors[tag_name]

        for tag in self.tags:
            if tag.name == tag_name or tag.name.endswith(f"_{tag_name}"):
                return tag.color

        return None

    def add_tag(self, name: str, color: str) -> bool:
        for tag in self.tags:
            if tag.name == name:
                return False

        self.tags.append(TagConfig(name, color, True))
        self.custom_tag_colors[name] = color
        self.save_config()
        return True

    def remove_tag(self, name: str) -> bool:
        self.tags = [t for t in self.tags if t.name != name]
        if name in self.custom_tag_colors:
            del self.custom_tag_colors[name]
        self.save_config()
        return True

    def set_tag_enabled(self, name: str, enabled: bool) -> bool:
        for tag in self.tags:
            if tag.name == name:
                tag.enabled = enabled
                self.save_config()
                return True
        return False

    def update_tag_color(self, name: str, color: str) -> bool:
        for tag in self.tags:
            if tag.name == name:
                tag.color = color
                self.custom_tag_colors[name] = color
                self.save_config()
                return True
        return False

    def get_all_colors(self) -> List[ColorOption]:
        return self.colors.copy()

    def get_enabled_colors(self) -> List[ColorOption]:
        return [c for c in self.colors if c.enabled]

    def add_color(self, name_key: str, color: str, custom_name: str = "") -> bool:
        for c in self.colors:
            if c.color.lower() == color.lower():
                return False

        self.colors.append(ColorOption(name_key, color, True, custom_name))
        self.save_config()
        return True

    def remove_color(self, color: str) -> bool:
        default_colors = {c.color.lower() for c in self.DEFAULT_COLORS}
        if color.lower() in default_colors:
            return self.set_color_enabled(color, False)

        self.colors = [c for c in self.colors if c.color.lower() != color.lower()]
        self.save_config()
        return True

    def set_color_enabled(self, color: str, enabled: bool) -> bool:
        for c in self.colors:
            if c.color.lower() == color.lower():
                c.enabled = enabled
                self.save_config()
                return True
        return False

    def update_color(self, old_color: str, new_color: str) -> bool:
        for c in self.colors:
            if c.color.lower() == old_color.lower():
                c.color = new_color
                self.save_config()
                return True
        return False

    def update_color_custom_name(self, color: str, custom_name: str) -> bool:
        for c in self.colors:
            if c.color.lower() == color.lower():
                c.custom_name = custom_name
                self.save_config()
                return True
        return False

    def get_color_list(self) -> List[Tuple[str, str]]:
        from ui.i18n import tr
        return [(tr(c.name_key), c.color) for c in self.get_enabled_colors()]

    def reset_tags_to_default(self):
        self.tags = [TagConfig(t.name, t.color, True) for t in self.DEFAULT_TAGS]
        self.save_config()

    def reset_colors_to_default(self):
        self.colors = [ColorOption(c.name_key, c.color, True) for c in self.DEFAULT_COLORS]
        self.save_config()

    def reset_all_to_default(self):
        self._reset_to_defaults()


_config_instance: Optional[UserConfigManager] = None


def init_user_config(config_dir: str = "config") -> UserConfigManager:
    global _config_instance
    _config_instance = UserConfigManager(config_dir)
    return _config_instance


def get_user_config() -> UserConfigManager:
    global _config_instance
    if _config_instance is None:
        _config_instance = UserConfigManager()
    return _config_instance
