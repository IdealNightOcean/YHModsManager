"""
插件基类模块
支持双插件体系：游戏插件 + 功能插件

遵循插件系统需求文档规范：
- 游戏元数据 ≠ Mod元数据，完全独立
- 插件负责读取输出，主程序负责管理分发
- 通信仅传递管理者，不传递离散数据

双插件体系规则：
- 游戏插件(GameAdapter)：互斥，同一时间仅能启用一个
- 功能插件(FeaturePlugin)：不互斥，可同时启用多个
- 功能插件与游戏插件不互斥，可混合启用

架构设计：
- PluginBase: 通用插件基类，提供菜单、事件、高亮、过滤、配置等通用功能
- GameAdapter: 继承PluginBase，添加游戏特定的强制要求
- FeaturePlugin: 继承PluginBase，无额外强制要求
"""

import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple, TYPE_CHECKING

from . import Mod
from .config import GamePaths, GameInfo, PluginConfig, SaveParseResult, SaveParserCapability, GameMetadata, ModMetadata
from .enum_types import ModType, ModIssueStatus
from .events import PluginEventType, PluginEvent
from .menu import PluginMenuItem, PluginType
from .utils import PluginResult

if TYPE_CHECKING:
    from .protocols import (
        ManagerCollectionProtocol,
        I18nProtocol,
    )

logger = logging.getLogger(__name__)


