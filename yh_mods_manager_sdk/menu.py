"""
菜单相关类型定义
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class PluginType(Enum):
    """插件类型枚举
    
    GAME: 游戏插件，互斥，同一时间仅能启用一个
    FEATURE: 功能插件，不互斥，可同时启用多个
    """
    GAME = "game"
    FEATURE = "feature"


@dataclass
class PluginMenuItem:
    """插件菜单项"""
    id: str
    label: str
    action_id: str = ""
    shortcut: str = ""
    enabled: bool = True
    separator_before: bool = False
    submenu_items: List["PluginMenuItem"] = field(default_factory=list)
