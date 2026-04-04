"""
VibeUI Plugin SDK

插件开发SDK，提供插件开发所需的所有接口、类型定义和基类。
插件开发者只需安装此SDK即可开发插件，无需获取主程序源码。

安装方式：
    pip install vibe-ui-plugin-sdk

使用示例：
    from yh_mods_manager_sdk import FeaturePlugin, PluginEventType, Mod, ListType
    
    class MyPlugin(FeaturePlugin):
        PLUGIN_ID = "my_plugin"
        PLUGIN_NAME = "My Plugin"
        
        def on_initialize(self, manager_collection):
            mod_manager = manager_collection.get_mod_manager()
            mods = mod_manager.get_all_mods()
            return True, ""
"""

from .config import (
    GamePaths,
    GameInfo,
    PathValidation,
    PluginConfig,
    ModParserConfig,
    SaveParseResult,
    SaveParserCapability,
    GameMetadata,
    ModMetadata,
    PlatformPaths,
    PlatformPathMap,
    ModProfile,
)
from .enum_types import (
    ModType,
    ModIssueStatus,
    ListItemState,
    ListType,
    Platform,
    SearchField,
    StatusType,
    FrontType,
)
from .events import (
    PluginEventType,
    PluginEvent,
    PluginEventBus,
    EventHandler,
    get_event_bus,
)
from .menu import PluginMenuItem, PluginType
from .mod import Mod, ModCustomMeta
from .plugin_base import (
    PluginBase,
    GameAdapter,
    FeaturePlugin,
    GameDetectorBase,
    ModParserBase,
)
from .protocols import (
    ManagerCollectionProtocol,
    ConfigManagerProtocol,
    ModManagerProtocol,
    GameMetadataManagerProtocol,
    ModMetadataManagerProtocol,
    HighlightRuleManagerProtocol,
    ModFilterManagerProtocol,
    IdComparerProtocol,
    I18nProtocol,
    ThemeManagerProtocol,
)
from .utils import ModIDUtils, PlatformUtils, PluginResult
from .plugin_packer import (
    PluginPacker,
    pack_plugin,
    verify_plugin,
    PLUGIN_EXTENSION,
    PLUGIN_MANIFEST,
)

__version__ = "1.0.0"

__all__ = [
    # Types
    'Mod',
    'ModType',
    'ModIssueStatus',
    'ModCustomMeta',
    'ListItemState',
    'ListType',
    'Platform',
    'SearchField',
    'StatusType',
    'FrontType',

    # Config
    'GamePaths',
    'GameInfo',
    'PathValidation',
    'PluginConfig',
    'ModParserConfig',
    'SaveParseResult',
    'SaveParserCapability',
    'GameMetadata',
    'ModMetadata',
    'PlatformPaths',
    'PlatformPathMap',
    'ModProfile',

    # Menu
    'PluginMenuItem',
    'PluginType',

    # Events
    'PluginEventType',
    'PluginEvent',
    'PluginEventBus',
    'EventHandler',
    'get_event_bus',

    # Protocols
    'ManagerCollectionProtocol',
    'ConfigManagerProtocol',
    'ModManagerProtocol',
    'GameMetadataManagerProtocol',
    'ModMetadataManagerProtocol',
    'HighlightRuleManagerProtocol',
    'ModFilterManagerProtocol',
    'IdComparerProtocol',
    'I18nProtocol',
    'ThemeManagerProtocol',

    # Base Classes
    'PluginBase',
    'GameAdapter',
    'FeaturePlugin',
    'GameDetectorBase',
    'ModParserBase',

    # Utils
    'ModIDUtils',
    'PlatformUtils',
    'PluginResult',

    # Plugin Packer
    'PluginPacker',
    'pack_plugin',
    'verify_plugin',
    'PLUGIN_EXTENSION',
    'PLUGIN_MANIFEST',
]
