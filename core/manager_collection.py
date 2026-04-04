"""
管理者集合模块
遵循插件系统需求文档规范：
- 插件向主程序请求时，禁止传递离散数据
- 仅传递对应功能的管理者实例/引用
- 主程序统一维护插件通用管理者集合
- 插件通过管理者集合获取所需能力
"""

from typing import Optional, Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from core.config_manager import ConfigManager
    from core.mod_manager import ModManager
    from core.metadata_manager import GameMetadataManager, ModMetadataManager
    from core.highlight_rule_manager import HighlightRuleManager
    from core.mod_filter_manager import ModFilterManager
    from core.id_comparer import IdComparer
    from ui.i18n import I18nManager
    from ui.theme_manager import ThemeManager


class ManagerCollection:
    """管理者集合 
    
    统一维护插件全量依赖管理器，插件通过管理者集合获取所需能力。
    
    核心原则：
    1. 所有交互面向管理者/服务，不面向零散数据
    2. 统一入口、统一上下文
    3. 无零散调用、无硬编码依赖
    4. 禁止零散配置调用、禁止跨插件依赖、禁止反向调用
    """

    def __init__(self):
        self._config_manager: Optional["ConfigManager"] = None
        self._mod_manager: Optional["ModManager"] = None
        self._game_metadata_manager: Optional["GameMetadataManager"] = None
        self._mod_metadata_manager: Optional["ModMetadataManager"] = None
        self._highlight_rule_manager: Optional["HighlightRuleManager"] = None
        self._mod_filter_manager: Optional["ModFilterManager"] = None
        self._i18n: Optional["I18nManager"] = None
        self._theme_manager: Optional["ThemeManager"] = None
        self._custom_managers: Dict[str, Any] = {}

    @property
    def id_comparer(self) -> Optional["IdComparer"]:
        """获取ID比较工具（便捷访问）"""
        if self._mod_manager:
            return self._mod_manager.id_comparer
        return None

    def set_config_manager(self, manager: "ConfigManager") -> None:
        """设置配置管理器"""
        self._config_manager = manager

    def get_config_manager(self) -> Optional["ConfigManager"]:
        """获取配置管理器"""
        return self._config_manager

    def set_mod_manager(self, manager: "ModManager") -> None:
        """设置Mod管理器"""
        self._mod_manager = manager

    def get_mod_manager(self) -> Optional["ModManager"]:
        """获取Mod管理器"""
        return self._mod_manager

    def set_game_metadata_manager(self, manager: "GameMetadataManager") -> None:
        """设置游戏元数据管理器"""
        self._game_metadata_manager = manager

    def get_game_metadata_manager(self) -> Optional["GameMetadataManager"]:
        """获取游戏元数据管理器"""
        return self._game_metadata_manager

    def set_mod_metadata_manager(self, manager: "ModMetadataManager") -> None:
        """设置Mod元数据管理器"""
        self._mod_metadata_manager = manager

    def get_mod_metadata_manager(self) -> Optional["ModMetadataManager"]:
        """获取Mod元数据管理器"""
        return self._mod_metadata_manager

    def set_highlight_rule_manager(self, manager: "HighlightRuleManager") -> None:
        """设置高亮规则管理器"""
        self._highlight_rule_manager = manager

    def get_highlight_rule_manager(self) -> Optional["HighlightRuleManager"]:
        """获取高亮规则管理器"""
        return self._highlight_rule_manager

    def set_mod_filter_manager(self, manager: "ModFilterManager") -> None:
        """设置Mod过滤管理器"""
        self._mod_filter_manager = manager

    def get_mod_filter_manager(self) -> Optional["ModFilterManager"]:
        """获取Mod过滤管理器"""
        return self._mod_filter_manager

    def set_i18n(self, i18n: "I18nManager") -> None:
        """设置国际化管理器"""
        self._i18n = i18n

    def get_i18n(self) -> Optional["I18nManager"]:
        """获取国际化管理器"""
        return self._i18n

    def set_theme_manager(self, manager: "ThemeManager") -> None:
        """设置主题管理器"""
        self._theme_manager = manager

    def get_theme_manager(self) -> Optional["ThemeManager"]:
        """获取主题管理器"""
        return self._theme_manager

    def register_manager(self, name: str, manager: Any) -> None:
        """注册自定义管理器"""
        self._custom_managers[name] = manager

    def get_manager(self, name: str) -> Optional[Any]:
        """获取自定义管理器"""
        return self._custom_managers.get(name)

    def unregister_manager(self, name: str) -> None:
        """注销自定义管理器"""
        self._custom_managers.pop(name, None)

    def get_all_managers(self) -> Dict[str, Any]:
        """获取所有管理器（用于调试）"""
        managers = {
            "config_manager": self._config_manager,
            "mod_manager": self._mod_manager,
            "game_metadata_manager": self._game_metadata_manager,
            "mod_metadata_manager": self._mod_metadata_manager,
            "highlight_rule_manager": self._highlight_rule_manager,
        }
        managers.update(self._custom_managers)
        return managers

    def is_ready(self) -> bool:
        """检查核心管理器是否就绪"""
        return all([
            self._config_manager is not None,
            self._mod_manager is not None,
            self._game_metadata_manager is not None,
            self._mod_metadata_manager is not None,
        ])

    def clear_managers(self) -> None:
        """清除所有管理器引用
        
        用于切换游戏或重置状态时清理
        """
        self._config_manager = None
        self._mod_manager = None
        self._game_metadata_manager = None
        self._mod_metadata_manager = None
        self._highlight_rule_manager = None
        self._mod_filter_manager = None
        self._i18n = None
        self._theme_manager = None
        self._custom_managers.clear()

    def clear_game_data(self, game_id: str = None) -> None:
        """清理指定游戏相关的数据
        
        Args:
            game_id: 游戏ID，为None时清理当前游戏数据
        """
        if self._game_metadata_manager:
            self._game_metadata_manager.clear_metadata(game_id)
        if self._mod_metadata_manager:
            self._mod_metadata_manager.clear_game_mods(game_id)


