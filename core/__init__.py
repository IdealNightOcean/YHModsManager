"""
核心业务模块
包含Mod数据模型、管理器、服务层等核心业务逻辑

遵循插件系统需求文档规范：
- 游戏元数据与Mod元数据独立管理
- 管理者集合统一维护插件依赖
"""

from yh_mods_manager_sdk import ModProfile
from yh_mods_manager_sdk.enum_types import ListType
from yh_mods_manager_sdk.enum_types import ModType, ModIssueStatus, ListItemState
from .config_manager import ConfigManager, GamePaths
from .dependency_resolver import DependencyResolver
from .json_serializer import JsonSerializeManager, get_json_manager, init_json_manager
from .manager_collection import (
    ManagerCollection,
    get_manager_collection,
    init_manager_collection,
    reset_manager_collection,
)
from .metadata_manager import (
    GameMetadata,
    ModMetadata,
    GameMetadataManager,
    ModMetadataManager,
)
from .mod_manager import ModManager
from .mod_operations import ModOperations
from .mod_parser import ModParser, create_mod_parser
from .mod_service import ModService
from .mod_types import ModOperationResult, ValidationResult
from .user_config_manager import (
    TagConfig,
    ColorOption,
    UserConfigManager,
    init_user_config,
    get_user_config,
)

__all__ = [
    'ModType',
    'ModIssueStatus',
    'ListItemState',
    'ModOperationResult',
    'ValidationResult',
    'ModManager',
    'ModService',
    'ModOperations',
    'ModParser',
    'create_mod_parser',
    'ConfigManager',
    'ModProfile',
    'GamePaths',
    'DependencyResolver',
    'ListType',
    'JsonSerializeManager',
    'get_json_manager',
    'init_json_manager',
    'GameMetadata',
    'ModMetadata',
    'GameMetadataManager',
    'ModMetadataManager',
    'ManagerCollection',
    'get_manager_collection',
    'init_manager_collection',
    'reset_manager_collection',
    'TagConfig',
    'ColorOption',
    'UserConfigManager',
    'init_user_config',
    'get_user_config',
]
