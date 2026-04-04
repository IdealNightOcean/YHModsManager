from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set

from yh_mods_manager_sdk import ModType, ModIssueStatus
from yh_mods_manager_sdk.enum_extension import EnumExtension


@dataclass
class ModCustomMeta:
    """Mod自定义元数据

    集中管理用户自定义的元数据字段，便于统一持久化和访问
    """
    tags: Set[str] = field(default_factory=set)
    custom_color: Optional[str] = None
    custom_name: Optional[str] = None
    note: Optional[str] = None
    ignored_issues: ModIssueStatus = ModIssueStatus.NORMAL
    ignored_issues_set: Set[ModIssueStatus] = field(default_factory=set)

    def update_from_data(self, data: dict):
        if "tags" in data:
            self.tags = set(data["tags"])
        if "custom_color" in data:
            self.custom_color = data["custom_color"]
        if "custom_name" in data:
            self.custom_name = data["custom_name"]
        if "note" in data:
            self.note = data["note"]
        if "ignored_issues" in data:
            value = data["ignored_issues"]
            self.ignored_issues = ModIssueStatus(value) if value else None
            if self.ignored_issues:
                for issue in EnumExtension.PREDEFINE_MOD_ISSUES_STATUS:
                    if self.ignored_issues.has_issue(issue):
                        self.ignored_issues_set.add(issue)

    def is_issue_ignored(self, issue: "ModIssueStatus") -> bool:
        return self.ignored_issues.has_issue(issue)

    def ignore_issue(self, issue: "ModIssueStatus") -> None:
        self.ignored_issues |= issue
        self.ignored_issues_set.add(issue)

    def unignore_issue(self, issue: "ModIssueStatus") -> None:
        self.ignored_issues_set.discard(issue)
        self.ignored_issues = ModIssueStatus.NORMAL
        for status in self.ignored_issues_set:
            self.ignored_issues |= status