def reset_manager_collection() -> None:
    """重置全局管理者集合实例
    
    用于单元测试或需要完全重置的场景
    """
    global _manager_collection
    if _manager_collection is not None:
        _manager_collection.clear_managers()
        _manager_collection = None


_manager_collection: Optional[ManagerCollection] = None


def get_manager_collection() -> ManagerCollection:
    """获取全局管理者集合实例"""
    global _manager_collection
    if _manager_collection is None:
        _manager_collection = ManagerCollection()
    return _manager_collection


def init_manager_collection(
        config_manager: "ConfigManager" = None,
        mod_manager: "ModManager" = None,
        game_metadata_manager: "GameMetadataManager" = None,
        mod_metadata_manager: "ModMetadataManager" = None,
        highlight_rule_manager: "HighlightRuleManager" = None,
        mod_filter_manager: "ModFilterManager" = None,
        i18n: "I18nManager" = None,
        theme_manager: "ThemeManager" = None,
) -> ManagerCollection:
    """初始化全局管理者集合"""
    collection = get_manager_collection()
    if config_manager:
        collection.set_config_manager(config_manager)
    if mod_manager:
        collection.set_mod_manager(mod_manager)
    if game_metadata_manager:
        collection.set_game_metadata_manager(game_metadata_manager)
    if mod_metadata_manager:
        collection.set_mod_metadata_manager(mod_metadata_manager)
    if highlight_rule_manager:
        collection.set_highlight_rule_manager(highlight_rule_manager)
    if mod_filter_manager:
        collection.set_mod_filter_manager(mod_filter_manager)
    if i18n:
        collection.set_i18n(i18n)
    if theme_manager:
        collection.set_theme_manager(theme_manager)
    return collection
