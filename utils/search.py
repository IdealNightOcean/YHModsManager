import logging
import re
from typing import Callable, Dict, Optional

from yh_mods_manager_sdk import SearchField, Mod, ModIssueStatus
from yh_mods_manager_sdk.enum_extension import get_issue_extension
from utils.debouncer import Debouncer

logger = logging.getLogger(__name__)


class SearchDebouncer(Debouncer):
    def __init__(self, callback: Callable[[str], None], delay_ms: Optional[int] = None):
        super().__init__(callback, delay_ms, config_key="search_delay")

    def update(self, text: str):
        self.trigger(text)


class StructuredSearchParser:
    """结构化搜索解析器，支持 @key=value 语法"""

    SUPPORTED_FIELDS = {field.value for field in SearchField}
    TRUE_VALUES = ('true', '1', 'yes')
    FALSE_VALUES = ('false', '0', 'no')

    def __init__(self, user_config=None):
        self.text_filter = ""
        self.filters: Dict[SearchField, str] = {}
        self.user_config = user_config
        self._tag_map = {}
        self._build_tag_map()

    def _build_tag_map(self):
        from ui.i18n import tr

        self._tag_map = {}
        if self.user_config:
            for tag_config in self.user_config.get_enabled_tags():
                tag_key = tag_config.name
                self._tag_map[tag_key] = tag_key
                self._tag_map[tag_key.lower()] = tag_key

                tr_name = tr(tag_key)
                if tr_name and tr_name != tag_key:
                    self._tag_map[tr_name] = tag_key
                    self._tag_map[tr_name.lower()] = tag_key

    def _normalize_tag(self, tag_value: str) -> str:
        if tag_value in self._tag_map:
            return self._tag_map[tag_value]
        if tag_value.startswith('tag_'):
            return tag_value
        lower_val = tag_value.lower()
        if lower_val in self._tag_map:
            return self._tag_map[lower_val]

        return tag_value

    def parse(self, search_text: str) -> dict:
        self.text_filter = ""
        self.filters = {}

        if not search_text:
            return {'text': '', 'filters': {}}

        pattern = r'@(\w+)=([^\s@]+)'
        matches = re.findall(pattern, search_text)

        remaining = re.sub(pattern, '', search_text).strip()
        enum_extension = get_issue_extension()
        for key, value in matches:
            field = enum_extension.from_string_search_field(key)
            if field is None:
                logger.debug(f"Invalid search field '{key}'")
                continue

            try:
                if field == SearchField.TAG:
                    self.filters[SearchField.TAG] = self._normalize_tag(value)
                else:
                    self.filters[field] = value
            except ValueError as e:
                logger.debug(f"Invalid search field '{key}': {e}")

        self.text_filter = remaining

        return {
            'text': self.text_filter,
            'filters': self.filters
        }

    @staticmethod
    def _parse_bool_value(value: str) -> bool | None:
        value_lower = value.lower()
        if value_lower in StructuredSearchParser.TRUE_VALUES:
            return True
        elif value_lower in StructuredSearchParser.FALSE_VALUES:
            return False
        return None

    @staticmethod
    def matches(mod: 'Mod', parsed: dict) -> bool:
        text = parsed.get('text', '').lower()
        filters: Dict[SearchField, str] = parsed.get('filters', {})

        if text:
            text_match = (
                    text in mod.name.lower() or
                    text in mod.display_name.lower()
            )
            if not text_match:
                return False

        enum_extension = get_issue_extension()

        for field, value in filters.items():
            if not value:
                continue

            value_lower = value.lower()
            match field:
                case SearchField.TAG:
                    if mod.official_tags_lower and any(value_lower in t for t in mod.official_tags_lower):
                        return True
                    if mod.tags_lower and any(value_lower in t for t in mod.tags_lower):
                        return True
                    return False
                case SearchField.AUTHOR:
                    if not mod.authors_lower or not any(value_lower in a for a in mod.authors_lower):
                        return False
                case SearchField.NAME:
                    if value_lower not in mod.name.lower():
                        return False
                case SearchField.ID:
                    if value_lower not in mod.original_id.lower():
                        return False
                case SearchField.ISSUE:
                    if not mod.issue_status or mod.issue_status == ModIssueStatus.NORMAL:
                        return False
                    target_issue = enum_extension.from_string_issue(value_lower)
                    if not target_issue or not mod.has_visible_issue(target_issue):
                        return False
                case SearchField.WORKSHOPID:
                    if not mod.workshop_id or value_lower not in mod.workshop_id:
                        return False
                case SearchField.COLOR:
                    if not mod.custom_color or value_lower not in mod.custom_color.lower():
                        return False
                case SearchField.Description:
                    if not mod.description_lower or value_lower not in mod.description_lower:
                        return False
                case SearchField.NOTE:
                    if not mod.note_lower or value_lower not in mod.note_lower:
                        return False

        return True
