"""
Mod管理器模块
负责Mod的数据管理：状态存储、元数据持久化、配置文件操作
业务逻辑（依赖验证、拓扑排序）委托给ModService处理

设计原则：
- Mod实例统一存储于此，避免双重存储
- 解析器仅负责解析，不负责存储
- 提供快速ID查找能力
"""

import logging
from typing import List, Set, Dict, Optional, Tuple

from yh_mods_manager_sdk import Mod, ModProfile
from yh_mods_manager_sdk.enum_types import ModIssueStatus
from .config_manager import ConfigManager
from .dependency_resolver import DependencyResolver
from .id_comparer import IdComparer
from .mod_types import ModOperationResult

logger = logging.getLogger(__name__)


class ModManager:
    """Mod管理器 - 负责Mod的数据管理
    
    职责：
    1. Mod实例的统一存储（唯一存储点）
    2. Mod状态存储（启用/禁用列表）
    3. 元数据持久化（标签、颜色、备注）
    4. 配置文件操作（导入/导出配置）
    5. 依赖关系映射（数据层面）
    6. ID比较工具管理
    
    不负责：
    - 依赖验证逻辑（由ModService处理）
    - 拓扑排序（由ModService处理）
    - 加载顺序验证（由ModService处理）
    """

    def __init__(self, config_manager: ConfigManager):
        self._config_manager = config_manager
        self._id_comparer: Optional[IdComparer] = None
        self._resolver: Optional[DependencyResolver] = None

        self._all_mods: List[Mod] = []
        self._mod_map: Dict[str, Mod] = {}
        self._enabled_mod_ids: Set[str] = set()
        self._enabled_mod_order: List[str] = []
        self._disabled_mod_order: List[str] = []
        self._dependency_map: Dict[str, List[str]] = {}
        self._game_version: str = ""

        self._metadata: Dict[str, dict] = {}
        self._metadata_dirty: bool = False

    @property
    def all_mods(self) -> List[Mod]:
        return self._all_mods

    @property
    def is_metadata_dirty(self) -> bool:
        return self._metadata_dirty

    @property
    def enabled_mod_ids(self) -> Set[str]:
        return self._enabled_mod_ids

    @property
    def enabled_mod_order(self) -> List[str]:
        return self._enabled_mod_order

    @property
    def disabled_mod_order(self) -> List[str]:
        return self._disabled_mod_order

    @property
    def resolver(self) -> Optional[DependencyResolver]:
        return self._resolver

    @property
    def id_comparer(self) -> Optional[IdComparer]:
        return self._id_comparer

    @property
    def game_version(self) -> str:
        return self._game_version

    def set_game_version(self, version: str):
        self._game_version = version

    def get_mod_by_id(self, mod_id: str) -> Optional[Mod]:
        """根据ID获取Mod实例（统一入口）"""
        return self._mod_map.get(mod_id)

    def set_mods(self, mods: List[Mod], case_sensitive: bool = False):
        """设置Mod列表，构建索引"""
        self._all_mods = mods
        self._mod_map = {mod.id: mod for mod in mods}
        self._id_comparer = IdComparer(case_sensitive=case_sensitive)
        self._id_comparer.build_from_mods(mods)
        self._resolver = DependencyResolver(mods, self._id_comparer)
        self._build_dependency_map()
        self._load_metadata()

    def _build_dependency_map(self):
        self._dependency_map.clear()
        for mod in self._all_mods:
            for dep_original_id in mod.depended_modules:
                dep_mod_ids = self._resolver.id_comparer.get_all_mod_ids_by_original_id(dep_original_id)
                for dep_mod_id in dep_mod_ids:
                    if dep_mod_id not in self._dependency_map:
                        self._dependency_map[dep_mod_id] = []
                    if mod.id not in self._dependency_map[dep_mod_id]:
                        self._dependency_map[dep_mod_id].append(mod.id)

    def get_mods_depending_on(self, mod_id: str) -> List[str]:
        return self._dependency_map.get(mod_id, [])

    def _load_metadata(self):
        self._metadata = self._config_manager.load_mod_metadata()
        for mod in self._all_mods:
            if mod.id in self._metadata:
                mod.custom_meta.update_from_data(self._metadata[mod.id])

    def save_metadata(self):
        if not self._metadata_dirty:
            return
        self._config_manager.save_mod_metadata(self._all_mods)
        self._metadata_dirty = False

    def update_mod_metadata(self, mod: Mod):
        from .serializers import ModCustomMetaSerializer
        serializer = ModCustomMetaSerializer()
        meta_dict = serializer.serialize(mod.custom_meta)
        if any(meta_dict.values()):
            self._metadata[mod.id] = meta_dict
        elif mod.id in self._metadata:
            del self._metadata[mod.id]
        self._metadata_dirty = True

    def enable_mods(self, mod_ids: List[str], insert_pos: int = -1) -> ModOperationResult:
        if not mod_ids:
            return ModOperationResult(True, affected_mods=[])

        affected = []
        for i, mod_id in enumerate(mod_ids):
            mod = self.get_mod_by_id(mod_id)
            if not mod:
                continue

            mod.is_enabled = True
            self._enabled_mod_ids.add(mod_id)

            if mod_id in self._disabled_mod_order:
                self._disabled_mod_order.remove(mod_id)
            if mod_id in self._enabled_mod_order:
                self._enabled_mod_order.remove(mod_id)

            pos = insert_pos + i if insert_pos >= 0 else -1
            if pos < 0 or pos >= len(self._enabled_mod_order):
                self._enabled_mod_order.append(mod_id)
            else:
                self._enabled_mod_order.insert(pos, mod_id)

            affected.append(mod_id)

        return ModOperationResult(True, affected_mods=affected)

    def disable_mods(self, mod_ids: List[str], insert_pos: int = -1) -> ModOperationResult:
        if not mod_ids:
            return ModOperationResult(True, affected_mods=[])

        affected = []

        for i, mod_id in enumerate(mod_ids):
            mod = self.get_mod_by_id(mod_id)
            if mod:
                mod.is_enabled = False
                mod.clear_issues()

            self._enabled_mod_ids.discard(mod_id)

            if mod_id in self._enabled_mod_order:
                self._enabled_mod_order.remove(mod_id)
            if mod_id in self._disabled_mod_order:
                self._disabled_mod_order.remove(mod_id)

            pos = insert_pos + i if insert_pos >= 0 else -1
            if pos < 0 or pos >= len(self._disabled_mod_order):
                self._disabled_mod_order.append(mod_id)
            else:
                self._disabled_mod_order.insert(pos, mod_id)

            affected.append(mod_id)

        return ModOperationResult(True, affected_mods=affected)

    def enable_all_mods(self) -> ModOperationResult:
        disabled_ids = [mod.id for mod in self._all_mods if mod.id not in self._enabled_mod_ids]
        return self.enable_mods(disabled_ids)

    def disable_all_mods(self) -> ModOperationResult:
        for mod in self._all_mods:
            mod.is_enabled = False
            mod.clear_issues()

        affected = list(self._enabled_mod_ids)
        self._enabled_mod_ids.clear()
        self._enabled_mod_order.clear()
        self._disabled_mod_order.clear()

        return ModOperationResult(True, affected_mods=affected)

    def move_mod_up(self, mod_id: str) -> bool:
        if mod_id not in self._enabled_mod_order:
            return False
        idx = self._enabled_mod_order.index(mod_id)
        if idx == 0:
            return False
        self._enabled_mod_order[idx], self._enabled_mod_order[idx - 1] = \
            self._enabled_mod_order[idx - 1], self._enabled_mod_order[idx]
        return True

    def move_mod_down(self, mod_id: str) -> bool:
        if mod_id not in self._enabled_mod_order:
            return False
        idx = self._enabled_mod_order.index(mod_id)
        if idx == len(self._enabled_mod_order) - 1:
            return False
        self._enabled_mod_order[idx], self._enabled_mod_order[idx + 1] = \
            self._enabled_mod_order[idx + 1], self._enabled_mod_order[idx]
        return True

    def reorder_enabled_mods(self, new_order: List[str]):
        self._enabled_mod_order = [mod_id for mod_id in new_order if mod_id in self._enabled_mod_ids]

    def reorder_disabled_mods(self, new_order: List[str]):
        disabled_ids = {mod.id for mod in self._all_mods if mod.id not in self._enabled_mod_ids}
        self._disabled_mod_order = [mod_id for mod_id in new_order if mod_id in disabled_ids]

    def sort_mods_topologically(self) -> Tuple[bool, List[str], Optional[str]]:
        if not self._resolver:
            return False, [], "Resolver not initialized"

        try:
            sorted_ids = self._resolver.topological_sort(list(self._enabled_mod_ids))
            self._enabled_mod_order = sorted_ids.copy()

            for mod_id in sorted_ids:
                mod = self.get_mod_by_id(mod_id)
                if mod:
                    mod.is_enabled = True

            return True, sorted_ids, None
        except ValueError as e:
            logger.error(f"Failed to sort enabled mods: {e}")
            return False, [], str(e)

    def add_tag_to_mod(self, mod_id: str, tag: str) -> bool:
        mod = self.get_mod_by_id(mod_id)
        if not mod:
            return False
        if tag in mod.tags:
            return False
        mod.add_tag(tag)
        self.update_mod_metadata(mod)
        return True

    def remove_tag_from_mod(self, mod_id: str, tag: str) -> bool:
        mod = self.get_mod_by_id(mod_id)
        if not mod:
            return False
        if tag not in mod.tags:
            return False
        mod.tags.discard(tag)
        self.update_mod_metadata(mod)
        return True

    def set_mod_color(self, mod_id: str, color: Optional[str]) -> bool:
        mod = self.get_mod_by_id(mod_id)
        if not mod:
            return False
        mod.custom_color = color
        self.update_mod_metadata(mod)
        return True

    def set_mod_custom_name(self, mod_id: str, name: Optional[str]) -> bool:
        mod = self.get_mod_by_id(mod_id)
        if not mod:
            return False
        mod.custom_name = name.strip() if name and name.strip() else None
        self.update_mod_metadata(mod)
        return True

    def set_mod_note(self, mod_id: str, note: Optional[str]) -> bool:
        mod = self.get_mod_by_id(mod_id)
        if not mod:
            return False
        mod.note = note.strip() if note and note.strip() else None
        self.update_mod_metadata(mod)
        return True

    def set_mod_ignored_issue(self, mod_id: str, issue: "ModIssueStatus", ignored: bool) -> bool:
        mod = self.get_mod_by_id(mod_id)
        if not mod:
            return False
        if ignored:
            mod.custom_meta.ignore_issue(issue)
        else:
            mod.custom_meta.unignore_issue(issue)
        self.update_mod_metadata(mod)
        return True

    def batch_set_ignored_issues(self, operations: List[Tuple[str, "ModIssueStatus", bool]]) -> List[str]:
        affected_mod_ids = []
        for mod_id, issue, ignored in operations:
            mod = self.get_mod_by_id(mod_id)
            if not mod:
                continue
            if ignored:
                mod.custom_meta.ignore_issue(issue)
            else:
                mod.custom_meta.unignore_issue(issue)
            if mod_id not in affected_mod_ids:
                affected_mod_ids.append(mod_id)

        for mod_id in affected_mod_ids:
            mod = self.get_mod_by_id(mod_id)
            if mod:
                self.update_mod_metadata(mod)

        return affected_mod_ids

    def delete_mod(self, mod_id: str) -> ModOperationResult:
        mod = self.get_mod_by_id(mod_id)
        if not mod:
            return ModOperationResult(False, f"Mod not found: {mod_id}")

        if self._config_manager.delete_mod(mod):
            self._all_mods = [m for m in self._all_mods if m.id != mod_id]
            self._mod_map.pop(mod_id, None)
            self._enabled_mod_ids.discard(mod_id)
            self._enabled_mod_order = [id for id in self._enabled_mod_order if id != mod_id]
            self._disabled_mod_order = [id for id in self._disabled_mod_order if id != mod_id]
            return ModOperationResult(True, affected_mods=[mod_id])

        return ModOperationResult(False, "Failed to delete mod")

    def load_profile(self, profile: ModProfile) -> ModOperationResult:
        if not profile:
            return ModOperationResult(False, message="Profile is None")

        valid_ids = {mod.id for mod in self._all_mods}
        profile_mod_ids = [mid for mid in profile.mod_order if mid in valid_ids]

        self.disable_all_mods()

        if profile_mod_ids:
            return self.enable_mods(profile_mod_ids)

        return ModOperationResult(True, affected_mods=[])

    def save_to_profile(self, name: str, profile: ModProfile):
        profile.mod_order = list(self._enabled_mod_order)
        profile.game_version = self._game_version
        self._config_manager.save_profile(name, profile, self.get_mod_by_id)

    def create_profile(self, name: str, description: str = "") -> Optional[ModProfile]:
        profile = self._config_manager.create_profile(name, description)
        if profile:
            profile.mod_order = list(self._enabled_mod_order)
            profile.game_version = self._game_version
            self._config_manager.save_profile(name, profile, self.get_mod_by_id)
        return profile

    def export_current_mods(self, export_path: str) -> bool:
        return self._config_manager.export_current_mods(list(self._enabled_mod_order), export_path, self.get_mod_by_id)

    def export_profile(self, profile_name: str, export_path: str) -> bool:
        return self._config_manager.export_profile(profile_name, export_path, self.get_mod_by_id)

    def import_profile(self, import_path: str):
        return self._config_manager.import_profile(import_path)

    def export_metadata(self, export_path: str) -> bool:
        return self._config_manager.export_mod_metadata(export_path, self._all_mods)

    def import_metadata(self, import_path: str) -> bool:
        metadata = self._config_manager.import_mod_metadata(import_path)
        if metadata:
            for mod_id, data in metadata.items():
                mod = self.get_mod_by_id(mod_id)
                if mod:
                    mod.custom_meta.update_from_data(data)
            return True
        return False

    def get_enabled_mods(self) -> List[Mod]:
        return [self.get_mod_by_id(mod_id) for mod_id in self._enabled_mod_order if self.get_mod_by_id(mod_id)]

    def get_disabled_mods(self) -> List[Mod]:
        disabled_ids = {mod.id for mod in self._all_mods if mod.id not in self._enabled_mod_ids}
        if not self._disabled_mod_order:
            self._disabled_mod_order = list(disabled_ids)

        order_map = {mod_id: idx for idx, mod_id in enumerate(self._disabled_mod_order)}
        disabled_mods = [mod for mod in self._all_mods if mod.id in disabled_ids]
        disabled_mods.sort(key=lambda m: order_map.get(m.id, len(self._disabled_mod_order)))
        return disabled_mods

    def is_mod_enabled(self, mod_id: str) -> bool:
        return mod_id in self._enabled_mod_ids

    def get_mod_dependencies(self, mod_id: str) -> Set[str]:
        mod = self.get_mod_by_id(mod_id)
        if not mod:
            return set()

        result = set()
        for dep_original_id in mod.depended_modules:
            dep_mod_ids = self._resolver.id_comparer.get_all_mod_ids_by_original_id(dep_original_id)
            for dep_mod_id in dep_mod_ids:
                result.add(dep_mod_id)
        return result

    def clear_all(self):
        self._all_mods.clear()
        self._mod_map.clear()
        self._enabled_mod_ids.clear()
        self._enabled_mod_order.clear()
        self._disabled_mod_order.clear()
        self._dependency_map.clear()
        self._metadata.clear()
        self._game_version = ""
        self._id_comparer = None
        self._resolver = None
