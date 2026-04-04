"""
插件事件系统
支持插件订阅主程序事件，实现松耦合通信

此模块从SDK重新导出事件相关类型
"""

from yh_mods_manager_sdk import (
    PluginEventType,
    PluginEvent,
    PluginEventBus,
    EventHandler,
    get_event_bus,
)

__all__ = [
    'PluginEventType',
    'PluginEvent',
    'PluginEventBus',
    'EventHandler',
    'get_event_bus',
]
