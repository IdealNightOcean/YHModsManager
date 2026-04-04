"""
管理器协议定义模块

使用 Python Protocol 定义管理器接口，插件开发时只需要这些协议定义，
运行时由主程序提供具体实现。这实现了插件与主程序的完全解耦。
"""

from typing import Any, Callable, Dict, List, Optional, Protocol, TYPE_CHECKING

from yh_mods_manager_sdk.config import GamePaths

if TYPE_CHECKING:
    from . import Mod
    from .config import ModMetadata, GameMetadata


class IdComparerProtocol(Protocol):
    """ID比较器协议"""

    def normalize_id(self, mod_id: str) -> str:
        """标准化Mod ID"""
        ...

    def ids_equal(self, id1: str, id2: str) -> bool:
        """比较两个ID是否相等"""
        ...

    def find_matching_id(self, target_id: str, id_list: List[str]) -> Optional[str]:
        """在ID列表中查找匹配的ID"""
        ...


class ConfigManagerProtocol(Protocol):
    """配置管理器协议"""

    def get_game_dir_path(self) -> str:
        """获取游戏目录路径"""
        ...

    def get_workshop_dir_path(self) -> str:
        """获取创意工坊目录路径"""
        ...

    def get_local_mod_dir_path(self) -> str:
        """获取本地Mod目录路径"""
        ...

    def get_language(self) -> str:
        """获取当前语言设置"""
        ...

    def get_theme(self) -> str:
        """获取当前主题"""
        ...

    def get_font_size(self) -> int:
        """获取字体大小"""
        ...

    def get_last_game(self) -> str:
        """获取上次选择的游戏ID"""
        ...

    def get_game_paths(self) -> "GamePaths":
        """获取游戏路径配置"""
        ...


class ModManagerProtocol(Protocol):
    """Mod管理器协议"""

    id_comparer: IdComparerProtocol

    def get_all_mods(self) -> List["Mod"]:
        """获取所有Mod"""
        ...

    def get_enabled_mods(self) -> List["Mod"]:
        """获取已启用的Mod"""
        ...

    def get_disabled_mods(self) -> List["Mod"]:
        """获取已禁用的Mod"""
        ...

    def get_mod_by_id(self, mod_id: str) -> Optional["Mod"]:
        """根据ID获取Mod"""
        ...

    def enable_mod(self, mod_id: str) -> bool:
        """启用Mod"""
        ...

    def disable_mod(self, mod_id: str) -> bool:
        """禁用Mod"""
        ...

    def move_mod(self, mod_id: str, new_index: int) -> bool:
        """移动Mod到新位置"""
        ...

    def get_mod_count(self) -> int:
        """获取Mod总数"""
        ...

    def get_enabled_count(self) -> int:
        """获取已启用Mod数量"""
        ...


class GameMetadataManagerProtocol(Protocol):
    """游戏元数据管理器协议"""

    def get_metadata(self, game_id: str = None) -> Optional["GameMetadata"]:
        """获取游戏元数据"""
        ...

    def get_game_version(self, game_id: str = None) -> str:
        """获取游戏版本"""
        ...

    def get_game_name(self, game_id: str = None) -> str:
        """获取游戏名称"""
        ...


class ModMetadataManagerProtocol(Protocol):
    """Mod元数据管理器协议"""

    def get_mod_metadata(self, mod_id: str) -> Optional["ModMetadata"]:
        """获取Mod元数据"""
        ...

    def get_all_metadata(self) -> Dict[str, "ModMetadata"]:
        """获取所有Mod元数据"""
        ...


class HighlightRuleManagerProtocol(Protocol):
    """高亮规则管理器协议"""

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
        """注册高亮规则"""
        ...

    def unregister_rule(self, rule_id: str, plugin_id: str) -> bool:
        """注销高亮规则"""
        ...

    def set_rule_enabled(self, rule_id: str, plugin_id: str, enabled: bool) -> bool:
        """设置规则启用状态"""
        ...

    def unregister_plugin_rules(self, plugin_id: str) -> int:
        """注销插件的所有规则"""
        ...

    def get_highlight_for_mod(self, mod: "Mod") -> Optional[Dict[str, Any]]:
        """获取Mod的高亮样式"""
        ...


class ModFilterManagerProtocol(Protocol):
    """Mod过滤管理器协议"""

    def register_filter(
            self,
            rule_id: str,
            plugin_id: str,
            condition: Callable[["Mod"], bool],
            description: str = ""
    ) -> bool:
        """注册过滤规则"""
        ...

    def unregister_filter(self, rule_id: str, plugin_id: str) -> bool:
        """注销过滤规则"""
        ...

    def unregister_plugin_filters(self, plugin_id: str) -> int:
        """注销插件的所有过滤规则"""
        ...

    def filter_mods(self, mods: List["Mod"]) -> List["Mod"]:
        """过滤Mod列表"""
        ...