class GameDetectorBase(ABC):
    """游戏检测器基类
    
    支持两种使用方式：
    
    1. 类属性方式（简单场景）：
       子类直接定义类属性，适用于所有平台相同的情况
       
    2. 配置驱动方式（推荐）：
       子类通过 PluginConfig 初始化，自动支持平台差异化配置
       
    类属性：
    - STEAM_APP_ID: Steam应用ID
    - GAME_FOLDER_NAMES: 游戏可能的文件夹名称列表（所有平台）
    - EXECUTABLE_PATHS: 可执行文件相对路径列表（所有平台）
    - LOCAL_MODS_FOLDER: 游戏路径下的本地Mod文件夹名
    - CONFIG_DIR_PATHS: 配置目录路径（按平台区分）
    
    Steam检测功能需要主程序注入实现：
    - GameDetectorBase.set_steam_detector(detect_func, get_libraries_func)
    """

    STEAM_APP_ID: str = ""
    GAME_FOLDER_NAMES: List[str] = []
    EXECUTABLE_PATHS: List[str] = []
    LOCAL_MODS_FOLDER: str = ""

    _steam_detect_impl: Optional[Callable[[], Optional[str]]] = None
    _steam_libraries_impl: Optional[Callable[[str], List]] = None

    CONFIG_DIR_PATHS: Dict[str, List[str]] = {}

    _config: Optional["PluginConfig"] = None

    @classmethod
    def set_steam_detector(cls,
                           detect_func: Optional[Callable[[], Optional[str]]] = None,
                           get_libraries_func: Optional[Callable[[str], List]] = None) -> None:
        """注入Steam检测实现（由主程序调用）
        
        Args:
            detect_func: 检测Steam安装路径的函数，返回路径字符串或None
            get_libraries_func: 获取Steam库列表的函数，接收steam_path参数，返回库列表
        """
        if detect_func is not None:
            cls._steam_detect_impl = detect_func
        if get_libraries_func is not None:
            cls._steam_libraries_impl = get_libraries_func

    def _get_executable_paths(self) -> List[str]:
        """获取当前平台的可执行文件路径列表"""
        if self._config and self._config.path_validation:
            return self._config.path_validation.get_executable_paths()
        return self.EXECUTABLE_PATHS

    def _get_game_folder_names(self) -> List[str]:
        """获取当前平台的游戏文件夹名称列表"""
        if self._config and self._config.path_validation:
            return self._config.path_validation.get_game_folder_names()
        return self.GAME_FOLDER_NAMES

    def _get_local_mods_folder(self) -> str:
        """获取本地Mod文件夹名，子类应重写此方法"""
        return self.LOCAL_MODS_FOLDER

    def _get_config_dir_paths(self) -> List[str]:
        """获取当前平台的配置目录路径列表"""
        if self._config and self._config.path_validation:
            return self._config.path_validation.get_config_dir_paths()
        if self.CONFIG_DIR_PATHS:
            from .enum_types import Platform
            platform = Platform.current()
            return self.CONFIG_DIR_PATHS.get(platform.value, [])
        return []

    def detect_game_dir_paths(self) -> GamePaths:
        """检测游戏路径"""
        steam_path = self.detect_steam_install_path()
        if not steam_path:
            return GamePaths()

        libraries = self.get_steam_libraries(steam_path)
        game_dir_path = ""
        workshop_dir_path = ""
        local_mod_dir_path = ""

        for library in libraries:
            if not game_dir_path:
                game_dir_path = self.find_game_in_library(library)
            if not workshop_dir_path:
                workshop_dir_path = self.find_workshop_in_library(library)

        local_mods_folder = self._get_local_mods_folder()
        if game_dir_path and local_mods_folder:
            local_mod_dir_path = os.path.join(game_dir_path, local_mods_folder)
            if not os.path.exists(local_mod_dir_path):
                local_mod_dir_path = ""

        config_dir_path = self._detect_config_directory()

        return GamePaths(
            game_dir_path=game_dir_path,
            workshop_dir_path=workshop_dir_path,
            game_config_dir_path=config_dir_path,
            local_mod_dir_path=local_mod_dir_path
        )

    def _detect_config_directory(self) -> Optional[str]:
        """检测游戏配置目录
        
        支持的环境变量占位符: {APPDATA}, {LOCALAPPDATA}, {USERPROFILE}, {HOME}, {STEAM_APP_ID}
        """
        paths = self._get_config_dir_paths()
        if not paths:
            return None

        from .enum_types import Platform
        platform = Platform.current()

        env_map = {}

        match platform:
            case Platform.WINDOWS:
                env_map = {
                    "APPDATA": os.environ.get("APPDATA", ""),
                    "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", ""),
                    "USERPROFILE": os.environ.get("USERPROFILE", ""),
                }
            case Platform.LINUX:
                env_map = {
                    "HOME": os.environ.get("HOME", ""),
                    "STEAM_APP_ID": self.STEAM_APP_ID,
                }
            case Platform.MACOS:
                env_map = {
                    "HOME": os.environ.get("HOME", ""),
                }

        for path_template in paths:
            path = path_template
            for env_key, env_value in env_map.items():
                path = path.replace(f"{{{env_key}}}", env_value)
            if os.path.exists(path):
                return path

        return None

    def find_game_in_library(self, library) -> Optional[str]:
        """在Steam库中查找游戏"""
        common_path = library.common_path
        if not os.path.exists(common_path):
            return None

        folder_names = self._get_game_folder_names()
        for name in folder_names:
            game_dir_path = os.path.join(common_path, name)
            if os.path.exists(game_dir_path) and self._validate_game_dir_path(game_dir_path):
                return game_dir_path

        try:
            for item in os.listdir(common_path):
                game_dir_path = os.path.join(common_path, item)
                if os.path.isdir(game_dir_path) and self._validate_game_dir_path(game_dir_path):
                    return game_dir_path
        except (PermissionError, OSError) as e:
            logger.warning(f"Failed to list directory {common_path}: {e}")

        return None

    def _validate_game_dir_path(self, path: str) -> bool:
        """验证游戏路径，子类可重写"""
        for exec_path in self._get_executable_paths():
            full_path = os.path.join(path, exec_path)
            if os.path.exists(full_path):
                return True
        return False

    def find_workshop_in_library(self, library) -> Optional[str]:
        """在Steam库中查找创意工坊"""
        if not self.STEAM_APP_ID:
            return None
        workshop_dir_path = os.path.join(library.workshop_dir_path, self.STEAM_APP_ID)
        if os.path.exists(workshop_dir_path):
            return workshop_dir_path
        return None

    @classmethod
    def detect_steam_install_path(cls) -> Optional[str]:
        """检测Steam安装路径"""
        if cls._steam_detect_impl is not None:
            return cls._steam_detect_impl()
        raise NotImplementedError(
            "Steam detection not configured. "
            "Call GameDetectorBase.set_steam_detector() at application startup."
        )

    @classmethod
    def get_steam_libraries(cls, steam_path: str) -> List:
        """获取所有Steam库"""
        if cls._steam_libraries_impl is not None:
            return cls._steam_libraries_impl(steam_path)
        raise NotImplementedError(
            "Steam libraries detection not configured. "
            "Call GameDetectorBase.set_steam_detector() at application startup."
        )


