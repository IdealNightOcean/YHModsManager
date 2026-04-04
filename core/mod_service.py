"""
Mod服务层
统一管理Mod相关的业务逻辑，作为UI层和数据层之间的桥梁
遵循单一职责原则，将业务逻辑从UI层和MainWindow中抽离
"""

import re
from typing import List, Optional, Tuple, Dict, Set

from yh_mods_manager_sdk import Mod
from yh_mods_manager_sdk.enum_types import ModIssueStatus
from .dependency_resolver import DependencyResolver
from .mod_manager import ModManager
from .mod_types import ModOperationResult, ValidationResult


class ModService:
    """Mod服务层 - 统一的业务逻辑入口
    
    职责：
    1. Mod启用/禁用操作
    2. 加载顺序管理
    3. 依赖关系验证
    4. 拓扑排序
    
    不负责：
    - UI更新（由调用方处理）
    - 数据持久化（由ModManager处理）
    """

    def __init__(self, mod_manager: ModManager):
        self._manager = mod_manager

    @property
    def manager(self) -> ModManager:
        return self._manager

    @property
    def resolver(self) -> Optional[DependencyResolver]:
        return self._manager.resolver

    def enable_mods(self, mod_ids: List[str], insert_pos: int = -1) -> ModOperationResult:
        if not mod_ids:
            return ModOperationResult(True, affected_mods=[])

        result = self._manager.enable_mods(mod_ids, insert_pos)

        if result.success and result.affected_mods:
            self._update_dependency_status(result.affected_mods)

        return result

    def enable_mod(self, mod_id: str, insert_pos: int = -1) -> ModOperationResult:
        return self.enable_mods([mod_id], insert_pos)

    def disable_mods(self, mod_ids: List[str], insert_pos: int = -1) -> ModOperationResult:
        if not mod_ids:
            return ModOperationResult(True, affected_mods=[])

        result = self._manager.disable_mods(mod_ids, insert_pos)

        if result.success:
            dependent_mods = []
            for mod_id in result.affected_mods:
                dependent_mods.extend(self._manager.get_mods_depending_on(mod_id))

            if dependent_mods:
                self._update_dependency_status(dependent_mods)

        return result

    def move_mod_up(self, mod_id: str) -> bool:
        return self._manager.move_mod_up(mod_id)

    def move_mod_down(self, mod_id: str) -> bool:
        return self._manager.move_mod_down(mod_id)

    def reorder_enabled_mods(self, new_order: List[str]):
        self._manager.reorder_enabled_mods(new_order)

    def reorder_disabled_mods(self, new_order: List[str]):
        self._manager.reorder_disabled_mods(new_order)

    def disable_all_mods(self) -> ModOperationResult:
        return self._manager.disable_all_mods()

    def sort_topologically(self) -> Tuple[bool, List[str], Optional[str]]:
        return self._manager.sort_mods_topologically()

    def validate_all(self) -> Tuple[ValidationResult, Dict[str, List[str]]]:
        """合并验证：一次遍历完成缺失依赖和加载顺序检查
         
        性能优化：
        - 原方案：2+N次遍历（N为错误数量）
        - 优化后：1次遍历 + O(1)字典查找
        
        Returns:
            Tuple[ValidationResult, Dict]: 验证结果和缺失依赖映射
        """
        if not self.resolver:
            return ValidationResult(is_valid=True, errors=[]), {}

        enabled_order = self._manager.enabled_mod_order
        enabled_set = set(enabled_order)
        mod_cache = {mod.id: mod for mod in self._manager.all_mods}
        mod_name_cache = {mod.name: mod for mod in self._manager.all_mods}

        missing_issues: Dict[str, List[str]] = {}

        for mod_id in enabled_order:
            mod = mod_cache.get(mod_id)
            if not mod:
                continue

            mod.clear_issues(clear_static=False)

            missing_dependencies = self.resolver.get_missing_dependencies(mod_id, enabled_order)
            if missing_dependencies:
                mod.add_issue(ModIssueStatus.MISSING_DEPENDENCIES)
                mod.set_issue_details(ModIssueStatus.MISSING_DEPENDENCIES, missing_dependencies)
                missing_issues[mod_id] = missing_dependencies
            else:
                mod.clear_issue_details(ModIssueStatus.MISSING_DEPENDENCIES)

        for mod in self._manager.all_mods:
            if mod.id not in enabled_set:
                mod.clear_issues(clear_static=False)

        is_valid, errors = self.resolver.validate_load_order(enabled_order)

        if not is_valid:
            for error in errors:
                match = re.search(r"'([^']+)'", error)
                if match:
                    mod_name = match.group(1)
                    mod = mod_cache.get(mod_name) or mod_name_cache.get(mod_name)
                    if mod:
                        mod.add_issue(ModIssueStatus.ORDER_ERROR)
                        mod.add_issue_detail(ModIssueStatus.ORDER_ERROR, error)

        return ValidationResult(is_valid=is_valid, errors=errors, warning_count=len(errors)), missing_issues

    def get_missing_dependencies(self, mod_id: str) -> List[str]:
        if not self.resolver:
            return []
        return self.resolver.get_missing_dependencies(mod_id, list(self._manager.enabled_mod_ids))

    def get_mod_dependencies(self, mod_id: str) -> Set[str]:
        return self._manager.get_mod_dependencies(mod_id)

    def get_mods_depending_on(self, mod_id: str) -> List[str]:
        return self._manager.get_mods_depending_on(mod_id)

    def is_mod_enabled(self, mod_id: str) -> bool:
        return self._manager.is_mod_enabled(mod_id)

    def get_mod_by_id(self, mod_id: str) -> Optional[Mod]:
        return self._manager.get_mod_by_id(mod_id)

    def _update_dependency_status(self, mod_ids: List[str]):
        if not self.resolver:
            return

        enabled_list = list(self._manager.enabled_mod_ids)
        for mod_id in mod_ids:
            if mod_id not in enabled_list:
                continue
            mod = self.get_mod_by_id(mod_id)
            if mod:
                missing_dependencies = self.resolver.get_missing_dependencies(mod_id, enabled_list)
                if missing_dependencies:
                    mod.add_issue(ModIssueStatus.MISSING_DEPENDENCIES)
                    mod.set_issue_details(ModIssueStatus.MISSING_DEPENDENCIES, missing_dependencies)
                else:
                    mod.remove_issue(ModIssueStatus.MISSING_DEPENDENCIES)

    def add_tag_to_mod(self, mod_id: str, tag: str) -> bool:
        return self._manager.add_tag_to_mod(mod_id, tag)

    def remove_tag_from_mod(self, mod_id: str, tag: str) -> bool:
        return self._manager.remove_tag_from_mod(mod_id, tag)

    def set_mod_color(self, mod_id: str, color: Optional[str]) -> bool:
        return self._manager.set_mod_color(mod_id, color)

    def set_mod_custom_name(self, mod_id: str, name: Optional[str]) -> bool:
        return self._manager.set_mod_custom_name(mod_id, name)

    def set_mod_note(self, mod_id: str, note: Optional[str]) -> bool:
        return self._manager.set_mod_note(mod_id, note)

    def set_mod_ignored_issue(self, mod_id: str, issue: "ModIssueStatus", ignored: bool) -> bool:
        return self._manager.set_mod_ignored_issue(mod_id, issue, ignored)

    def batch_set_ignored_issues(self, operations: List[Tuple[str, "ModIssueStatus", bool]]) -> List[str]:
        return self._manager.batch_set_ignored_issues(operations)

    def delete_mod(self, mod_id: str) -> ModOperationResult:
        return self._manager.delete_mod(mod_id)

    def load_profile(self, profile) -> ModOperationResult:
        return self._manager.load_profile(profile)

    def save_to_profile(self, name: str, profile):
        self._manager.save_to_profile(name, profile)

    @property
    def all_mods(self) -> List[Mod]:
        return self._manager.all_mods

    @property
    def enabled_mod_ids(self) -> Set[str]:
        return self._manager.enabled_mod_ids

    @property
    def enabled_mod_order(self) -> List[str]:
        return self._manager.enabled_mod_order

    @property
    def disabled_mod_order(self) -> List[str]:
        return self._manager.disabled_mod_order

    def get_enabled_mods(self) -> List[Mod]:
        return self._manager.get_enabled_mods()

    def get_disabled_mods(self) -> List[Mod]:
        return self._manager.get_disabled_mods()
