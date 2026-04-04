"""
Mod过滤管理器
支持插件注册条件过滤规则，用于筛选Mod列表
与主程序搜索过滤配合工作
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from yh_mods_manager_sdk import Mod

logger = logging.getLogger(__name__)


class FilterMode(Enum):
    """过滤模式"""
    OR = "or"
    AND = "and"


@dataclass
class FilterRule:
    """过滤规则"""
    rule_id: str
    plugin_id: str
    condition: Callable[["Mod"], bool]
    description: str = ""
    enabled: bool = True


@dataclass
class ActiveFilterState:
    """当前激活的过滤状态"""
    plugin_filter_enabled: bool = True
    active_rule_ids: List[str] = field(default_factory=list)
    filter_mode: FilterMode = FilterMode.OR


class ModFilterManager:
    """Mod过滤管理器
    
    支持插件注册条件过滤规则：
    - 插件通过 register_filter() 注册过滤条件
    - 可用于筛选、搜索、分类Mod
    - 与主程序搜索过滤配合工作
    - 支持状态清除，恢复无过滤状态
    
    过滤流程：
    1. 主程序搜索过滤（文本搜索、类型过滤）
    2. 插件过滤规则（可选启用/禁用）
    3. 最终显示结果
    """

    def __init__(self):
        self._filters: Dict[str, FilterRule] = {}
        self._state = ActiveFilterState()

    def register_filter(
            self,
            rule_id: str,
            plugin_id: str,
            condition: Callable[["Mod"], bool],
            description: str = ""
    ) -> bool:
        """注册过滤规则
        
        Args:
            rule_id: 规则唯一标识（插件内唯一）
            plugin_id: 插件ID
            condition: 条件函数，接收Mod对象，返回bool
            description: 规则描述
        
        Returns:
            是否注册成功
        """
        full_id = f"{plugin_id}:{rule_id}"

        if full_id in self._filters:
            return False

        rule = FilterRule(
            rule_id=rule_id,
            plugin_id=plugin_id,
            condition=condition,
            description=description
        )

        self._filters[full_id] = rule
        return True

    def unregister_filter(self, rule_id: str, plugin_id: str) -> bool:
        """注销过滤规则
        
        Args:
            rule_id: 规则ID
            plugin_id: 插件ID
        
        Returns:
            是否注销成功
        """
        full_id = f"{plugin_id}:{rule_id}"

        if full_id not in self._filters:
            return False

        del self._filters[full_id]

        if full_id in self._state.active_rule_ids:
            self._state.active_rule_ids.remove(full_id)

        return True

    def unregister_plugin_filters(self, plugin_id: str) -> int:
        """注销插件的所有过滤规则
        
        Args:
            plugin_id: 插件ID
        
        Returns:
            注销的规则数量
        """
        to_remove = [
            full_id for full_id, rule in self._filters.items()
            if rule.plugin_id == plugin_id
        ]

        for full_id in to_remove:
            del self._filters[full_id]
            if full_id in self._state.active_rule_ids:
                self._state.active_rule_ids.remove(full_id)

        return len(to_remove)

    def set_filter_enabled(self, rule_id: str, plugin_id: str, enabled: bool) -> bool:
        """设置过滤规则启用状态
        
        Args:
            rule_id: 规则ID
            plugin_id: 插件ID
            enabled: 是否启用
        
        Returns:
            是否设置成功
        """
        full_id = f"{plugin_id}:{rule_id}"

        if full_id not in self._filters:
            return False

        self._filters[full_id].enabled = enabled
        return True

    def activate_rule(self, rule_id: str, plugin_id: str) -> bool:
        """激活过滤规则（添加到激活列表）
        
        Args:
            rule_id: 规则ID
            plugin_id: 插件ID
        
        Returns:
            是否激活成功
        """
        full_id = f"{plugin_id}:{rule_id}"

        if full_id not in self._filters:
            return False

        if full_id not in self._state.active_rule_ids:
            self._state.active_rule_ids.append(full_id)

        return True

    def deactivate_rule(self, rule_id: str, plugin_id: str) -> bool:
        """停用过滤规则（从激活列表移除）
        
        Args:
            rule_id: 规则ID
            plugin_id: 插件ID
        
        Returns:
            是否停用成功
        """
        full_id = f"{plugin_id}:{rule_id}"

        if full_id in self._state.active_rule_ids:
            self._state.active_rule_ids.remove(full_id)
            return True

        return False

    def clear_active_rules(self) -> None:
        """清除所有激活的过滤规则（恢复无过滤状态）"""
        self._state.active_rule_ids.clear()

    def set_plugin_filter_enabled(self, enabled: bool) -> None:
        """设置插件过滤功能是否启用
        
        Args:
            enabled: 是否启用插件过滤
        """
        self._state.plugin_filter_enabled = enabled

    def is_plugin_filter_enabled(self) -> bool:
        """检查插件过滤功能是否启用"""
        return self._state.plugin_filter_enabled

    def set_filter_mode(self, mode: FilterMode) -> None:
        """设置过滤模式
        
        Args:
            mode: OR模式（任一规则匹配）或AND模式（所有规则匹配）
        """
        self._state.filter_mode = mode

    def get_filter_mode(self) -> FilterMode:
        """获取当前过滤模式"""
        return self._state.filter_mode

    def get_active_rule_ids(self) -> List[str]:
        """获取当前激活的规则ID列表"""
        return self._state.active_rule_ids.copy()

    def apply_plugin_filters(self, mods: List["Mod"]) -> List["Mod"]:
        """应用插件过滤规则到Mod列表
        
        仅应用插件注册的过滤规则，不包含主程序搜索过滤。
        
        Args:
            mods: Mod列表
        
        Returns:
            过滤后的Mod列表
        """
        if not self._state.plugin_filter_enabled:
            return mods

        active_rules = [
            self._filters[full_id]
            for full_id in self._state.active_rule_ids
            if full_id in self._filters and self._filters[full_id].enabled
        ]

        if not active_rules:
            return mods

        if self._state.filter_mode == FilterMode.OR:
            return self._apply_or_filter(mods, active_rules)
        else:
            return self._apply_and_filter(mods, active_rules)

    def apply_combined_filter(
            self,
            mods: List["Mod"],
            main_search_result: List["Mod"] = None
    ) -> List["Mod"]:
        """应用组合过滤（主程序搜索 + 插件过滤）
        
        过滤顺序：
        1. 如果提供了主程序搜索结果，先取交集
        2. 再应用插件过滤规则
        
        Args:
            mods: 原始Mod列表
            main_search_result: 主程序搜索过滤后的结果（可选）
        
        Returns:
            最终过滤后的Mod列表
        """
        if main_search_result is not None:
            mod_set = {mod.id for mod in main_search_result}
            mods = [mod for mod in mods if mod.id in mod_set]

        return self.apply_plugin_filters(mods)

    @staticmethod
    def _apply_or_filter(mods: List["Mod"], rules: List[FilterRule]) -> List["Mod"]:
        """OR模式过滤：任一规则匹配即保留"""
        result = []
        matched_ids = set()

        for rule in rules:
            for mod in mods:
                if mod.id in matched_ids:
                    continue
                try:
                    if rule.condition(mod):
                        result.append(mod)
                        matched_ids.add(mod.id)
                except Exception as e:
                    logger.warning(f"Filter rule '{rule.rule_id}' condition error: {e}")

        return result

    def _apply_and_filter(self, mods: List["Mod"], rules: List[FilterRule]) -> List["Mod"]:
        """AND模式过滤：所有规则都匹配才保留"""
        result = mods

        for rule in rules:
            result = self._apply_single_filter(result, rule.condition)
            if not result:
                break

        return result

    @staticmethod
    def _apply_single_filter(mods: List["Mod"], condition: Callable[["Mod"], bool]) -> List["Mod"]:
        """应用单个过滤条件"""
        result = []
        for mod in mods:
            try:
                if condition(mod):
                    result.append(mod)
            except Exception as e:
                logger.warning(f"Filter condition error for mod '{mod.id}': {e}")
        return result

    def filter_mods(self, mods: List["Mod"], rule_id: str = None, plugin_id: str = None) -> List["Mod"]:
        """根据规则过滤Mod列表（直接使用指定规则，不受激活状态影响）
        
        Args:
            mods: Mod列表
            rule_id: 规则ID（可选，不指定则使用所有启用的规则进行OR匹配）
            plugin_id: 插件ID（与rule_id配合使用）
        
        Returns:
            过滤后的Mod列表
        """
        if rule_id and plugin_id:
            full_id = f"{plugin_id}:{rule_id}"
            rule = self._filters.get(full_id)
            if rule and rule.enabled:
                return self._apply_single_filter(mods, rule.condition)
            return []

        enabled_filters = [f for f in self._filters.values() if f.enabled]
        if not enabled_filters:
            return mods

        return self._apply_or_filter(mods, enabled_filters)

    def filter_mods_by_condition(self, mods: List["Mod"], condition: Callable[["Mod"], bool]) -> List["Mod"]:
        """根据自定义条件过滤Mod
        
        Args:
            mods: Mod列表
            condition: 条件函数
        
        Returns:
            过滤后的Mod列表
        """
        return self._apply_single_filter(mods, condition)

    def get_all_filters(self) -> List[FilterRule]:
        """获取所有过滤规则"""
        return list(self._filters.values())

    def get_plugin_filters(self, plugin_id: str) -> List[FilterRule]:
        """获取插件的所有过滤规则"""
        return [
            rule for rule in self._filters.values()
            if rule.plugin_id == plugin_id
        ]

    def get_filter(self, rule_id: str, plugin_id: str) -> Optional[FilterRule]:
        """获取指定过滤规则"""
        full_id = f"{plugin_id}:{rule_id}"
        return self._filters.get(full_id)

    def clear_all_filters(self) -> None:
        """清除所有过滤规则和状态"""
        self._filters.clear()
        self._state = ActiveFilterState()

    def reset_state(self) -> None:
        """重置过滤状态（保留规则，清除激活状态）"""
        self._state = ActiveFilterState()


_mod_filter_manager: Optional[ModFilterManager] = None


def get_mod_filter_manager() -> ModFilterManager:
    """获取全局Mod过滤管理器实例"""
    global _mod_filter_manager
    if _mod_filter_manager is None:
        _mod_filter_manager = ModFilterManager()
    return _mod_filter_manager


def init_mod_filter_manager() -> ModFilterManager:
    """初始化全局Mod过滤管理器"""
    return get_mod_filter_manager()