class ModParserBase(ABC):
    """Mod解析器基类
    
    子类需要实现:
    - _parse_mod(): 解析单个Mod
    - _is_version_compatible(): 版本兼容性检查(可选)
    
    设计原则：
    - 解析器仅负责解析，不负责存储
    - Mod实例统一由ModManager存储和管理
    - 避免双重存储导致的不一致问题
    
    遵循规则P3：使用GamePaths聚合类管理路径，禁止离散路径参数
    """

    GAME_CORE_FOLDER: str = ""
    LOCAL_MODS_FOLDER: str = ""
    MOD_METADATA_FILE: str = ""
    CORE_MOD_ID: str = ""
    DLC_MOD_IDS: set = set()
    ID_SEPARATOR = "@"

    def __init__(
            self,
            config: PluginConfig,
            paths: GamePaths,
            i18n: Optional["I18nProtocol"] = None):
        self._config = config
        self._paths = paths
        self._i18n = i18n

        if not config:
            logger.error("PluginConfig is None")
            raise ValueError("PluginConfig is None")

        mod_parser_config = config.mod_parser
        if not mod_parser_config:
            logger.error("ModParserConfig is None")
            raise ValueError("ModParserConfig is None")

        self.GAME_CORE_FOLDER = mod_parser_config.game_core_folder
        self.LOCAL_MODS_FOLDER = mod_parser_config.local_mods_folder
        self.CORE_MOD_ID = mod_parser_config.game_core_id
        self.MOD_METADATA_FILE = mod_parser_config.mod_metadata_file
        self.DLC_MOD_IDS = set(mod_parser_config.game_dlc_ids)

    @property
    def game_dir_path(self) -> str:
        return self._paths.game_dir_path

    @property
    def workshop_dir_path(self) -> str:
        return self._paths.workshop_dir_path

    @property
    def local_mod_dir_path(self) -> str:
        return self._paths.local_mod_dir_path

    @property
    def game_version(self) -> str:
        return self._paths.game_version

    @property
    def paths(self) -> GamePaths:
        return self._paths

    def tr(self, key: str, *args) -> str:
        """翻译文本
        
        Args:
            key: 翻译键
            *args: 格式化参数
        
        Returns:
            翻译后的文本
        """
        if self._i18n:
            return self._i18n.tr(key, *args)
        return key if not args else key.format(*args)

    def scan_all_mods(self) -> List[Mod]:
        """扫描所有Mod，返回Mod列表（不存储）"""
        mods: List[Mod] = []
        mod_id_map: Dict[str, Mod] = {}

        if self.local_mod_dir_path and os.path.exists(self.local_mod_dir_path):
            self._scan_directory(mods, mod_id_map, self.local_mod_dir_path, mod_type=ModType.LOCAL)

        if self.workshop_dir_path and os.path.exists(self.workshop_dir_path):
            self._scan_workshop_directory(mods, mod_id_map, self.workshop_dir_path)

        return mods

    def _scan_directory(self, mods: List[Mod], mod_id_map: Dict[str, Mod],
                        directory: str, mod_type: ModType = ModType.LOCAL):
        """扫描目录中的Mod"""
        try:
            for item in os.listdir(directory):
                mod_path = os.path.join(directory, item)
                if os.path.isdir(mod_path):
                    mod = self._parse_mod(mod_path, mod_type=mod_type)
                    if mod:
                        self._add_mod(mods, mod_id_map, mod)
        except PermissionError as e:
            logger.warning(f"Permission denied scanning directory {directory}: {e}")

    def _scan_workshop_directory(self, mods: List[Mod], mod_id_map: Dict[str, Mod], directory: str):
        """扫描创意工坊目录"""
        try:
            for item in os.listdir(directory):
                mod_path = os.path.join(directory, item)
                if os.path.isdir(mod_path):
                    workshop_id = item if item.isdigit() else None
                    mod = self._parse_mod(mod_path, mod_type=ModType.WORKSHOP, workshop_id=workshop_id)
                    if mod:
                        self._add_mod(mods, mod_id_map, mod)
        except PermissionError as e:
            logger.warning(f"Permission denied scanning workshop directory {directory}: {e}")

    def _add_mod(self, mods: List[Mod], mod_id_map: Dict[str, Mod], mod: Mod):
        """添加Mod到列表，检测重复
        
        只保留第一个出现的mod，并在第一个mod上标记存在重复
        """
        if mod.id in mod_id_map:
            existing_mod = mod_id_map[mod.id]
            existing_mod.add_issue(ModIssueStatus.DUPLICATE)
            existing_mod.add_issue_detail(ModIssueStatus.DUPLICATE, self.tr("duplicate_path_detail", mod.path))
        else:
            mod_id_map[mod.id] = mod
            mods.append(mod)

    def _determine_mod_type(self, mod_id: str, original_type: ModType) -> ModType:
        """确定Mod类型(核心/DLC/本地/创意工坊)"""
        if original_type == ModType.CORE:
            if mod_id == self.CORE_MOD_ID:
                return ModType.CORE
            elif (not self.DLC_MOD_IDS) or (mod_id in self.DLC_MOD_IDS):
                return ModType.DLC
        return original_type

    @abstractmethod
    def _parse_mod(self, mod_path: str, mod_type: ModType = ModType.LOCAL, workshop_id: Optional[str] = None) -> \
            Optional[Mod]:
        """解析单个Mod，子类必须实现"""
        pass

    @staticmethod
    def validate_mod(mod: Mod) -> List[str]:
        """验证Mod，返回问题列表"""
        issues = []

        if mod.has_issue(ModIssueStatus.INCOMPLETE):
            issues.append("Mod is incomplete")

        if mod.has_issue(ModIssueStatus.VERSION_MISMATCH):
            issues.append("Game version mismatch")

        return issues


