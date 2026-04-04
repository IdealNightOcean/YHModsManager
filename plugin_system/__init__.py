"""
核心框架模块
提供插件基类、加载器和打包工具
支持双插件体系：游戏插件(互斥) + 功能插件(不互斥)

此模块作为桥接层：
- 从SDK导入类型定义、基类和事件系统
- 提供主程序特定的加载器和打包工具
"""

from yh_mods_manager_sdk import (
    ModType,
    ModIssueStatus,
    ListItemState,
    ListType,
    Platform,
    SearchField,
    StatusType,
    FrontType,
    GamePaths,
    GameInfo,
    PathValidation,
    PluginConfig,
    SaveParseResult,
    SaveParserCapability,
    PluginMenuItem,
    PluginType,
    PluginEventType,
    PluginEvent,
    PluginEventBus,
    EventHandler,
    get_event_bus,
    ManagerCollectionProtocol,
    ConfigManagerProtocol,
    ModManagerProtocol,
    GameMetadataManagerProtocol,
    ModMetadataManagerProtocol,
    HighlightRuleManagerProtocol,
    ModFilterManagerProtocol,
    IdComparerProtocol,
    PluginBase,
    GameAdapter,
    FeaturePlugin,
    GameDetectorBase,
    ModParserBase,
    ModIDUtils,
)

from .plugin_loader import (
    PluginLoader,
    PluginInfo,
    get_plugin_loader,
)

from .plugin_ui import (
    PluginPanelManager,
    init_panel_manager,
    get_panel_manager,
)

__all__ = [
    'ModType',
    'ModIssueStatus',
    'ListItemState',
    'ListType',
    'Platform',
    'SearchField',
    'StatusType',
    'FrontType',

    'GamePaths',
    'GameInfo',
    'PathValidation',
    'PluginConfig',
    'SaveParseResult',
    'SaveParserCapability',

    'PluginMenuItem',
    'PluginType',

    'PluginEventType',
    'PluginEvent',
    'PluginEventBus',
    'EventHandler',
    'get_event_bus',

    'ManagerCollectionProtocol',
    'ConfigManagerProtocol',
    'ModManagerProtocol',
    'GameMetadataManagerProtocol',
    'ModMetadataManagerProtocol',
    'HighlightRuleManagerProtocol',
    'ModFilterManagerProtocol',
    'IdComparerProtocol',

    'PluginBase',
    'GameAdapter',
    'FeaturePlugin',
    'GameDetectorBase',
    'ModParserBase',

    'ModIDUtils',

    'PluginLoader',
    'PluginInfo',
    'get_plugin_loader',

    'PluginPanelManager',
    'init_panel_manager',
    'get_panel_manager',
]
