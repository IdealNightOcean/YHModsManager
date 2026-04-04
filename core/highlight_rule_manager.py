"""
高亮规则管理器
支持插件注册条件高亮规则，优先级低于选择高亮
"""

import logging
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from yh_mods_manager_sdk import Mod

logger = logging.getLogger(__name__)


@dataclass
class HighlightRule:
    """高亮规则"""
    rule_id: str
    plugin_id: str
    condition: Callable[["Mod"], bool]
    background_color: str
    border_color: Optional[str] = None
    priority: int = 0
    description: str = ""
    enabled: bool = True


@dataclass
class HighlightResult:
    """高亮结果"""
    background_color: str
    border_color: Optional[str] = None
    rule_id: Optional[str] = None
    plugin_id: Optional[str] = None


class HighlightRuleManager:
    """高亮规则管理器
    
    支持插件注册条件高亮规则：
    - 插件通过 register_rule() 注册规则
    - 规则包含条件函数、颜色、优先级
    - 优先级数值越大，优先级越高
    - 选择高亮优先级最高（内部处理）
    """

    def __init__(self):
        self._rules: Dict[str, HighlightRule] = {}
        self._sorted_rules: List[HighlightRule] = []
        self._rules_dirty: bool = True

    def register_rule(
            self,
            rule_id: str,
            plugin_id: str,
            condition: Callable[["Mod"], bool],
            background_color: str,
            border_color: Optional[str] = None,
            priority: int = 0,
            description: str = ""
    ) -> bool:
        """注册高亮规则
        
        Args:
            rule_id: 规则唯一标识（插件内唯一）
            plugin_id: 插件ID
            condition: 条件函数，接收Mod对象，返回bool
            background_color: 背景颜色（十六进制）
            border_color: 边框颜色（可选）
            priority: 优先级，数值越大优先级越高
            description: 规则描述
        
        Returns:
            是否注册成功
        """
        full_id = f"{plugin_id}:{rule_id}"

        if full_id in self._rules:
            return False

        rule = HighlightRule(
            rule_id=rule_id,
            plugin_id=plugin_id,
            condition=condition,
            background_color=background_color,
            border_color=border_color,
            priority=priority,
            description=description
        )

        self._rules[full_id] = rule
        self._rules_dirty = True
        return True

    def unregister_rule(self, rule_id: str, plugin_id: str) -> bool:
        """注销高亮规则
        
        Args:
            rule_id: 规则ID
            plugin_id: 插件ID
        
        Returns:
            是否注销成功
        """
        full_id = f"{plugin_id}:{rule_id}"

        if full_id not in self._rules:
            return False

        del self._rules[full_id]
        self._rules_dirty = True
        return True

    def unregister_plugin_rules(self, plugin_id: str) -> int:
        """注销插件的所有规则
        
        Args:
            plugin_id: 插件ID
        
        Returns:
            注销的规则数量
        """
        to_remove = [
            full_id for full_id, rule in self._rules.items()
            if rule.plugin_id == plugin_id
        ]

        for full_id in to_remove:
            del self._rules[full_id]

        if to_remove:
            self._rules_dirty = True

        return len(to_remove)

    def set_rule_enabled(self, rule_id: str, plugin_id: str, enabled: bool) -> bool:
        """设置规则启用状态
        
        Args:
            rule_id: 规则ID
            plugin_id: 插件ID
            enabled: 是否启用
        
        Returns:
            是否设置成功
        """
        full_id = f"{plugin_id}:{rule_id}"

        if full_id not in self._rules:
            return False

        self._rules[full_id].enabled = enabled
        self._rules_dirty = True
        return True

    def update_rule_color(
            self,
            rule_id: str,
            plugin_id: str,
            background_color: str,
            border_color: Optional[str] = None
    ) -> bool:
        """更新规则颜色
        
        Args:
            rule_id: 规则ID
            plugin_id: 插件ID
            background_color: 新的背景颜色
            border_color: 新的边框颜色
        
        Returns:
            是否更新成功
        """
        full_id = f"{plugin_id}:{rule_id}"

        if full_id not in self._rules:
            return False

        rule = self._rules[full_id]
        rule.background_color = background_color
        rule.border_color = border_color
        return True

    def get_highlight(self, mod: "Mod") -> Optional[HighlightResult]:
        """获取Mod的高亮颜色
        
        按优先级从高到低检查规则，返回第一个匹配的结果。
        
        Args:
            mod: Mod对象
        
        Returns:
            高亮结果，如果没有匹配的规则则返回None
        """
        if self._rules_dirty:
            self._rebuild_sorted_rules()

        for rule in self._sorted_rules:
            if not rule.enabled:
                continue

            try:
                if rule.condition(mod):
                    return HighlightResult(
                        background_color=rule.background_color,
                        border_color=rule.border_color,
                        rule_id=rule.rule_id,
                        plugin_id=rule.plugin_id
                    )
            except Exception as e:
                logger.error(f"Highlight rule '{rule.rule_id}' error: {e}")

        return None

    def get_all_rules(self) -> List[HighlightRule]:
        """获取所有规则"""
        return list(self._rules.values())

    def get_plugin_rules(self, plugin_id: str) -> List[HighlightRule]:
        """获取插件的所有规则"""
        return [
            rule for rule in self._rules.values()
            if rule.plugin_id == plugin_id
        ]

    def get_rule(self, rule_id: str, plugin_id: str) -> Optional[HighlightRule]:
        """获取指定规则"""
        full_id = f"{plugin_id}:{rule_id}"
        return self._rules.get(full_id)

    def clear_all_rules(self) -> None:
        """清除所有规则"""
        self._rules.clear()
        self._sorted_rules.clear()
        self._rules_dirty = False

    def get_matching_rules(self, mod: "Mod") -> List[HighlightRule]:
        """获取Mod匹配的所有规则
        
        Args:
            mod: Mod对象
        
        Returns:
            匹配的规则列表（按优先级排序）
        """
        if self._rules_dirty:
            self._rebuild_sorted_rules()

        matched = []
        for rule in self._sorted_rules:
            if not rule.enabled:
                continue
            try:
                if rule.condition(mod):
                    matched.append(rule)
            except Exception as e:
                logger.warning(f"Highlight rule '{rule.rule_id}' condition error: {e}")

        return matched

    def _rebuild_sorted_rules(self) -> None:
        """重建排序后的规则列表"""
        self._sorted_rules = sorted(
            [rule for rule in self._rules.values() if rule.enabled],
            key=lambda r: r.priority,
            reverse=True
        )
        self._rules_dirty = False


_highlight_rule_manager: Optional[HighlightRuleManager] = None


def get_highlight_rule_manager() -> HighlightRuleManager:
    """获取全局高亮规则管理器实例"""
    global _highlight_rule_manager
    if _highlight_rule_manager is None:
        _highlight_rule_manager = HighlightRuleManager()
    return _highlight_rule_manager


def init_highlight_rule_manager() -> HighlightRuleManager:
    """初始化全局高亮规则管理器"""
    return get_highlight_rule_manager()
