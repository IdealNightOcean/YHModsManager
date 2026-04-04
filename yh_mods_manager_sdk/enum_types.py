"""
核心类型定义模块

包含插件开发所需的所有核心数据类型。
这些类型定义与主程序完全一致，确保插件与主程序之间的数据兼容性。
"""

import enum
from enum import IntFlag, auto


class ModIssueStatus(IntFlag):
    """Mod问题状态 - 使用Flag枚举支持多个问题同时存在
    
    - INCOMPLETE: 文件不完整
    - CONFLICT: 冲突
    - MISSING_DEPENDENCIES: 缺失依赖

    - DUPLICATE: 重复Mod
    - ORDER_ERROR: 加载顺序错误
    - VERSION_MISMATCH: 版本不兼容
    """
    NORMAL = 0

    _STATIC_BIT = 1
    _DYNAMIC_BIT = 2
    _WARNING_BIT = 4
    _ERROR_BIT = 8
    _CUSTOM_BIT = 16

    _INCOMPLETE_BIT = 32
    _MISSING_DEP_BIT = 64
    _CONFLICT_BIT = 128
    _VERSION_MISMATCH_BIT = 256
    _DUPLICATE_BIT = 512
    _ORDER_ERROR_BIT = 1024

    INCOMPLETE = _INCOMPLETE_BIT | _STATIC_BIT | _ERROR_BIT
    VERSION_MISMATCH = _VERSION_MISMATCH_BIT | _STATIC_BIT | _WARNING_BIT
    DUPLICATE = _DUPLICATE_BIT | _STATIC_BIT | _WARNING_BIT
    CUSTOM_STATIC_ERROR = _CUSTOM_BIT | _STATIC_BIT | _ERROR_BIT
    CUSTOM_STATIC_WARNING = _CUSTOM_BIT | _STATIC_BIT | _WARNING_BIT

    ORDER_ERROR = _ORDER_ERROR_BIT | _DYNAMIC_BIT | _WARNING_BIT
    MISSING_DEPENDENCIES = _MISSING_DEP_BIT | _DYNAMIC_BIT | _ERROR_BIT
    CONFLICT = _CONFLICT_BIT | _DYNAMIC_BIT | _ERROR_BIT
    CUSTOM_DYNAMIC_ERROR = _CUSTOM_BIT | _DYNAMIC_BIT | _ERROR_BIT
    CUSTOM_DYNAMIC_WARNING = _CUSTOM_BIT | _DYNAMIC_BIT | _WARNING_BIT

    ALL_DYNAMIC = ORDER_ERROR | MISSING_DEPENDENCIES | CONFLICT | CUSTOM_DYNAMIC_ERROR | CUSTOM_DYNAMIC_WARNING
    ALL_STATIC = INCOMPLETE | VERSION_MISMATCH | DUPLICATE | CUSTOM_STATIC_ERROR | CUSTOM_STATIC_WARNING

    def has_issue(self, issue: "ModIssueStatus") -> bool:
        return (self & issue) == issue

    def has_error(self) -> bool:
        return bool(self & ModIssueStatus._ERROR_BIT)

    def has_warning(self) -> bool:
        return bool(self & ModIssueStatus._WARNING_BIT)

    def has_custom(self) -> bool:
        return bool(self & ModIssueStatus._CUSTOM_BIT)

    def has_static(self) -> bool:
        return bool(self & ModIssueStatus._STATIC_BIT)

    def has_dynamic(self) -> bool:
        return bool(self & ModIssueStatus._DYNAMIC_BIT)


class ListItemState(IntFlag):
    """列表项状态 - 使用组合枚举统一管理"""
    NONE = 0
    SELECTED = auto()
    HOVERED = auto()
    DEPENDENCY_HIGHLIGHT = auto()
    MULTI_SELECTED = auto()
    GLOBAL_SELECTED = auto()

    ACTIVE_SELECTION = SELECTED | MULTI_SELECTED | GLOBAL_SELECTED


class ActionTypes(enum.Enum):
    """操作类型枚举"""
    COPY = "copy"
    LOCATE = "locate"
    FOLDER = "folder"
    STEAM = "steam"


class ModType(enum.Enum):
    """Mod类型枚举"""
    CORE = "core"
    DLC = "dlc"
    LOCAL = "local"
    WORKSHOP = "workshop"


class FrontType(enum.Enum):
    """字体大小枚举"""
    BASE = "base"
    SMALL = "small"
    LARGE = "large"


class Platform(enum.Enum):
    """操作系统平台枚举
    
    value: 配置文件中使用的键名
    system_name: platform.system() 返回的系统名称
    """
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"

    @property
    def system_name(self) -> str:
        """获取 platform.system() 返回的系统名称"""
        return {
            Platform.WINDOWS: "Windows",
            Platform.LINUX: "Linux",
            Platform.MACOS: "Darwin"
        }[self]

    @classmethod
    def current(cls) -> "Platform":
        import platform
        system = platform.system()
        for p in cls:
            if p.system_name == system:
                return p
        raise ValueError(f"Unknown platform: {system}")

    def is_windows(self) -> bool:
        return self == Platform.WINDOWS

    def is_linux(self) -> bool:
        return self == Platform.LINUX

    def is_macos(self) -> bool:
        return self == Platform.MACOS


class ListType(enum.Enum):
    """列表类型枚举"""
    ENABLED = "enabled"
    DISABLED = "disabled"

    def is_enabled(self) -> bool:
        return self == ListType.ENABLED

    def is_disabled(self) -> bool:
        return self == ListType.DISABLED


class SearchField(enum.Enum):
    """搜索过滤字段枚举"""
    TAG = "tag"
    AUTHOR = "author"
    NAME = "name"
    ID = "id"
    ISSUE = "issue"
    WORKSHOPID = "workshopid"
    Description = "desc"
    NOTE = "note"
    COLOR = "color"


class StatusType(enum.Enum):
    """状态类型枚举"""
    NORMAL = "normal"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    DISABLED = "disabled"