class I18nProtocol(Protocol):
    """国际化管理器协议"""

    def tr(self, key: str, *args) -> str:
        """翻译文本
        
        Args:
            key: 翻译键，支持格式：
                - 普通键: "common.save"
                - 插件键: "plugin.plugin_id.key_name"
            *args: 格式化参数
        
        Returns:
            翻译后的文本，未找到则返回原键
        """
        ...

    def get_language(self) -> str:
        """获取当前语言代码
        
        Returns:
            语言代码，如 "zh_CN", "en_US"
        """
        ...

    def set_language(self, lang_code: str) -> bool:
        """设置当前语言
        
        Args:
            lang_code: 语言代码
        
        Returns:
            是否设置成功
        """
        ...

    def get_available_languages(self) -> Dict[str, str]:
        """获取可用语言列表
        
        Returns:
            语言代码到语言名称的映射，如 {"zh_CN": "简体中文", "en_US": "English"}
        """
        ...

    def load_plugin_translations(self, plugin_id: str, i18n_dir: str) -> bool:
        """加载插件翻译文件
        
        Args:
            plugin_id: 插件ID
            i18n_dir: 插件i18n目录路径
        
        Returns:
            是否加载成功
        """
        ...

    def unload_plugin_translations(self, plugin_id: str) -> None:
        """卸载插件翻译
        
        Args:
            plugin_id: 插件ID
        """
        ...


class ThemeManagerProtocol(Protocol):
    """主题管理器协议"""

    @property
    def current_theme_id(self) -> str:
        """当前主题ID"""
        ...

    @property
    def current_theme_name(self) -> str:
        """当前主题名称"""
        ...

    def get_theme_list(self) -> List[str]:
        """获取可用主题列表
        
        Returns:
            主题ID列表，如 ["light", "dark"]
        """
        ...

    def get_theme_name(self, theme_id: str) -> str:
        """获取主题显示名称
        
        Args:
            theme_id: 主题ID
        
        Returns:
            主题显示名称
        """
        ...

    def load_theme(self, theme_id: str) -> bool:
        """加载指定主题
        
        Args:
            theme_id: 主题ID
        
        Returns:
            是否加载成功
        """
        ...

    def get_color(self, key: str) -> str:
        """获取颜色值
        
        Args:
            key: 颜色键名，如 "primary", "error", "surface"
        
        Returns:
            颜色值，如 "#FF6B6B"
        """
        ...

    def get_all_colors(self) -> Dict[str, str]:
        """获取所有颜色配置
        
        Returns:
            颜色键名到颜色值的映射
        """
        ...

    def get_border_radius(self, key: str) -> int:
        """获取圆角大小
        
        Args:
            key: 圆角键名
        
        Returns:
            圆角像素值
        """
        ...

    def apply_theme_to_app(self) -> bool:
        """将当前主题应用到应用程序
        
        Returns:
            是否应用成功
        """
        ...


class ManagerCollectionProtocol(Protocol):
    """管理者集合协议
    
    统一维护插件全量依赖管理器，插件通过管理者集合获取所需能力。
    
    核心原则：
    1. 所有交互面向管理者/服务，不面向零散数据
    2. 统一入口、统一上下文
    3. 无零散调用、无硬编码依赖
    """

    @property
    def id_comparer(self) -> Optional[IdComparerProtocol]:
        """获取ID比较工具"""
        ...

    def get_config_manager(self) -> Optional[ConfigManagerProtocol]:
        """获取配置管理器"""
        ...

    def get_mod_manager(self) -> Optional[ModManagerProtocol]:
        """获取Mod管理器"""
        ...

    def get_game_metadata_manager(self) -> Optional[GameMetadataManagerProtocol]:
        """获取游戏元数据管理器"""
        ...

    def get_mod_metadata_manager(self) -> Optional[ModMetadataManagerProtocol]:
        """获取Mod元数据管理器"""
        ...

    def get_highlight_rule_manager(self) -> Optional[HighlightRuleManagerProtocol]:
        """获取高亮规则管理器"""
        ...

    def get_mod_filter_manager(self) -> Optional[ModFilterManagerProtocol]:
        """获取Mod过滤管理器"""
        ...

    def get_i18n(self) -> Optional[I18nProtocol]:
        """获取国际化管理器"""
        ...

    def get_theme_manager(self) -> Optional[ThemeManagerProtocol]:
        """获取主题管理器"""
        ...

    def get_manager(self, name: str) -> Optional[Any]:
        """获取自定义管理器"""
        ...

    def is_ready(self) -> bool:
        """检查核心管理器是否就绪"""
        ...

    def clear_game_data(self, game_id: str = None) -> None:
        """清理指定游戏相关的数据"""
        ...