class PluginBase(ABC):
    """插件基类
    
    提供所有插件通用的功能：
    - 插件元信息（ID、名称、版本等）
    - 菜单项、工具栏项、面板
    - 事件订阅和处理
    - 高亮规则、过滤规则
    - 配置管理
    - 生命周期钩子

    - 拓展静态mod错误检测
    - 拓展动态mod错误检测
    - 自定义拓扑排序
    - 拓展mod列表右键菜单
    - 操作mod列表
    - 操作mod元数据
    - 操作游戏元数据
    
    遵循插件系统需求文档规范：
    - 仅传递管理者集合，禁止传递离散数据
    - 插件通过管理者集合获取所需能力
    """

    PLUGIN_TYPE: PluginType = PluginType.FEATURE
    PLUGIN_ID: str = ""
    PLUGIN_NAME: str = ""
    PLUGIN_VERSION: str = "1.0.0"
    PLUGIN_AUTHOR: str = ""
    PLUGIN_DESCRIPTION: str = ""

    def __init__(self):
        self._is_initialized: bool = False
        self._manager_collection: Optional["ManagerCollectionProtocol"] = None
        self._config: Dict[str, Any] = {}
        self._config_file_path: Optional[str] = None

    def tr(self, key: str, *args) -> str:
        if self._manager_collection:
            i18n = self._manager_collection.get_i18n()
            if i18n:
                return i18n.tr(key, *args)
        return key if not args else key.format(*args)

    def get_plugin_id(self) -> str:
        """获取插件ID"""
        return self.PLUGIN_ID

    def get_plugin_name(self) -> str:
        """获取插件名称"""
        return self.PLUGIN_NAME

    def get_plugin_version(self) -> str:
        """获取插件版本"""
        return self.PLUGIN_VERSION

    def get_plugin_type(self) -> PluginType:
        """获取插件类型"""
        return self.PLUGIN_TYPE

    def is_initialized(self) -> bool:
        """检查插件是否已初始化"""
        return self._is_initialized

    def get_manager_collection(self) -> Optional["ManagerCollectionProtocol"]:
        """获取管理者集合"""
        return self._manager_collection

    @staticmethod
    def get_menu_items() -> List[PluginMenuItem]:
        """获取插件提供的菜单项"""
        return []

    @staticmethod
    def get_toolbar_items() -> List[Dict[str, Any]]:
        """获取插件提供的工具栏按钮"""
        return []

    @staticmethod
    def get_panels() -> List[Dict[str, Any]]:
        """获取插件提供的面板"""
        return []

    @staticmethod
    def on_pre_initialize(context: Dict[str, Any]) -> Tuple[bool, str]:
        """预初始化钩子（生命周期第一步）"""
        return True, ""

    def on_initialize(self, manager_collection: "ManagerCollectionProtocol") -> Tuple[bool, str]:
        """初始化插件（生命周期第二步）"""
        self._manager_collection = manager_collection
        self._is_initialized = True
        return True, ""

    def on_startup_complete(self, context: Dict[str, Any]) -> None:
        """启动完成回调（生命周期第三步）"""
        pass

    def on_shutdown(self) -> None:
        """插件关闭时的清理工作（生命周期最后一步）"""
        self._is_initialized = False
        self._manager_collection = None

    @staticmethod
    def on_menu_action(action_id: str, manager_collection: "ManagerCollectionProtocol") -> Optional[PluginResult]:
        """处理菜单动作"""
        return None

    def on_game_changed(self, game_id: str) -> None:
        """游戏切换时的回调"""
        pass

    def on_event(self, event: PluginEvent) -> None:
        """事件处理回调"""
        pass

    @staticmethod
    def get_subscribed_events() -> List[PluginEventType]:
        """获取插件订阅的事件类型列表"""
        return []

    def get_config(self, key: str, default: Any = None) -> Any:
        """获取插件配置项"""
        return self._config.get(key, default)

    def set_config(self, key: str, value: Any) -> None:
        """设置插件配置项"""
        self._config[key] = value

    def save_config(self) -> bool:
        if not self._config_file_path:
            return False

        try:
            from core.json_serializer import get_json_manager
            json_manager = get_json_manager()
            return json_manager.save_dict_to_file(self._config, self._config_file_path)
        except Exception as e:
            logger.error(f"Failed to save plugin config to {self._config_file_path}: {e}")
            return False

    def load_config(self, config_dir: str) -> bool:
        self._config_file_path = os.path.join(config_dir, "plugins", f"{self.PLUGIN_ID}.json")

        if not os.path.exists(self._config_file_path):
            return False

        try:
            from core.json_serializer import get_json_manager
            json_manager = get_json_manager()
            self._config = json_manager.load_dict_from_file(self._config_file_path, default={})
            return True
        except Exception as e:
            logger.error(f"Failed to load plugin config from {self._config_file_path}: {e}")
            return False

    @staticmethod
    def get_default_config() -> Dict[str, Any]:
        """获取默认配置"""
        return {}

    def register_highlight_rule(
            self,
            rule_id: str,
            condition: Callable[[Mod], bool],
            background_color: str,
            border_color: Optional[str] = None,
            priority: int = 0,
            description: str = ""
    ) -> bool:
        """注册高亮规则
        
        Args:
            rule_id: 规则唯一标识（插件内唯一）
            condition: 条件函数，接收Mod对象，返回bool
            background_color: 背景颜色（十六进制）
            border_color: 边框颜色（可选）
            priority: 优先级，数值越大优先级越高
            description: 规则描述
        
        Returns:
            是否注册成功
        """
        if not self._manager_collection:
            return False

        highlight_manager = self._manager_collection.get_highlight_rule_manager()
        if not highlight_manager:
            return False

        return highlight_manager.register_rule(
            rule_id=rule_id,
            plugin_id=self.PLUGIN_ID,
            condition=condition,
            background_color=background_color,
            border_color=border_color,
            priority=priority,
            description=description
        )

    def unregister_highlight_rule(self, rule_id: str) -> bool:
        """注销高亮规则"""
        if not self._manager_collection:
            return False

        highlight_manager = self._manager_collection.get_highlight_rule_manager()
        if not highlight_manager:
            return False

        return highlight_manager.unregister_rule(rule_id, self.PLUGIN_ID)

    def set_highlight_rule_enabled(self, rule_id: str, enabled: bool) -> bool:
        """设置高亮规则启用状态"""
        if not self._manager_collection:
            return False

        highlight_manager = self._manager_collection.get_highlight_rule_manager()
        if not highlight_manager:
            return False

        return highlight_manager.set_rule_enabled(rule_id, self.PLUGIN_ID, enabled)

    def register_filter_rule(
            self,
            rule_id: str,
            condition: Callable[[Mod], bool],
            description: str = ""
    ) -> bool:
        """注册过滤规则"""
        if not self._manager_collection:
            return False

        filter_manager = self._manager_collection.get_mod_filter_manager()
        if not filter_manager:
            return False

        return filter_manager.register_filter(
            rule_id=rule_id,
            plugin_id=self.PLUGIN_ID,
            condition=condition,
            description=description
        )

    def unregister_filter_rule(self, rule_id: str) -> bool:
        """注销过滤规则"""
        if not self._manager_collection:
            return False

        filter_manager = self._manager_collection.get_mod_filter_manager()
        if not filter_manager:
            return False

        return filter_manager.unregister_filter(rule_id, self.PLUGIN_ID)

    def notify_highlight_changed(self) -> None:
        """通知高亮规则已变更"""
        from .events import get_event_bus
        get_event_bus().publish(
            PluginEventType.MOD_HIGHLIGHT_RULES_CHANGED,
            {"plugin_id": self.PLUGIN_ID}
        )

    def notify_filter_changed(self) -> None:
        """通知过滤规则已变更"""
        from .events import get_event_bus
        get_event_bus().publish(
            PluginEventType.MOD_FILTER_RULES_CHANGED,
            {"plugin_id": self.PLUGIN_ID}
        )

    def notify_mod_list_changed(self) -> None:
        """通知Mod列表已变更"""
        from .events import get_event_bus
        get_event_bus().publish(
            PluginEventType.MOD_LIST_CHANGED,
            {"plugin_id": self.PLUGIN_ID}
        )

    def static_error_check(self, mods: List[Mod], game_metadata: GameMetadata) -> None:
        """拓展静态Mod错误检测
        
        在Mod加载时调用一次，用于检测Mod本身的静态问题。
        插件应直接调用 mod.add_issue() 添加问题标记。
        
        Args:
            mods: Mod列表
            game_metadata: 游戏元数据（已缓存，无需重新加载）
        """
        pass

    def dynamic_error_check(self, mods: List[Mod], game_metadata: GameMetadata,
                            manager_collection: "ManagerCollectionProtocol") -> None:
        """拓展动态Mod错误检测
        
        在启用列表发生变化时实时调用，用于检测Mod之间的动态依赖问题。
        插件应直接调用 mod.add_issue() 添加问题标记。
        
        Args:
            mods: Mod列表
            game_metadata: 游戏元数据（已缓存，无需重新加载）
            manager_collection: 管理者集合
        """
        pass

    @staticmethod
    def custom_topological_sort(mods: List[Mod],
                                manager_collection: "ManagerCollectionProtocol") -> None:
        """自定义拓扑排序
        
        Args:
            mods: Mod列表
            manager_collection: 管理者集合
        
        Returns:
            排序后的Mod列表，返回None表示使用默认排序
        """
        return None

    @staticmethod
    def get_context_menu_items(selected_mods: List[Mod],
                               manager_collection: "ManagerCollectionProtocol") -> List[Dict[str, Any]]:
        """拓展Mod列表右键菜单
        
        Args:
            selected_mods: 选中的Mod列表
            manager_collection: 管理者集合
        
        Returns:
            菜单项列表，每个菜单项为字典格式
        """
        return []

    @staticmethod
    def on_mod_list_action(action_id: str, selected_mods: List[Mod],
                           manager_collection: "ManagerCollectionProtocol") -> Optional[Any]:
        """处理Mod列表动作
        
        Args:
            action_id: 动作ID
            selected_mods: 选中的Mod列表
            manager_collection: 管理者集合
        
        Returns:
            动作结果
        """
        return None

    @staticmethod
    def update_mod_metadata(mod: Mod, metadata: ModMetadata,
                            manager_collection: "ManagerCollectionProtocol") -> ModMetadata:
        """操作Mod元数据
        
        Args:
            mod: Mod对象
            metadata: 元数据
            manager_collection: 管理者集合
        
        Returns:
            更新后的元数据
        """
        return metadata

    @staticmethod
    def update_game_metadata(game_metadata: GameMetadata,
                             manager_collection: "ManagerCollectionProtocol") -> GameMetadata:
        """操作游戏元数据
        
        Args:
            game_metadata: 游戏元数据
            manager_collection: 管理者集合
        
        Returns:
            更新后的游戏元数据
        """
        return game_metadata


