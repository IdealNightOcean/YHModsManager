"""
自定义序列化器模块
所有实体类的序列化逻辑集中在此文件
遵循单一职责原则：实体类仅存储数据，序列化逻辑独立管理

设计原则：
- 纯 dataclass 无需自定义序列化器，JsonSerializeManager 会自动处理
- 仅对有特殊序列化需求的类型创建自定义序列化器：
  - Set 转 List
  - 枚举类型转换
  - datetime 格式化
  - 嵌套对象特殊处理
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import asdict, is_dataclass
from datetime import datetime
from typing import Any, Dict, Type, TypeVar, Generic, TypeGuard, TYPE_CHECKING

if TYPE_CHECKING:
    from yh_mods_manager_sdk.config import PlatformPaths, PlatformPathMap

T = TypeVar('T')

logger = logging.getLogger(__name__)


class TypeSerializer(ABC, Generic[T]):
    """类型序列化器基类"""

    @abstractmethod
    def serialize(self, obj: T) -> Dict[str, Any]:
        pass

    @abstractmethod
    def deserialize(self, data: Dict[str, Any]) -> T:
        pass


def is_dataclass_instance(obj: object) -> TypeGuard[Any]:
    return hasattr(obj, "__dataclass_fields__")


class DataclassSerializer(TypeSerializer[T], Generic[T]):
    """通用 dataclass 序列化器"""

    def __init__(self, target_class: Type[T]):
        self._target_class = target_class

    def serialize(self, obj: T) -> Dict[str, Any]:
        if not is_dataclass_instance(obj):
            raise ValueError(f"Object {obj} is not a dataclass")

        return asdict(obj)

    def deserialize(self, data: Dict[str, Any]) -> T:
        if is_dataclass(self._target_class):
            return self._target_class(**data)
        raise ValueError(f"Class {self._target_class} is not a dataclass")


class ModCustomMetaSerializer(TypeSerializer):
    """ModCustomMeta 序列化器
    
    特殊处理：
    - Set[str] 转 List[str]
    - ModIssueStatus 转 int
    """

    def serialize(self, obj) -> Dict[str, Any]:
        return {
            "tags": list(obj.tags) if obj.tags else [],
            "custom_color": obj.custom_color,
            "custom_name": obj.custom_name,
            "note": obj.note,
            "ignored_issues": obj.ignored_issues.value if obj.ignored_issues else 0
        }

    def deserialize(self, data: Dict[str, Any]):
        from yh_mods_manager_sdk.enum_types import ModIssueStatus
        from yh_mods_manager_sdk import ModCustomMeta
        ignored_issues_value = data.get("ignored_issues", 0)
        ignored_issues = ModIssueStatus(ignored_issues_value) if ignored_issues_value else None
        return ModCustomMeta(
            tags=set(data.get("tags", [])),
            custom_color=data.get("custom_color"),
            custom_name=data.get("custom_name"),
            note=data.get("note"),
            ignored_issues=ignored_issues
        )


class SteamModInfoSerializer(TypeSerializer):
    """SteamModInfo 序列化器
    
    特殊处理：datetime 格式化
    """

    def serialize(self, obj) -> Dict[str, Any]:
        return {
            "workshop_id": obj.workshop_id,
            "title": obj.title,
            "update_time": obj.update_time.isoformat() if obj.update_time else None,
            "file_size": obj.file_size,
            "subscriptions": obj.subscriptions,
            "favorited": obj.favorited,
            "creator": obj.creator,
            "tags": obj.tags
        }

    def deserialize(self, data: Dict[str, Any]):
        from services.steam_service import SteamModInfo

        update_time = None
        if data.get("update_time"):
            try:
                update_time = datetime.fromisoformat(data["update_time"])
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to parse update_time '{data.get('update_time')}': {e}")

        return SteamModInfo(
            workshop_id=data.get("workshop_id", ""),
            title=data.get("title", ""),
            update_time=update_time,
            file_size=data.get("file_size", 0),
            subscriptions=data.get("subscriptions", 0),
            favorited=data.get("favorited", 0),
            creator=data.get("creator", ""),
            tags=data.get("tags", [])
        )


class PluginConfigSerializer(TypeSerializer):
    """PluginConfig 序列化器
    
    特殊处理：嵌套对象 GameInfo、PathValidation、ModParserConfig 的构建
    """

    def serialize(self, obj) -> Dict[str, Any]:
        return {
            "plugin_id": obj.plugin_id,
            "plugin_version": obj.plugin_version,
            "name": obj.name,
            "description": obj.description,
            "author": obj.author,
            "case_sensitive_id": obj.case_sensitive_id,
            "game_info": {
                "game_id": obj.game_info.game_id if obj.game_info else "",
                "steam_app_id": obj.game_info.steam_app_id if obj.game_info else "",
                "default_name": obj.game_info.default_name if obj.game_info else "",
                "version": obj.game_info.version if obj.game_info else "",
                "description": obj.game_info.description if obj.game_info else "",
                "icon": obj.game_info.icon if obj.game_info else "",
                "author": obj.game_info.author if obj.game_info else "",
                "website": obj.game_info.website if obj.game_info else ""
            },
            "path_validation": {
                "game_dir_path_markers": obj.path_validation.game_dir_path_markers if obj.path_validation else [],
                "mod_path_markers": obj.path_validation.mod_path_markers if obj.path_validation else [],
                "executable_paths": self._platform_paths_to_dict(
                    obj.path_validation.executable_paths) if obj.path_validation else {},
                "version_file": obj.path_validation.version_file if obj.path_validation else "",
                "required_paths": self._platform_path_map_to_dict(
                    obj.path_validation.required_paths) if obj.path_validation else {},
                "game_folder_names": self._platform_paths_to_dict(
                    obj.path_validation.game_folder_names) if obj.path_validation else {},
                "config_dir_paths": self._platform_paths_to_dict(
                    obj.path_validation.config_dir_paths) if obj.path_validation else {}
            },
            "mod_parser": {
                "game_core_folder": obj.mod_parser.game_core_folder if obj.mod_parser else "",
                "local_mods_folder": obj.mod_parser.local_mods_folder if obj.mod_parser else "",
                "game_core_id": obj.mod_parser.game_core_id if obj.mod_parser else "",
                "game_dlc_ids": obj.mod_parser.game_dlc_ids if obj.mod_parser else [],
                "mod_metadata_file": obj.mod_parser.mod_metadata_file if obj.mod_parser else ""
            },
            "default_settings": obj.default_settings,
            "custom_data": obj.custom_data,
        }

    def deserialize(self, data: Dict[str, Any]):
        from plugin_system.plugin_base import PluginConfig, GameInfo, PathValidation, ModParserConfig
        game_info_data = data.get("game_info", {})
        path_validation_data = data.get("path_validation", {})
        mod_parser_data = data.get("mod_parser", {})

        return PluginConfig(
            plugin_id=data.get("plugin_id", game_info_data.get("game_id", "")),
            plugin_version=data.get("plugin_version", "1.0.0"),
            name=data.get("name", ""),
            description=data.get("description", ""),
            author=data.get("author", ""),
            case_sensitive_id=data.get("case_sensitive_id", False),
            game_info=GameInfo(
                game_id=game_info_data.get("game_id", ""),
                default_name=game_info_data.get("default_name", ""),
                version=game_info_data.get("version", ""),
                description=game_info_data.get("description", ""),
                icon=game_info_data.get("icon", ""),
                author=game_info_data.get("author", ""),
                website=game_info_data.get("website", ""),
                steam_app_id=game_info_data.get("steam_app_id", "")
            ),
            path_validation=PathValidation.from_config(path_validation_data),
            mod_parser=ModParserConfig(
                game_core_folder=mod_parser_data.get("game_core_folder", ""),
                local_mods_folder=mod_parser_data.get("local_mods_folder", ""),
                game_core_id=mod_parser_data.get("game_core_id", ""),
                game_dlc_ids=mod_parser_data.get("game_dlc_ids", []),
                mod_metadata_file=mod_parser_data.get("mod_metadata_file", "")
            ),
            default_settings=data.get("default_settings", {}),
            custom_data=data.get("custom_data", {}),
        )

    @staticmethod
    def _platform_paths_to_dict(obj: "PlatformPaths") -> Dict[str, list]:
        """将 PlatformPaths 转换为字典"""
        return {
            "windows": obj.windows,
            "linux": obj.linux,
            "macos": obj.macos
        }

    @staticmethod
    def _platform_path_map_to_dict(obj: "PlatformPathMap") -> Dict[str, Dict[str, str]]:
        """将 PlatformPathMap 转换为字典"""
        return {
            "windows": obj.windows,
            "linux": obj.linux,
            "macos": obj.macos
        }


def register_all_serializers(manager):
    """注册所有自定义序列化器到管理器
    
    Args:
        manager: JsonSerializeManager 实例
    
    注意：仅注册有特殊序列化需求的类型
    纯 dataclass 类型无需注册，JsonSerializeManager 会自动处理
    """
    from yh_mods_manager_sdk import ModCustomMeta
    from services.steam_service import SteamModInfo
    from plugin_system.plugin_base import PluginConfig

    manager.register_serializer(ModCustomMeta, ModCustomMetaSerializer())
    manager.register_serializer(SteamModInfo, SteamModInfoSerializer())
    manager.register_serializer(PluginConfig, PluginConfigSerializer())
