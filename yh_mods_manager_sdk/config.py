"""
配置相关数据类型
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .enum_types import Platform


@dataclass
class PlatformPaths:
    """平台相关路径配置
    
    支持多平台差异化路径配置，自动根据当前平台返回对应路径
    
    示例:
        PlatformPaths(
            windows=["bin/Win64_Shipping_Client/Game.exe", "Game.exe"],
            linux=["bin/Linux64_Shipping_Client/Game.x86_64"],
            macos=["Game.app/Contents/MacOS/Game"]
        )
    """
    windows: List[str] = field(default_factory=list)
    linux: List[str] = field(default_factory=list)
    macos: List[str] = field(default_factory=list)

    @classmethod
    def from_config(cls, config: Dict[str, List[str]]) -> "PlatformPaths":
        """从配置字典创建实例
        
        格式: {"windows": [...], "linux": [...], "macos": [...]}
        """
        return cls(
            windows=config.get("windows", []),
            linux=config.get("linux", []),
            macos=config.get("macos", [])
        )

    def get_for_platform(self, platform: Platform) -> List[str]:
        """获取指定平台的路径列表"""
        match platform:
            case Platform.WINDOWS:
                return self.windows
            case Platform.LINUX:
                return self.linux
            case Platform.MACOS:
                return self.macos
            case _:
                return self.windows

    def get_for_current_platform(self) -> List[str]:
        """获取当前平台的路径列表"""
        return self.get_for_platform(Platform.current())

    def is_empty(self) -> bool:
        """检查所有平台是否都为空"""
        return not (self.windows or self.linux or self.macos)

    def all_paths(self) -> List[str]:
        """获取所有平台的路径（用于搜索）"""
        return list(set(self.windows + self.linux + self.macos))


@dataclass
class PlatformPathMap:
    """平台相关路径映射
    
    用于键值对形式的平台差异化配置（如required_paths）
    
    示例:
        PlatformPathMap({
            "windows": {"mods": "Mods", "config": "Config"},
            "linux": {"mods": "mods", "config": ".config"}
        })
    """
    windows: Dict[str, str] = field(default_factory=dict)
    linux: Dict[str, str] = field(default_factory=dict)
    macos: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_config(cls, config: Dict[str, Dict[str, str]]) -> "PlatformPathMap":
        """从配置字典创建实例
        
        格式: {"windows": {...}, "linux": {...}, "macos": {...}}
        """
        if not config:
            return cls()

        return cls(
            windows=config.get("windows", {}),
            linux=config.get("linux", {}),
            macos=config.get("macos", {})
        )

    def get_for_platform(self, platform: Platform) -> Dict[str, str]:
        """获取指定平台的路径映射"""
        match platform:
            case Platform.WINDOWS:
                return self.windows
            case Platform.LINUX:
                return self.linux
            case Platform.MACOS:
                return self.macos
            case _:
                return self.windows

    def get_for_current_platform(self) -> Dict[str, str]:
        """获取当前平台的路径映射"""
        return self.get_for_platform(Platform.current())

    def is_empty(self) -> bool:
        """检查所有平台是否都为空"""
        return not (self.windows or self.linux or self.macos)


@dataclass
class GamePaths:
    """游戏路径配置
    
    作为插件系统中路径信息的唯一数据源，所有路径相关方法都应使用此类。
    遵循规则P3：禁止硬编码，使用JSON或其它合理配置。
    """
    game_dir_path: str = ""
    workshop_dir_path: str = ""
    game_config_dir_path: str = ""
    local_mod_dir_path: str = ""
    default_save_dir_path: str = ""
    game_version: str = ""
    custom_paths: Dict[str, str] = field(default_factory=dict)

    def is_valid(self) -> bool:
        return bool(self.game_dir_path)

    def with_version(self, version: str) -> "GamePaths":
        """返回带有版本信息的新实例"""
        return GamePaths(
            game_dir_path=self.game_dir_path,
            workshop_dir_path=self.workshop_dir_path,
            game_config_dir_path=self.game_config_dir_path,
            local_mod_dir_path=self.local_mod_dir_path,
            default_save_dir_path=self.default_save_dir_path,
            game_version=version,
            custom_paths=self.custom_paths.copy()
        )

    def with_paths(self, **kwargs) -> "GamePaths":
        """返回更新了指定路径的新实例"""
        return GamePaths(
            game_dir_path=kwargs.get("game_dir_path", self.game_dir_path),
            workshop_dir_path=kwargs.get("workshop_dir_path", self.workshop_dir_path),
            game_config_dir_path=kwargs.get("game_config_dir_path", self.game_config_dir_path),
            local_mod_dir_path=kwargs.get("local_mod_dir_path", self.local_mod_dir_path),
            default_save_dir_path=kwargs.get("default_save_dir_path", self.default_save_dir_path),
            game_version=kwargs.get("game_version", self.game_version),
            custom_paths=kwargs.get("custom_paths", self.custom_paths.copy())
        )


@dataclass
class GameInfo:
    """游戏信息"""
    game_id: str = ""
    default_name: str = ""
    version: str = ""
    description: str = ""
    icon: str = ""
    author: str = ""
    website: str = ""
    steam_app_id: str = ""

    @classmethod
    def from_config(cls, config: dict) -> "GameInfo":
        return cls(
            game_id=config.get("game_id", ""),
            steam_app_id=config.get("steam_app_id", ""),
            default_name=config.get("default_name", ""),
            version=config.get("version", ""),
            description=config.get("description", ""),
            icon=config.get("icon", ""),
            author=config.get("author", ""),
            website=config.get("website", "")
        )


@dataclass
class PathValidation:
    """路径验证规则
    
    支持平台差异化配置，所有路径配置都支持按平台区分
    
    配置格式示例:
    {
        "executable_paths": {
            "windows": ["bin/Win64/Game.exe"],
            "linux": ["bin/Linux64/Game.x86_64"]
        },
        "game_folder_names": ["GameName"],
        "required_paths": {
            "windows": {"mods": "Mods"},
            "linux": {"mods": "mods"}
        },
        "config_dir_paths": {
            "windows": ["{USERPROFILE}/Documents/Game"],
            "linux": ["{HOME}/.config/Game"]
        }
    }
    
    也支持简写格式（所有平台相同）:
    {
        "executable_paths": ["Game.exe"],
        "game_folder_names": ["GameName"],
        "required_paths": {"mods": "Mods"}
    }
    """
    executable_paths: PlatformPaths = field(default_factory=PlatformPaths)
    game_folder_names: PlatformPaths = field(default_factory=PlatformPaths)
    required_paths: PlatformPathMap = field(default_factory=PlatformPathMap)
    config_dir_paths: PlatformPaths = field(default_factory=PlatformPaths)
    version_file: str = ""
    game_dir_path_markers: List[str] = field(default_factory=list)
    mod_path_markers: List[str] = field(default_factory=list)

    @classmethod
    def from_config(cls, config: dict) -> "PathValidation":
        return cls(
            executable_paths=PlatformPaths.from_config(config.get("executable_paths", {})),
            game_folder_names=PlatformPaths.from_config(config.get("game_folder_names", {})),
            required_paths=PlatformPathMap.from_config(config.get("required_paths", {})),
            config_dir_paths=PlatformPaths.from_config(config.get("config_dir_paths", {})),
            version_file=config.get("version_file", ""),
            game_dir_path_markers=config.get("game_dir_path_markers", []),
            mod_path_markers=config.get("mod_path_markers", [])
        )

    def get_executable_paths(self) -> List[str]:
        """获取当前平台的可执行文件路径列表"""
        return self.executable_paths.get_for_current_platform()

    def get_game_folder_names(self) -> List[str]:
        """获取当前平台的游戏文件夹名称列表"""
        return self.game_folder_names.get_for_current_platform()

    def get_required_paths(self) -> Dict[str, str]:
        """获取当前平台的必需路径映射"""
        return self.required_paths.get_for_current_platform()

    def get_config_dir_paths(self) -> List[str]:
        """获取当前平台的配置目录路径列表"""
        return self.config_dir_paths.get_for_current_platform()


@dataclass
class ModParserConfig:
    """Mod解析器配置"""
    game_core_folder: str = ""
    local_mods_folder: str = ""
    game_core_id: str = ""
    game_dlc_ids: List[str] = field(default_factory=list)
    mod_metadata_file: str = ""

    @classmethod
    def from_config(cls, config: dict) -> "ModParserConfig":
        return cls(
            game_core_folder=config.get("game_core_folder", ""),
            local_mods_folder=config.get("local_mods_folder", ""),
            game_core_id=config.get("game_core_id", ""),
            game_dlc_ids=config.get("game_dlc_ids", []),
            mod_metadata_file=config.get("mod_metadata_file", "")
        )


@dataclass
class PluginConfig:
    """插件配置
    
    序列化逻辑由 core.serializers.PluginConfigSerializer 处理
    文件加载由 core.json_serializer.JsonSerializeManager 处理
    """
    plugin_id: str = ""
    plugin_version: str = "1.0.0"
    name: str = ""
    description: str = ""
    author: str = ""
    game_info: Optional[GameInfo] = None
    path_validation: Optional[PathValidation] = None
    mod_parser: Optional[ModParserConfig] = None
    default_settings: Dict[str, Any] = field(default_factory=dict)
    custom_data: Dict[str, Any] = field(default_factory=dict)
    case_sensitive_id: bool = False


@dataclass
class SaveParseResult:
    """存档解析结果"""
    success: bool = True
    mod_order: List[str] = field(default_factory=list)
    game_version: str = ""
    error_message: str = ""
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def error(cls, message: str) -> "SaveParseResult":
        return cls(success=False, error_message=message)


@dataclass
class SaveParserCapability:
    """存档解析器能力标识"""
    supported_extensions: List[str] = field(default_factory=list)
    supported_versions: List[str] = field(default_factory=list)
    description: str = ""
    priority: int = 0


@dataclass
class GameMetadata:
    """游戏元数据
    
    与Mod元数据完全独立，格式不同、结构不同、用途不同
    """
    game_id: str = ""
    game_version: str = ""
    game_name: str = ""
    architecture: str = ""
    platform: str = ""
    install_path: str = ""
    workshop_path: str = ""
    local_mod_path: str = ""
    config_path: str = ""
    last_scan_time: str = ""
    custom_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModMetadata:
    """Mod元数据
    
    与游戏元数据完全独立，格式不同、结构不同、用途不同
    保留Mod原生格式，不转换、不统一、不合并
    """
    mod_id: str = ""
    original_id: str = ""
    name: str = ""
    version: str = ""
    authors: List[str] = field(default_factory=list)
    description: str = ""
    path: str = ""
    mod_type: str = ""
    workshop_id: str = ""
    preview_image: str = ""
    supported_versions: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    load_before: List[str] = field(default_factory=list)
    load_after: List[str] = field(default_factory=list)
    incompatible_with: List[str] = field(default_factory=list)
    raw_metadata: Dict[str, Any] = field(default_factory=dict)
    scan_time: str = ""


@dataclass
class ModProfile:
    """Mod 配置方案
    
    用于保存和管理Mod的加载顺序配置
    """
    game_id: str = ""
    game_version: str = ""
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now().isoformat())
    mod_order: List[str] = field(default_factory=list)
