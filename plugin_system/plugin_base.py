"""
插件基类模块
支持双插件体系：游戏插件 + 功能插件

此模块作为桥接层：
- 从SDK导入基类和类型定义
- 提供主程序特定的加载器和打包工具

遵循插件系统需求文档规范：
- 游戏元数据 ≠ Mod元数据，完全独立
- 插件负责读取输出，主程序负责管理分发
- 通信仅传递管理者，不传递离散数据

双插件体系规则：
- 游戏插件(GameAdapter)：互斥，同一时间仅能启用一个
- 功能插件(FeaturePlugin)：不互斥，可同时启用多个
- 功能插件与游戏插件不互斥，可混合启用
"""

import logging

from yh_mods_manager_sdk import (
    ModType,
    ModIssueStatus,
    GamePaths,
    GameInfo,
    PathValidation,
    PluginConfig,
    ModParserConfig,
    SaveParseResult,
    SaveParserCapability,
    PluginMenuItem,
    PluginType,
    PluginBase,
    GameAdapter,
    FeaturePlugin,
    GameDetectorBase,
    ModParserBase,
    PlatformPaths,
    PlatformPathMap,
)

logger = logging.getLogger(__name__)

__all__ = [
    'ModType',
    'ModIssueStatus',
    'GamePaths',
    'GameInfo',
    'PathValidation',
    'PluginConfig',
    'ModParserConfig',
    'SaveParseResult',
    'SaveParserCapability',
    'PluginMenuItem',
    'PluginType',
    'PluginBase',
    'GameAdapter',
    'FeaturePlugin',
    'GameDetectorBase',
    'ModParserBase',
    'PlatformPaths',
    'PlatformPathMap',
]