class GameAdapter(PluginBase):
    """游戏适配器基类
    
    游戏插件必须继承此类，实现游戏特定的功能。
    游戏插件之间互斥，同一时间只能启用一个。
    
    必须实现的功能：
    - 游戏元数据加载
    - Mod元数据加载
    - 游戏启动
    
    可选实现的功能：
    - 路径检测
    - 外部配置文件解析
        - 存档解析
    
    遵循规则P3：使用GamePaths聚合类管理路径，禁止离散路径参数
    """

    PLUGIN_TYPE = PluginType.GAME

    def __init__(self, config: PluginConfig):
        super().__init__()
        self._config: PluginConfig = config
        self._game_info: Optional[GameInfo] = self._config.game_info if self._config else None

    @property
    def game_id(self) -> str:
        """获取游戏ID"""
        return self._game_info.game_id if self._game_info else ""

    @property
    def game_steam_app_id(self) -> str:
        """获取游戏Steam应用ID"""
        return self._game_info.steam_app_id if self._game_info else ""

    @property
    def game_name(self) -> str:
        """获取游戏名称"""
        if self._game_info:
            return self._game_info.default_name
        return ""

    @property
    def game_version(self) -> str:
        """获取游戏版本"""
        return self._game_info.version if self._game_info else ""

    def get_game_info(self) -> Optional[GameInfo]:
        """获取游戏信息"""
        return self._game_info

    def get_config(self, **kwargs) -> PluginConfig:
        """获取插件配置"""
        return self._config

    @abstractmethod
    def get_mod_parser(self, paths: GamePaths,
                       i18n: Optional["I18nProtocol"] = None) -> ModParserBase:
        """获取Mod解析器实例
        
        Args:
            paths: 游戏路径配置（GamePaths聚合类）
            i18n: 国际化管理器（可选）
        
        Returns:
            Mod解析器实例
        """
        pass

    @abstractmethod
    def launch_game_native(self, manager_collection: "ManagerCollectionProtocol") -> Tuple[bool, str]:
        """本地启动游戏
        
        Args:
            manager_collection: 管理者集合
        
        Returns:
            (是否启动成功, 错误信息)
        """
        pass

    @abstractmethod
    def launch_game_steam(self, manager_collection: "ManagerCollectionProtocol") -> Tuple[bool, str]:
        """通过Steam启动游戏
        
        Args:
            manager_collection: 管理者集合
        
        Returns:
            (是否启动成功, 错误信息)
        """
        pass

    @staticmethod
    def get_game_detector() -> Optional[GameDetectorBase]:
        """获取游戏检测器（可选实现）"""
        return None

    @staticmethod
    def get_save_parser_capabilities() -> List[SaveParserCapability]:
        """获取存档解析能力（可选实现）"""
        return []

    @staticmethod
    def parse_save_file(file_path: str, manager_collection: "ManagerCollectionProtocol" = None,
                        **kwargs) -> SaveParseResult:
        """解析存档文件（可选实现）"""
        return SaveParseResult.error("Save parsing not implemented")

    @staticmethod
    def parse_external_config(file_path: str) -> SaveParseResult:
        """解析外部配置文件（可选实现）"""
        return SaveParseResult.error("External config parsing not implemented")

    @staticmethod
    def validate_paths(paths: GamePaths) -> Dict[str, bool]:
        """验证游戏路径（可选实现）
        
        Args:
            paths: 游戏路径配置
        
        Returns:
            各路径验证结果
        """
        return {"game_dir": bool(paths.game_dir_path)}

    @staticmethod
    def validate_required_paths(paths: GamePaths) -> Tuple[bool, List[str]]:
        """验证必要路径（可选实现）
        
        Args:
            paths: 游戏路径配置
        
        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []
        if not paths.game_dir_path:
            errors.append("Game directory path is required")
        return len(errors) == 0, errors

    def load_game_metadata(self, paths: GamePaths) -> GameMetadata:
        """加载游戏元数据（可选实现）
        
        Args:
            paths: 游戏路径配置
        """
        return GameMetadata(
            game_id=self.game_id,
            game_name=self.game_name,
            game_version=paths.game_version or self.game_version,
            install_path=paths.game_dir_path,
            workshop_path=paths.workshop_dir_path,
            local_mod_path=paths.local_mod_dir_path,
            config_path=paths.game_config_dir_path,
        )

    @staticmethod
    def load_mod_metadata(mod: Mod) -> ModMetadata:
        """加载Mod元数据（可选实现）"""
        return ModMetadata(
            mod_id=mod.id,
            name=mod.name,
            version=mod.version,
        )

    def static_error_check(self, mods: List[Mod], game_metadata: GameMetadata) -> None:
        """静态错误检测（可选实现）"""
        pass

    @staticmethod
    def detect_game_version(paths: GamePaths) -> str:
        """检测游戏版本（可选实现）
        
        Args:
            paths: 游戏路径配置
        """
        return ""

    @staticmethod
    def save_mod_order(manager_collection: "ManagerCollectionProtocol",
                       config_dir_path: str = None) -> Tuple[bool, str]:
        """保存Mod顺序（可选实现）"""
        return True, ""

    def get_default_settings(self) -> Dict[str, Any]:
        """获取默认设置（可选实现）"""
        if self._config and self._config.default_settings:
            return self._config.default_settings.copy()
        return {}

    def get_custom_data(self) -> Dict[str, Any]:
        """获取自定义数据（可选实现）"""
        if self._config and self._config.custom_data:
            return self._config.custom_data.copy()
        return {}

    def create_detector(self) -> Optional[GameDetectorBase]:
        """创建游戏检测器（可选实现）"""
        return self.get_game_detector()

    def is_case_sensitive_id(self) -> bool:
        """是否区分ID大小写"""
        return self._config.case_sensitive_id if self._config else False

    def get_save_file_filter(self) -> str:
        """获取存档文件过滤器（可选实现）"""
        caps = self.get_save_parser_capabilities()
        if not caps:
            return "All Files (*)"
        extensions = []
        for cap in caps:
            for ext in cap.supported_extensions:
                extensions.append(f"*{ext}")
        if extensions:
            return f"Save Files ({' '.join(extensions)});;All Files (*)"
        return "All Files (*)"

    @staticmethod
    def create_save_import_profile(parse_result: SaveParseResult,
                                   manager_collection: "ManagerCollectionProtocol") -> Optional[Any]:
        """从存档解析结果创建导入配置（可选实现）"""
        return None

    @staticmethod
    def prepare_for_launch(manager_collection: "ManagerCollectionProtocol") -> Tuple[bool, str]:
        """启动前准备（可选实现）"""
        return True, ""

    @staticmethod
    def validate_game_dir_path(path: str) -> bool:
        """验证游戏目录路径（可选实现）"""
        return bool(path)


class FeaturePlugin(PluginBase):
    """功能插件基类
    
    功能插件继承此类，实现自定义功能。
    功能插件之间不互斥，可同时启用多个。
    功能插件与游戏插件不互斥，可混合启用。
    
    功能插件可以：
    - 添加菜单项
    - 添加工具栏按钮
    - 添加自定义面板
    - 订阅和处理事件
    - 注册高亮规则
    - 注册过滤规则
    - 管理自己的配置
    """

    PLUGIN_TYPE = PluginType.FEATURE
