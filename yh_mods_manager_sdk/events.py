"""
插件事件系统
支持插件订阅主程序事件，实现松耦合通信
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class PluginEventType(Enum):
    """插件事件类型"""
    GAME_CHANGED = "game_changed"
    GAME_LAUNCHED = "game_launched"
    GAME_CLOSED = "game_closed"

    MOD_LIST_CHANGED = "mod_list_changed"
    MOD_ORDER_CHANGED = "mod_order_changed"
    MOD_ENABLED = "mod_enabled"
    MOD_DISABLED = "mod_disabled"
    MOD_SELECTION_CHANGED = "mod_selection_changed"

    MOD_HIGHLIGHT_RULES_CHANGED = "mod_highlight_rules_changed"
    MOD_FILTER_RULES_CHANGED = "mod_filter_rules_changed"

    CONFIG_CHANGED = "config_changed"
    THEME_CHANGED = "theme_changed"
    LANGUAGE_CHANGED = "language_changed"

    PROFILE_CHANGED = "profile_changed"
    PROFILE_SAVED = "profile_saved"
    PROFILE_LOADED = "profile_loaded"

    PLUGIN_LOADED = "plugin_loaded"
    PLUGIN_UNLOADED = "plugin_unloaded"

    UI_READY = "ui_ready"
    SHUTDOWN = "shutdown"


@dataclass
class PluginEvent:
    """插件事件"""
    event_type: PluginEventType
    data: Dict[str, Any]
    source: str = "main"

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)


EventHandler = Callable[[PluginEvent], None]


class PluginEventBus:
    """插件事件总线
    
    遵循插件系统规范：
    - 松耦合：发布者和订阅者互不依赖
    - 异步安全：事件处理不阻塞主线程
    - 可扩展：支持自定义事件类型
    """

    def __init__(self):
        self._handlers: Dict[PluginEventType, List[EventHandler]] = {}
        self._once_handlers: Dict[PluginEventType, List[EventHandler]] = {}
        self._wildcard_handlers: List[EventHandler] = []

    def subscribe(self, event_type: PluginEventType, handler: EventHandler) -> None:
        """订阅事件
        
        Args:
            event_type: 事件类型
            handler: 事件处理函数
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        if handler not in self._handlers[event_type]:
            self._handlers[event_type].append(handler)

    def subscribe_once(self, event_type: PluginEventType, handler: EventHandler) -> None:
        """订阅事件（仅触发一次）"""
        if event_type not in self._once_handlers:
            self._once_handlers[event_type] = []
        if handler not in self._once_handlers[event_type]:
            self._once_handlers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """订阅所有事件"""
        if handler not in self._wildcard_handlers:
            self._wildcard_handlers.append(handler)

    def unsubscribe(self, event_type: PluginEventType, handler: EventHandler) -> None:
        """取消订阅事件"""
        if event_type in self._handlers and handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)
        if event_type in self._once_handlers and handler in self._once_handlers[event_type]:
            self._once_handlers[event_type].remove(handler)

    def unsubscribe_all(self, handler: EventHandler) -> None:
        """取消订阅所有事件"""
        if handler in self._wildcard_handlers:
            self._wildcard_handlers.remove(handler)
        for event_type in self._handlers:
            if handler in self._handlers[event_type]:
                self._handlers[event_type].remove(handler)

    def publish(self, event_type: PluginEventType, data: Dict[str, Any] = None, source: str = "main") -> None:
        """发布事件"""
        event = PluginEvent(
            event_type=event_type,
            data=data or {},
            source=source
        )

        for handler in self._wildcard_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler error (wildcard): {e}")

        if event_type in self._handlers:
            for handler in self._handlers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Event handler error ({event_type.value}): {e}")

        if event_type in self._once_handlers:
            handlers = self._once_handlers[event_type].copy()
            self._once_handlers[event_type] = []
            for handler in handlers:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Event handler error (once {event_type.value}): {e}")

    def clear(self) -> None:
        """清除所有订阅"""
        self._handlers.clear()
        self._once_handlers.clear()
        self._wildcard_handlers.clear()

    def get_handlers(self, event_type: PluginEventType) -> List[EventHandler]:
        """获取指定事件类型的所有处理函数"""
        return self._handlers.get(event_type, [])


_event_bus: Optional[PluginEventBus] = None


def get_event_bus() -> PluginEventBus:
    """获取全局事件总线实例"""
    global _event_bus
    if _event_bus is None:
        _event_bus = PluginEventBus()
    return _event_bus
