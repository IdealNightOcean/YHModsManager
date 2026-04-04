"""
全局事件总线模块
提供跨组件的事件通信机制，支持MOD状态变更、游戏切换等事件的订阅与发布
"""

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional

from PyQt6.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class EventType(Enum):
    """事件类型枚举"""
    MOD_STATE_CHANGED = auto()
    MOD_LOCAL_UPDATED = auto()
    MOD_DELETED = auto()
    MOD_ADDED = auto()
    GAME_CHANGED = auto()
    MOD_METADATA_CHANGED = auto()


@dataclass
class Event:
    """事件数据结构"""
    event_type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None

    @property
    def mod_id(self) -> Optional[str]:
        return self.data.get("mod_id")

    @property
    def game_id(self) -> Optional[str]:
        return self.data.get("game_id")


class EventBus(QObject):
    """全局事件总线
    
    使用单例模式，支持跨组件的事件通信。
    基于PyQt6的信号机制实现。
    """

    _instance: Optional["EventBus"] = None

    event_emitted = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self._listeners: Dict[EventType, List[Callable[[Event], None]]] = {
            event_type: [] for event_type in EventType
        }

    @classmethod
    def get_instance(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def subscribe(self, event_type: EventType, listener: Callable[[Event], None]):
        if listener not in self._listeners[event_type]:
            self._listeners[event_type].append(listener)

    def unsubscribe(self, event_type: EventType, listener: Callable[[Event], None]):
        if listener in self._listeners[event_type]:
            self._listeners[event_type].remove(listener)

    def emit(self, event: Event):
        for listener in self._listeners[event.event_type]:
            try:
                listener(event)
            except Exception as e:
                logger.error(f"Error in listener for {event.event_type}: {e}")

        self.event_emitted.emit(event)

    def emit_async(self, event: Event):
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self.emit(event))

    def emit_mod_state_changed(self, mod_id: str, is_enabled: bool, source: str = None):
        self.emit(Event(
            event_type=EventType.MOD_STATE_CHANGED,
            data={"mod_id": mod_id, "is_enabled": is_enabled},
            source=source
        ))

    def emit_mod_local_updated(self, mod_id: str, source: str = None):
        self.emit(Event(
            event_type=EventType.MOD_LOCAL_UPDATED,
            data={"mod_id": mod_id},
            source=source
        ))

    def emit_mod_deleted(self, mod_id: str, source: str = None):
        self.emit(Event(
            event_type=EventType.MOD_DELETED,
            data={"mod_id": mod_id},
            source=source
        ))

    def emit_mod_added(self, mod_id: str, source: str = None):
        self.emit(Event(
            event_type=EventType.MOD_ADDED,
            data={"mod_id": mod_id},
            source=source
        ))

    def emit_game_changed(self, game_id: str, source: str = None):
        self.emit(Event(
            event_type=EventType.GAME_CHANGED,
            data={"game_id": game_id},
            source=source
        ))

    def emit_mod_metadata_changed(self, mod_id: str, source: str = None):
        self.emit(Event(
            event_type=EventType.MOD_METADATA_CHANGED,
            data={"mod_id": mod_id},
            source=source
        ))

    def clear_all_listeners(self):
        for event_type in EventType:
            self._listeners[event_type].clear()


def get_event_bus() -> EventBus:
    return EventBus.get_instance()
