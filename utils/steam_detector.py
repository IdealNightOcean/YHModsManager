"""
Steam检测器 - 通用模块
提供Steam安装路径和库检测功能
"""

import logging
import os
import re
import winreg
from dataclasses import dataclass
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)


@dataclass
class SteamLibrary:
    """Steam库信息"""
    path: str
    label: str = ""

    @property
    def steamapps_path(self) -> str:
        return os.path.join(self.path, "steamapps")

    @property
    def workshop_dir_path(self) -> str:
        return os.path.join(self.path, "steamapps", "workshop", "content")

    @property
    def common_path(self) -> str:
        return os.path.join(self.path, "steamapps", "common")


class SteamDetector:
    """Steam检测器 - 提供通用的Steam检测功能"""

    REGISTRY_PATHS = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Valve\Steam"),
    ]

    @classmethod
    def detect_steam_install_path(cls) -> Optional[str]:
        """检测Steam安装路径"""
        for hkey, subkey in cls.REGISTRY_PATHS:
            try:
                key = winreg.OpenKey(hkey, subkey, 0, winreg.KEY_READ)
                install_path, _ = winreg.QueryValueEx(key, "InstallPath")
                winreg.CloseKey(key)
                if install_path and os.path.exists(install_path):
                    return install_path
            except (WindowsError, OSError) as e:
                logger.debug(f"Registry key not found {hkey}\\{subkey}: {e}")
                continue
        return None

    @classmethod
    def get_steam_libraries(cls, steam_path: str) -> List[SteamLibrary]:
        """获取所有Steam库"""
        libraries = []

        if not steam_path or not os.path.exists(steam_path):
            return libraries

        libraries.append(SteamLibrary(path=steam_path, label="默认库"))

        library_folders_path = os.path.join(steam_path, "steamapps", "libraryfolders.vdf")

        if not os.path.exists(library_folders_path):
            return libraries

        try:
            with open(library_folders_path, "r", encoding="utf-8") as f:
                content = f.read()

            path_pattern = r'"path"\s+"([^"]+)"'
            label_pattern = r'"label"\s+"([^"]*)"'

            path_matches = re.findall(path_pattern, content)
            label_matches = re.findall(label_pattern, content)

            for i, path in enumerate(path_matches):
                if path and os.path.exists(path):
                    label = label_matches[i] if i < len(label_matches) else ""
                    if not any(lib.path == path for lib in libraries):
                        libraries.append(SteamLibrary(path=path, label=label))

        except (IOError, UnicodeDecodeError) as e:
            logger.warning(f"Failed to read Steam library folders: {e}")

        return libraries

    @classmethod
    def get_steam_libraries_info(cls) -> List[Dict]:
        """获取Steam库信息"""
        steam_path = cls.detect_steam_install_path()
        if not steam_path:
            return []

        libraries = cls.get_steam_libraries(steam_path)
        result = []

        for lib in libraries:
            info = {
                "path": lib.path,
                "label": lib.label,
            }
            result.append(info)

        return result
