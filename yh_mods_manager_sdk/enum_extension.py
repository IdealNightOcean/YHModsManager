from typing import Optional, List, Dict

from yh_mods_manager_sdk import ModIssueStatus, StatusType, SearchField


class EnumExtension:
    """Mod问题状态扩展 - 提供更多问题状态的扩展功能（单例模式）"""

    _instance: Optional["EnumExtension"] = None

    PREDEFINE_MOD_ISSUES_STATUS: List[ModIssueStatus] = [
        ModIssueStatus.INCOMPLETE,
        ModIssueStatus.MISSING_DEPENDENCIES,
        ModIssueStatus.CONFLICT,
        ModIssueStatus.CUSTOM_STATIC_ERROR,
        ModIssueStatus.CUSTOM_DYNAMIC_ERROR,
        ModIssueStatus.VERSION_MISMATCH,
        ModIssueStatus.DUPLICATE,
        ModIssueStatus.ORDER_ERROR,
        ModIssueStatus.CUSTOM_STATIC_WARNING,
        ModIssueStatus.CUSTOM_DYNAMIC_WARNING
    ]

    PREDEFINE_DYNAMIC_ISSUES: List[ModIssueStatus] = [
        ModIssueStatus.ORDER_ERROR,
        ModIssueStatus.MISSING_DEPENDENCIES,
        ModIssueStatus.CONFLICT,
        ModIssueStatus.CUSTOM_DYNAMIC_ERROR,
        ModIssueStatus.CUSTOM_DYNAMIC_WARNING
    ]

    PREDEFINE_STATIC_ISSUES: List[ModIssueStatus] = [
        ModIssueStatus.INCOMPLETE,
        ModIssueStatus.VERSION_MISMATCH,
        ModIssueStatus.DUPLICATE,
        ModIssueStatus.CUSTOM_STATIC_ERROR,
        ModIssueStatus.CUSTOM_STATIC_WARNING
    ]

    _status_str_map: Dict[str, ModIssueStatus] = {}
    _search_field_map: Dict[str, SearchField] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._status_str_map: Dict[str, ModIssueStatus] = {}
        for status in EnumExtension.PREDEFINE_MOD_ISSUES_STATUS:
            self._status_str_map[status.name.lower()] = status

        for item in SearchField.__members__.values():
            self._search_field_map[item.name.lower()] = item

    @staticmethod
    def get_issue_label_key(issue: ModIssueStatus) -> str:
        return f"status_{issue.name.lower()}"

    @staticmethod
    def get_issue_category(issue: ModIssueStatus) -> "StatusType":
        if issue.has_error():
            return StatusType.ERROR
        return StatusType.WARNING

    def from_string_issue(self, value: str) -> Optional[ModIssueStatus]:
        normalized = EnumExtension.normalized_string(value)
        return self._status_str_map.get(normalized, None)

    def from_string_search_field(self, value: str) -> Optional[SearchField]:
        normalized = EnumExtension.normalized_string(value)
        return self._search_field_map.get(normalized, None)

    @staticmethod
    def normalized_string(value: str) -> str:
        return value.lower().replace('-', '_').replace(' ', '_')

    @classmethod
    def get_instance(cls) -> "EnumExtension":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def get_issue_extension() -> EnumExtension:
    return EnumExtension.get_instance()