@dataclass
class Mod:
    """Mod数据类

    包含Mod的所有元数据信息，是插件与主程序之间传递Mod数据的核心类型。
    """
    id: str
    original_id: str = ""
    name: str = ""
    version: str = "1.0.0"
    supported_versions: List[str] = field(default_factory=list)
    authors: List[str] = field(default_factory=list)
    official_tags: List[str] = field(default_factory=list)
    path: str = ""
    mod_type: ModType = ModType.LOCAL
    workshop_id: Optional[str] = None
    preview_image: Optional[str] = None
    description: Optional[str] = None

    depended_modules: List[str] = field(default_factory=list)
    load_before: List[str] = field(default_factory=list)
    load_after: List[str] = field(default_factory=list)
    incompatible_modules: List[str] = field(default_factory=list)

    is_enabled: bool = False
    order_index: int = 0
    custom_meta: ModCustomMeta = field(default_factory=ModCustomMeta)

    issue_status: ModIssueStatus = ModIssueStatus.NORMAL
    issue_status_set: Set[ModIssueStatus] = field(default_factory=set)
    mod_issues_details: Dict[str, List[str]] = field(default_factory=dict)

    _description_lower: Optional[str] = None
    _official_tags_lower: Optional[List[str]] = field(default=None, repr=False, compare=False)
    _authors_lower: Optional[List[str]] = field(default=None, repr=False, compare=False)

    _tags_lower: Optional[List[str]] = field(default=None, repr=False, compare=False)
    _note_lower: Optional[str] = None

    @property
    def description_lower(self) -> str:
        if self._description_lower is None:
            self._description_lower = (self.description or "").lower()
        return self._description_lower

    @property
    def official_tags_lower(self) -> List[str]:
        if self._official_tags_lower is None:
            self._official_tags_lower = [t.lower() for t in self.official_tags] if self.official_tags else []
        return self._official_tags_lower

    @property
    def authors_lower(self) -> List[str]:
        if self._authors_lower is None:
            self._authors_lower = [a.lower() for a in self.authors] if self.authors else []
        return self._authors_lower

    @property
    def display_name(self) -> str:
        if self.custom_meta.custom_name:
            return self.custom_meta.custom_name
        return self.name if self.name else self.original_id

    @property
    def tags(self) -> Set[str]:
        return self.custom_meta.tags

    @property
    def tags_lower(self) -> List[str]:
        if self._tags_lower is None:
            self._tags_lower = [t.lower() for t in self.tags] if self.tags else []
        return self._tags_lower

    @tags.setter
    def tags(self, value: Set[str]):
        self.custom_meta.tags = value
        self._tags_lower = None

    @property
    def custom_color(self) -> Optional[str]:
        return self.custom_meta.custom_color

    @custom_color.setter
    def custom_color(self, value: Optional[str]):
        self.custom_meta.custom_color = value

    @property
    def custom_name(self) -> Optional[str]:
        return self.custom_meta.custom_name

    @custom_name.setter
    def custom_name(self, value: Optional[str]):
        self.custom_meta.custom_name = value

    @property
    def note(self) -> Optional[str]:
        return self.custom_meta.note

    @property
    def note_lower(self) -> str:
        if self._note_lower is None:
            self._note_lower = (self.note or "").lower()
        return self.note_lower

    @note.setter
    def note(self, value: Optional[str]):
        self.custom_meta.note = value
        self._note_lower = None

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Mod):
            return self.id == other.id
        return False

    def add_tag(self, tag: str):
        self.custom_meta.tags.add(tag)
        self._tags_lower = None

    def remove_tag(self, tag: str):
        self.custom_meta.tags.discard(tag)
        self._tags_lower = None

    def has_tag(self, tag: str) -> bool:
        return tag in self.custom_meta.tags

    def has_issue(self, issue: ModIssueStatus) -> bool:
        return self.issue_status.has_issue(issue)

    def has_visible_issue(self, issue: ModIssueStatus) -> bool:
        return self.has_issue(issue) and not self.custom_meta.is_issue_ignored(issue)

    @staticmethod
    def _get_issue_details_key(issue: ModIssueStatus) -> str:
        return f"{issue.name.lower()}_details"

    def get_issue_details(self, issue: ModIssueStatus) -> List[str]:
        key = Mod._get_issue_details_key(issue)
        return self.mod_issues_details.get(key, [])

    def set_issue_details(self, issue: ModIssueStatus, details: List[str]):
        key = Mod._get_issue_details_key(issue)
        if details:
            self.mod_issues_details[key] = details
        elif key in self.mod_issues_details:
            del self.mod_issues_details[key]

    def add_issue_detail(self, issue: ModIssueStatus, detail: str):
        key = Mod._get_issue_details_key(issue)
        if key not in self.mod_issues_details:
            self.mod_issues_details[key] = []
        if detail not in self.mod_issues_details[key]:
            self.mod_issues_details[key].append(detail)

    def clear_issue_details(self, issue: ModIssueStatus):
        key = Mod._get_issue_details_key(issue)
        if key in self.mod_issues_details:
            del self.mod_issues_details[key]

    def add_issue(self, issue: ModIssueStatus):
        self.issue_status |= issue
        self.issue_status_set.add(issue)

    def remove_issue(self, issue: ModIssueStatus):
        self.issue_status_set.discard(issue)
        self._rebuild_issue_status()

    def clear_issues(self, clear_static: bool = False):
        if clear_static:
            self.issue_status = ModIssueStatus.NORMAL
            self.issue_status_set.clear()
            self.mod_issues_details.clear()
        else:
            for issue in EnumExtension.PREDEFINE_DYNAMIC_ISSUES:
                self.issue_status_set.discard(issue)
                self.clear_issue_details(issue)

            self._rebuild_issue_status()

    def _rebuild_issue_status(self):
        self.issue_status = ModIssueStatus.NORMAL
        for status in self.issue_status_set:
            self.issue_status |= status

    def has_dynamic_issue(self) -> bool:
        return self.issue_status.has_dynamic()

    def has_visible_static_issue(self) -> bool:
        if not self.issue_status.has_static():
            return False
        for issue in self.issue_status_set:
            if issue.has_static() and not self.custom_meta.is_issue_ignored(issue):
                return True
        return False

    def has_visible_error_issue(self) -> bool:
        if not self.issue_status.has_error():
            return False
        for issue in self.issue_status_set:
            if issue.has_error() and not self.custom_meta.is_issue_ignored(issue):
                return True
        return False

    def has_visible_warning_issue(self) -> bool:
        if not self.issue_status.has_warning():
            return False
        for issue in self.issue_status_set:
            if issue.has_warning() and not self.custom_meta.is_issue_ignored(issue):
                return True
        return False

    def has_any_visible_issue(self) -> bool:
        return bool(self.issue_status ^ self.custom_meta.ignored_issues)
