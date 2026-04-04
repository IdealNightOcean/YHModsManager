"""
工具类模块
"""

import logging
import os
import subprocess
import webbrowser
from dataclasses import dataclass, field
from typing import Tuple, Optional, Dict, Any

from .enum_types import ModType, Platform

logger = logging.getLogger(__name__)


@dataclass
class PluginResult:
    """插件操作结果"""
    success: bool = True
    message: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, message: str = "", **kwargs) -> "PluginResult":
        return cls(success=True, message=message, data=kwargs)

    @classmethod
    def error(cls, message: str, **kwargs) -> "PluginResult":
        return cls(success=False, message=message, data=kwargs)


class PlatformUtils:
    """平台工具类"""
    _current_platform: Optional[Platform] = None

    @classmethod
    def current_platform(cls) -> Platform:
        if cls._current_platform is None:
            cls._current_platform = Platform.current()
        return cls._current_platform

    @classmethod
    def is_windows(cls) -> bool:
        return cls.current_platform().is_windows()

    @classmethod
    def is_linux(cls) -> bool:
        return cls.current_platform().is_linux()

    @classmethod
    def is_macos(cls) -> bool:
        return cls.current_platform().is_macos()

    @classmethod
    def open_path(cls, path: str) -> PluginResult:
        if not path or not os.path.exists(path):
            return PluginResult.error("path_not_found", path=path)

        try:
            platform = cls.current_platform()
            match platform:
                case Platform.WINDOWS:
                    os.startfile(path)
                case Platform.LINUX:
                    subprocess.Popen(["xdg-open", path])
                case Platform.MACOS:
                    subprocess.Popen(["open", path])

            return PluginResult.ok()
        except Exception as e:
            logger.error(f"Error opening URL: {e}")
            return PluginResult.error(str(e))

    @classmethod
    def launch_steam_url(cls, steam_app_id: str, use_rungameid: bool = True) -> PluginResult:
        if not steam_app_id:
            return PluginResult.error("steam_app_id_empty")

        try:
            if use_rungameid:
                steam_url = f"steam://rungameid/{steam_app_id}"
            else:
                steam_url = f"steam://run/{steam_app_id}"
            platform = cls.current_platform()
            match platform:
                case Platform.WINDOWS:
                    os.startfile(steam_url)
                case Platform.LINUX:
                    subprocess.Popen(["xdg-open", steam_url])
                case Platform.MACOS:
                    subprocess.Popen(["open", steam_url])

            return PluginResult.ok()
        except Exception as e:
            logger.error(f"Error opening Steam URL: {e}")
            return PluginResult.error(str(e))

    @classmethod
    def launch_executable(cls, exe_path: str, **kwargs) -> PluginResult:
        if not exe_path or not os.path.exists(exe_path):
            return PluginResult.error("executable_not_found", path=exe_path)

        working_dir = kwargs.get('working_dir') or kwargs.get('cwd')

        try:
            platform = cls.current_platform()
            match platform:
                case Platform.WINDOWS:
                    subprocess.Popen([exe_path],
                                     shell=False,
                                     cwd=working_dir,
                                     creationflags=subprocess.DETACHED_PROCESS)
                case Platform.LINUX:
                    subprocess.Popen([exe_path], cwd=working_dir)
                case Platform.MACOS:
                    subprocess.Popen(["open", exe_path], cwd=working_dir)

            return PluginResult.ok()
        except Exception as e:
            logger.error(f"Error launching executable {exe_path}: {e}")
            return PluginResult.error(str(e))

    @classmethod
    def open_workshop_page(cls, workshop_id: str) -> PluginResult:
        if not workshop_id:
            return PluginResult.error("workshop_id_empty")

        steam_url = f"steam://openurl/https://steamcommunity.com/sharedfiles/filedetails/?id={workshop_id}"
        web_url = f"https://steamcommunity.com/sharedfiles/filedetails/?id={workshop_id}"

        try:
            platform = cls.current_platform()

            try:
                match platform:
                    case Platform.WINDOWS:
                        os.startfile(steam_url)
                    case Platform.LINUX:
                        subprocess.Popen(["xdg-open", steam_url])
                    case Platform.MACOS:
                        subprocess.Popen(["open", steam_url])

                steam_opened = True
            except Exception as e:
                logger.warning(f"Failed to open Steam URL {steam_url}: {e}")
                steam_opened = False

            if not steam_opened:
                webbrowser.open(web_url)

            return PluginResult.ok()
        except Exception as e:
            logger.error(f"Error opening workshop page: {e}")
            return PluginResult.error(str(e))


class ModIDUtils:
    """Mod ID工具类"""

    ID_SEPARATOR = "@"

    @staticmethod
    def generate_mod_id(original_id: str, mod_type: ModType) -> str:
        """生成Mod ID"""
        return f"{original_id}{ModIDUtils.ID_SEPARATOR}{mod_type.value}"

    @staticmethod
    def parse_mod_id(mod_id: str) -> Tuple[str, str]:
        """解析Mod ID，返回(original_id, type_str)"""
        if ModIDUtils.ID_SEPARATOR in mod_id:
            parts = mod_id.rsplit(ModIDUtils.ID_SEPARATOR, 1)
            return parts[0], parts[1]
        return mod_id, "local"

    @staticmethod
    def get_original_id(mod_id: str) -> str:
        """获取原始ID"""
        original_id, _ = ModIDUtils.parse_mod_id(mod_id)
        return original_id
