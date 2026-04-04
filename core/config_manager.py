"""
配置管理模块
使用 JsonSerializeManager 统一管理 JSON 序列化
"""

import logging
import os
import shutil
from datetime import datetime
from typing import Dict, Optional, Tuple

from yh_mods_manager_sdk import GamePaths, ModProfile
from utils.file_utils import FileUtils, get_app_data_dir
from utils.profile_serializer import ProfileSerializer
from .json_serializer import get_json_manager

logger = logging.getLogger(__name__)


class ConfigManager:
    """配置管理器"""

    CONFIG_DIR = "config"
    GAME_DATA_DIR = "game_data"
    PROFILES_DIR = "profiles"
    APP_SETTINGS_FILE = "app_settings.json"
    GAME_SETTINGS_FILE = "settings.json"
    METADATA_FILE = "mod_metadata.json"
    TOOL_NAME = "NightOcean's Mods Manager"

    DEFAULT_UI_SETTINGS = {
        "language": "zh_CN",
        "theme": "light",
        "font_size": 15,
        "last_game": "",
        "window_width": 1200,
        "window_height": 700,
        "window_maximized": True,
        "disabled_feature_plugins": [],
        "disable_update_check": False,
        "info_panel_sections": {
            "file_info": True,
            "load_requirements": True,
            "official_tags": True,
            "tags": True,
            "color": True,
            "note": True,
            "ignore_issues": True,
            "description": True
        }
    }

    DEFAULT_GAME_SETTINGS = {
        "game_dir_path": "",
        "workshop_dir_path": "",
        "local_mod_dir_path": "",
        "game_config_dir_path": "",
        "default_save_dir_path": "",
        "last_profile": "",
        "auto_sort": True,
        "launch_steam": True,
        "auto_detect_paths": True,
        "disable_steam_monitor": False,
        "custom_game_name": ""
    }

    @staticmethod
    def get_saved_language() -> str:
        app_dir = get_app_data_dir()
        config_dir = os.path.join(app_dir, "config")
        app_settings_path = os.path.join(config_dir, "app_settings.json")

        json_manager = get_json_manager(config_dir)
        settings = json_manager.load_from_file(app_settings_path, default={})
        return settings.get("language", "zh_CN")

    def __init__(self, app_data_dir: str = None, game_adapter=None, game_id: str = None):
        if app_data_dir:
            self.config_dir = os.path.join(app_data_dir, self.CONFIG_DIR)
            self.game_data_dir = os.path.join(app_data_dir, self.GAME_DATA_DIR)
        else:
            app_dir = get_app_data_dir()
            self.config_dir = os.path.join(app_dir, self.CONFIG_DIR)
            self.game_data_dir = os.path.join(app_dir, self.GAME_DATA_DIR)

        self.app_settings_path = os.path.join(self.config_dir, self.APP_SETTINGS_FILE)

        self._game_adapter = game_adapter
        self._current_game_id = game_id
        self._game_settings_path = None
        self._game_profiles_dir = None
        self._game_metadata_path = None

        self._json = get_json_manager(self.config_dir)

        self._ensure_directories()

        self.app_settings = self._load_app_settings()
        self.game_settings = {}
        self.profiles: Dict[str, ModProfile] = {}
        self._game_custom_name_cache: Dict[str, str] = {}

        if game_adapter:
            self.set_game_adapter(game_adapter)
        elif game_id:
            self.set_game_id(game_id)

    def set_game_adapter(self, game_adapter):
        self._game_adapter = game_adapter
        if game_adapter:
            game_info = game_adapter.get_game_info()
            if game_info:
                self._current_game_id = game_info.game_id
                self._init_game_dir_paths()
                self._ensure_game_directories()
                self.game_settings = self._load_game_settings()
                self.profiles = self._load_profiles()

    def set_game_id(self, game_id: str):
        self._current_game_id = game_id
        self._init_game_dir_paths()
        self._ensure_game_directories()
        self.game_settings = self._load_game_settings()
        self.profiles = self._load_profiles()

    def _init_game_dir_paths(self):
        if self._current_game_id:
            game_dir = os.path.join(self.game_data_dir, self._current_game_id)
            self._game_settings_path = os.path.join(game_dir, self.GAME_SETTINGS_FILE)
            self._game_profiles_dir = os.path.join(game_dir, self.PROFILES_DIR)
            self._game_metadata_path = os.path.join(game_dir, self.METADATA_FILE)
        else:
            self._game_settings_path = None
            self._game_profiles_dir = None
            self._game_metadata_path = None

    def _ensure_directories(self):
        FileUtils.ensure_directory(self.config_dir)
        FileUtils.ensure_directory(self.game_data_dir)

    def _ensure_game_directories(self):
        if self._game_profiles_dir:
            FileUtils.ensure_directory(os.path.dirname(self._game_settings_path))
            FileUtils.ensure_directory(self._game_profiles_dir)

    def _get_tool_name(self) -> str:
        if self._game_adapter:
            game_info = self._game_adapter.get_game_info()
            if game_info:
                return f"{game_info.default_name} - Mods Manager"
        return self.TOOL_NAME

    def _load_app_settings(self) -> dict:
        return self._json.load_with_defaults(
            self.app_settings_path,
            self.DEFAULT_UI_SETTINGS
        )

    def _save_app_settings(self):
        self._json.save_to_file(self.app_settings, self.app_settings_path)

    def _load_game_settings(self) -> dict:
        if not self._game_settings_path:
            default_settings = self.DEFAULT_GAME_SETTINGS.copy()
            if self._game_adapter:
                adapter_defaults = self._game_adapter.get_default_settings()
                if adapter_defaults:
                    default_settings.update(adapter_defaults)
            return default_settings

        default_settings = self.DEFAULT_GAME_SETTINGS.copy()
        if self._game_adapter:
            adapter_defaults = self._game_adapter.get_default_settings()
            if adapter_defaults:
                default_settings.update(adapter_defaults)

        return self._json.load_with_defaults(
            self._game_settings_path,
            default_settings
        )

    def _save_game_settings(self):
        if self._game_settings_path:
            self._json.save_to_file(self.game_settings, self._game_settings_path)

    def get_language(self) -> str:
        return self.app_settings.get("language", "zh_CN")

    def set_language(self, language: str):
        self.app_settings["language"] = language
        self._save_app_settings()

    def get_theme(self) -> str:
        return self.app_settings.get("theme", "light")

    def set_theme(self, theme: str):
        self.app_settings["theme"] = theme
        self._save_app_settings()

    def get_font_size(self) -> int:
        font_size = self.app_settings.get("font_size", 14)
        return max(4, font_size)

    def set_font_size(self, size: int):
        self.app_settings["font_size"] = max(4, size)
        self._save_app_settings()

    def get_last_game(self) -> str:
        return self.app_settings.get("last_game", "")

    def set_last_game(self, game_id: str):
        self.app_settings["last_game"] = game_id
        self._save_app_settings()

    def get_window_size(self) -> Tuple[int, int]:
        width = self.app_settings.get("window_width", 1200)
        height = self.app_settings.get("window_height", 700)
        return width, height

    def set_window_size(self, width: int, height: int):
        self.app_settings["window_width"] = width
        self.app_settings["window_height"] = height
        self._save_app_settings()

    def is_window_maximized(self) -> bool:
        return self.app_settings.get("window_maximized", True)

    def set_window_maximized(self, maximized: bool):
        self.app_settings["window_maximized"] = maximized
        self._save_app_settings()

    def get_disabled_feature_plugins(self) -> list:
        return self.app_settings.get("disabled_feature_plugins", [])

    def set_disabled_feature_plugins(self, plugin_ids: list):
        self.app_settings["disabled_feature_plugins"] = plugin_ids
        self._save_app_settings()

    def is_feature_plugin_disabled(self, plugin_id: str) -> bool:
        return plugin_id in self.get_disabled_feature_plugins()

    def set_feature_plugin_disabled(self, plugin_id: str, disabled: bool):
        disabled_plugins = self.get_disabled_feature_plugins()
        if disabled:
            if plugin_id not in disabled_plugins:
                disabled_plugins.append(plugin_id)
        else:
            if plugin_id in disabled_plugins:
                disabled_plugins.remove(plugin_id)
        self.set_disabled_feature_plugins(disabled_plugins)

    def get_info_panel_sections(self) -> dict:
        default_sections = self.DEFAULT_UI_SETTINGS.get("info_panel_sections", {})
        return self.app_settings.get("info_panel_sections", default_sections)

    def set_info_panel_sections(self, sections: dict):
        self.app_settings["info_panel_sections"] = sections
        self._save_app_settings()

    def is_info_panel_section_visible(self, section_key: str) -> bool:
        sections = self.get_info_panel_sections()
        return sections.get(section_key, True)

    def set_info_panel_section_visible(self, section_key: str, visible: bool):
        sections = self.get_info_panel_sections()
        sections[section_key] = visible
        self.set_info_panel_sections(sections)

    def get_game_dir_path(self) -> str:
        return self.game_settings.get("game_dir_path", "")

    def set_game_dir_path(self, path: str):
        self.game_settings["game_dir_path"] = path
        self._save_game_settings()

    def get_workshop_dir_path(self) -> str:
        return self.game_settings.get("workshop_dir_path", "")

    def set_workshop_dir_path(self, path: str):
        self.game_settings["workshop_dir_path"] = path
        self._save_game_settings()

    def get_config_dir_path(self) -> str:
        return self.game_settings.get("game_config_dir_path", "")

    def set_game_config_dir_path(self, path: str):
        self.game_settings["game_config_dir_path"] = path
        self._save_game_settings()

    def get_local_mod_dir_path(self) -> str:
        return self.game_settings.get("local_mod_dir_path", "")

    def set_local_mod_dir_path(self, path: str):
        self.game_settings["local_mod_dir_path"] = path
        self._save_game_settings()

    def get_custom_paths(self) -> Dict[str, str]:
        return self.game_settings.get("custom_paths", {})

    def set_custom_paths(self, paths: Dict[str, str]):
        self.game_settings["custom_paths"] = paths
        self._save_game_settings()

    def add_custom_path(self, key: str, path: str) -> bool:
        if not key or not path:
            return False
        custom_paths = self.get_custom_paths()
        custom_paths[key] = path
        self.set_custom_paths(custom_paths)
        return True

    def remove_custom_path(self, key: str) -> bool:
        custom_paths = self.get_custom_paths()
        if key in custom_paths:
            del custom_paths[key]
            self.set_custom_paths(custom_paths)
            return True
        return False

    def get_custom_path(self, key: str) -> Optional[str]:
        return self.get_custom_paths().get(key)

    def is_auto_detect_paths(self) -> bool:
        return self.game_settings.get("auto_detect_paths", True)

    def set_auto_detect_paths(self, auto: bool):
        self.game_settings["auto_detect_paths"] = auto
        self._save_game_settings()

    def is_auto_sort(self) -> bool:
        return self.game_settings.get("auto_sort", True)

    def set_auto_sort(self, auto: bool):
        self.game_settings["auto_sort"] = auto
        self._save_game_settings()

    def is_launch_steam(self) -> bool:
        return self.game_settings.get("launch_steam", True)

    def set_launch_steam(self, launch: bool):
        self.game_settings["launch_steam"] = launch
        self._save_game_settings()

    def is_steam_monitor_disabled(self) -> bool:
        return self.game_settings.get("disable_steam_monitor", False)

    def set_steam_monitor_disabled(self, disabled: bool):
        self.game_settings["disable_steam_monitor"] = disabled
        self._save_game_settings()

    def is_update_check_disabled(self) -> bool:
        return self.app_settings.get("disable_update_check", False)

    def set_update_check_disabled(self, disabled: bool):
        self.app_settings["disable_update_check"] = disabled
        self._save_app_settings()

    def get_custom_game_name(self) -> str:
        return self.game_settings.get("custom_game_name", "")

    def set_custom_game_name(self, name: str):
        self.game_settings["custom_game_name"] = name
        if self._current_game_id and self._current_game_id in self._game_custom_name_cache:
            del self._game_custom_name_cache[self._current_game_id]
        self._save_game_settings()

    def get_default_save_dir_path(self) -> str:
        return self.game_settings.get("default_save_dir_path", "")

    def set_default_save_dir_path(self, path: str):
        self.game_settings["default_save_dir_path"] = path
        self._save_game_settings()

    def get_display_game_name(self) -> str:
        custom_name = self.get_custom_game_name()
        if custom_name:
            return custom_name
        if self._game_adapter:
            game_info = self._game_adapter.get_game_info()
            if game_info:
                return game_info.default_name
        return ""

    def get_game_custom_name(self, game_id: str) -> str:
        if game_id in self._game_custom_name_cache:
            return self._game_custom_name_cache[game_id]

        settings_path = os.path.join(self.game_data_dir, game_id, self.GAME_SETTINGS_FILE)
        if os.path.exists(settings_path):
            settings = self._json.load_from_file(settings_path, default={})
            name = settings.get("custom_game_name", "")
            self._game_custom_name_cache[game_id] = name
            return name
        return ""

    def get_game_display_name(self, game_id: str, default_name: str = "") -> str:
        custom_name = self.get_game_custom_name(game_id)
        return custom_name if custom_name else default_name

    def get_game_dir_paths_with_detection(self, auto_replace: bool = False) -> GamePaths:
        game_paths = GamePaths(
            game_dir_path=self.get_game_dir_path(),
            workshop_dir_path=self.get_workshop_dir_path(),
            game_config_dir_path=self.get_config_dir_path(),
            local_mod_dir_path=self.get_local_mod_dir_path(),
            default_save_dir_path=self.get_default_save_dir_path(),
            custom_paths=self.get_custom_paths()
        )

        if self.is_auto_detect_paths() and self._game_adapter:
            try:
                detector = self._game_adapter.create_detector()
                detected = detector.detect_game_dir_paths()
                if detected.game_dir_path:
                    if auto_replace or not game_paths.game_dir_path:
                        self.set_game_dir_path(detected.game_dir_path)
                        game_paths.game_dir_path = detected.game_dir_path
                if detected.workshop_dir_path:
                    if auto_replace or not game_paths.workshop_dir_path:
                        self.set_workshop_dir_path(detected.workshop_dir_path)
                        game_paths.workshop_dir_path = detected.workshop_dir_path
                if detected.local_mod_dir_path:
                    if auto_replace or not game_paths.local_mod_dir_path:
                        self.set_local_mod_dir_path(detected.local_mod_dir_path)
                        game_paths.local_mod_dir_path = detected.local_mod_dir_path
                if detected.game_config_dir_path:
                    if auto_replace or not game_paths.game_config_dir_path:
                        self.set_game_config_dir_path(detected.game_config_dir_path)
                        game_paths.game_config_dir_path = detected.game_config_dir_path
                if detected.default_save_dir_path:
                    if auto_replace or not game_paths.default_save_dir_path:
                        self.set_default_save_dir_path(detected.default_save_dir_path)
                        game_paths.default_save_dir_path = detected.default_save_dir_path
                if detected.custom_paths:
                    if auto_replace or not game_paths.custom_paths:
                        self.set_custom_paths(detected.custom_paths)
                        game_paths.custom_paths = detected.custom_paths

            except Exception as e:
                logger.error(f"Plugin path detection failed: {e}")

        return game_paths

    def _load_profiles(self) -> Dict[str, ModProfile]:
        profiles = {}

        if not self._game_profiles_dir or not os.path.exists(self._game_profiles_dir):
            default_name = self._create_default_profile()
            if default_name:
                profiles[default_name] = self._load_profile_by_name(default_name)
            return profiles

        for filename in os.listdir(self._game_profiles_dir):
            if filename.endswith(".json"):
                profile_name = filename[:-5]
                filepath = os.path.join(self._game_profiles_dir, filename)
                data = self._json.load_from_file(filepath)
                if data:
                    profiles[profile_name] = ProfileSerializer.deserialize(data)

        if not profiles:
            default_name = self._create_default_profile()
            if default_name:
                profiles[default_name] = self._load_profile_by_name(default_name)

        return profiles

    def _load_profile_by_name(self, name: str) -> Optional[ModProfile]:
        if not self._game_profiles_dir:
            return None
        filename = ConfigManager._get_profile_filename(name)
        filepath = os.path.join(self._game_profiles_dir, filename)
        data = self._json.load_from_file(filepath)
        if data:
            return ProfileSerializer.deserialize(data)
        return None

    def _create_default_profile(self) -> Optional[str]:
        if not self._game_profiles_dir:
            return None
        FileUtils.ensure_directory(self._game_profiles_dir)
        default_name = "default"
        profile = ModProfile(description="默认配置方案", game_id=self._current_game_id or "")
        self._save_profile(default_name, profile)
        return default_name

    def create_profile(self, name: str, description: str = "") -> ModProfile:
        profile = ModProfile(description=description, game_id=self._current_game_id or "")
        self.profiles[name] = profile
        self._save_profile(name, profile)
        return profile

    def save_profile(self, name: str, profile: ModProfile, get_mod_by_id=None):
        profile.modified_at = datetime.now().isoformat()
        profile.game_id = self._current_game_id or profile.game_id
        self.profiles[name] = profile
        self._save_profile(name, profile, get_mod_by_id)

    def _save_profile(self, name: str, profile: ModProfile, get_mod_by_id=None):
        if not self._game_profiles_dir:
            return
        FileUtils.ensure_directory(self._game_profiles_dir)
        filename = ConfigManager._get_profile_filename(name)
        filepath = os.path.join(self._game_profiles_dir, filename)

        profile_data = ProfileSerializer.serialize(profile, get_mod_by_id)
        self._json.save_to_file(profile_data, filepath)

    def delete_profile(self, name: str) -> Tuple[bool, Optional[str]]:
        if name not in self.profiles:
            return False, None

        if not self._game_profiles_dir:
            return False, None

        filename = ConfigManager._get_profile_filename(name)
        filepath = os.path.join(self._game_profiles_dir, filename)

        FileUtils.delete_file(filepath)

        del self.profiles[name]

        next_profile_name = None
        if not self.profiles:
            default_name = self._create_default_profile()
            if default_name:
                self.profiles[default_name] = self._load_profile_by_name(default_name)
                next_profile_name = default_name
        else:
            next_profile_name = next(iter(self.profiles.keys()))

        return True, next_profile_name

    def rename_profile(self, old_name: str, new_name: str) -> bool:
        if old_name not in self.profiles:
            return False

        if not self._game_profiles_dir:
            return False

        if new_name in self.profiles:
            return False

        profile = self.profiles[old_name]

        old_filename = ConfigManager._get_profile_filename(old_name)
        old_filepath = os.path.join(self._game_profiles_dir, old_filename)

        FileUtils.delete_file(old_filepath, use_trash=False)

        self._save_profile(new_name, profile)
        del self.profiles[old_name]
        self.profiles[new_name] = profile

        return True

    def get_profile(self, name: str) -> Optional[ModProfile]:
        return self.profiles.get(name)

    def get_all_profiles(self) -> Dict[str, ModProfile]:
        return self.profiles.copy()

    def duplicate_profile(self, name: str, new_name: str) -> Optional[ModProfile]:
        original = self.profiles.get(name)
        if not original:
            return None

        new_profile = ModProfile(
            description=f"复制自 {name}",
            mod_order=original.mod_order.copy(),
            game_id=original.game_id
        )

        self.profiles[new_name] = new_profile
        self._save_profile(new_name, new_profile)
        return new_profile

    EXPORT_VERSION = "1.3"

    def export_current_mods(self, mod_order: list, export_path: str, get_mod_by_id=None) -> bool:
        game_id = self._current_game_id or "unknown"

        profile = ModProfile(
            description="",
            game_id=game_id,
            mod_order=mod_order
        )

        export_data = ProfileSerializer.serialize(profile, get_mod_by_id)

        return self._json.save_to_file(export_data, export_path)

    def export_profile(self, name: str, export_path: str, get_mod_by_id=None) -> bool:
        profile = self.profiles.get(name)
        if not profile:
            return False

        export_data = ProfileSerializer.serialize(profile, get_mod_by_id)

        return self._json.save_to_file(export_data, export_path)

    def import_profile(self, import_path: str) -> Optional[Tuple[str, ModProfile]]:
        data = self._json.load_from_file(import_path)
        if not data:
            return None

        if "profile" in data:
            profile_data = data["profile"]
        else:
            profile_data = data

        profile = ProfileSerializer.deserialize(profile_data)

        if "name" in data:
            base_name = data["name"]
        else:
            base_name = os.path.splitext(os.path.basename(import_path))[0]

        profile_name = base_name
        counter = 1
        while profile_name in self.profiles:
            profile_name = f"{base_name}_{counter}"
            counter += 1

        self.profiles[profile_name] = profile
        self._save_profile(profile_name, profile)

        return profile_name, profile

    @staticmethod
    def _get_profile_filename(name: str) -> str:
        safe_name = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in name)
        return f"{safe_name}.json"

    def get_last_profile_name(self) -> str:
        return self.game_settings.get("last_profile", "")

    def set_last_profile(self, name: str):
        self.game_settings["last_profile"] = name
        self._save_game_settings()

    def save_current_state(self, game_id: str = None, profile_name: str = None):
        if game_id:
            self.set_last_game(game_id)
        if profile_name:
            self.set_last_profile(profile_name)

    def restore_last_profile_with_fallback(self) -> Optional[Tuple[str, ModProfile]]:
        profiles = self.get_all_profiles()
        if not profiles:
            return None

        last_profile_name = self.get_last_profile_name()

        if last_profile_name and last_profile_name in profiles:
            return last_profile_name, profiles[last_profile_name]

        first_profile_name = next(iter(profiles.keys()))
        self.set_last_profile(first_profile_name)
        return first_profile_name, profiles[first_profile_name]

    def _get_metadata_path(self) -> str:
        return self._game_metadata_path

    def save_mod_metadata(self, mods: list):
        if not self._game_metadata_path:
            return
        from .serializers import ModCustomMetaSerializer
        serializer = ModCustomMetaSerializer()
        metadata = {}
        for mod in mods:
            meta_dict = serializer.serialize(mod.custom_meta)
            if any(meta_dict.values()):
                metadata[mod.id] = meta_dict

        self._json.save_to_file(metadata, self._game_metadata_path)

    def load_mod_metadata(self) -> dict:
        return self._json.load_from_file(self._game_metadata_path, default={})

    def export_mod_metadata(self, export_path: str, mods: list) -> bool:
        from .serializers import ModCustomMetaSerializer
        serializer = ModCustomMetaSerializer()
        metadata = {}
        for mod in mods:
            meta_dict = serializer.serialize(mod.custom_meta)
            if any(meta_dict.values()):
                metadata[mod.id] = {
                    "name": mod.name,
                    **meta_dict
                }

        game_id = self._current_game_id or "unknown"
        game_name = ""
        if self._game_adapter:
            game_info = self._game_adapter.get_game_info()
            if game_info:
                game_name = game_info.default_name

        export_data = {
            "version": self.EXPORT_VERSION,
            "exported_at": datetime.now().isoformat(),
            "tool": self._get_tool_name(),
            "game_id": game_id,
            "game_name": game_name,
            "type": "mod_metadata",
            "metadata": metadata
        }

        return self._json.save_to_file(export_data, export_path)

    def import_mod_metadata(self, import_path: str) -> Optional[dict]:
        data = self._json.load_from_file(import_path)
        if not data or data.get("type") != "mod_metadata":
            return None
        return data.get("metadata", {})

    @staticmethod
    def delete_mod(mod) -> bool:
        if not mod or not mod.path:
            return False

        try:
            if os.path.exists(mod.path):
                from send2trash import send2trash
                send2trash(mod.path)
                return True
        except (IOError, OSError, ImportError):
            try:
                if os.path.isfile(mod.path):
                    os.remove(mod.path)
                else:
                    shutil.rmtree(mod.path)
                return True
            except (IOError, OSError) as e:
                logger.warning(f"Failed to remove mod directory {mod.path}: {e}")
        return False

    def get_game_id(self) -> str:
        return self._current_game_id or ""
