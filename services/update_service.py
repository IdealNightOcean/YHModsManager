"""
更新服务模块
负责从静态托管检测更新、下载更新、安全安装更新
"""

import json
import logging
import os
import shutil
import zipfile
from dataclasses import dataclass
from typing import Callable, List, Optional, Tuple

from utils.file_utils import get_app_data_dir, get_resource_path
from yh_mods_manager_sdk.enum_types import Platform

logger = logging.getLogger(__name__)


@dataclass
class UpdateInfo:
    version: str
    release_date: str
    release_notes: str
    download_url: str
    file_size: int
    file_name: str


@dataclass
class ChangelogEntry:
    version: str
    date: str
    changes: List[str]


class UpdateService:
    CHECK_CACHE_DURATION = 600

    def __init__(self):
        self._app_info_data = None
        self._check_cache: Optional[Tuple[float, bool, Optional[UpdateInfo]]] = None
        self._remote_data_cache: Optional[Tuple[float, dict]] = None

    def _load_app_info(self) -> dict:
        if self._app_info_data:
            return self._app_info_data

        resource_path = get_resource_path("config/app_info.json")
        if os.path.exists(resource_path):
            try:
                with open(resource_path, "r", encoding="utf-8") as f:
                    self._app_info_data = json.load(f)
                    return self._app_info_data
            except Exception as e:
                logger.error(f"Failed to load app info from resource: {e}")

        return self._get_default_app_info()

    @staticmethod
    def _get_default_app_info() -> dict:
        return {
            "current_version": "1.0.0",
            "version_check_url": "https://idealnightocean.github.io/YHModsManager/version.json",
            "github_repo": "IdealNightOcean/YHModsManager",
            "license": "AGPL v3",
            "author": "NightOcean"
        }

    def get_current_version(self) -> str:
        data = self._load_app_info()
        return data.get("current_version", "1.0.0")

    def get_version_check_url(self) -> str:
        data = self._load_app_info()
        return data.get("version_check_url", "https://idealnightocean.github.io/YHModsManager/version.json")

    def get_github_repo(self) -> str:
        data = self._load_app_info()
        return data.get("github_repo", "IdealNightOcean/YHModsManager")

    def get_license(self) -> str:
        data = self._load_app_info()
        return data.get("license", "AGPL v3")

    def get_author(self) -> str:
        data = self._load_app_info()
        return data.get("author", "NightOcean")

    def _fetch_remote_version_info(self, use_cache: bool = True) -> Optional[dict]:
        import time
        import urllib.request
        import urllib.error

        if use_cache and self._remote_data_cache:
            cache_time, cached_data = self._remote_data_cache
            if time.time() - cache_time < self.CHECK_CACHE_DURATION:
                return cached_data

        check_url = self.get_version_check_url()
        if not check_url:
            return None

        try:
            req = urllib.request.Request(check_url)
            req.add_header("User-Agent", "YHModsManager-Version-Checker")
            req.add_header("Cache-Control", "no-cache")

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

            self._remote_data_cache = (time.time(), data)
            return data

        except Exception as e:
            logger.error(f"Failed to fetch remote version info: {e}")
            return None

    def get_changelog_entries(self, limit: int = 5) -> List[ChangelogEntry]:
        remote_data = self._fetch_remote_version_info()
        if remote_data:
            entries = []
            for item in remote_data.get("changelog", [])[:limit]:
                entries.append(ChangelogEntry(
                    version=item.get("version", ""),
                    date=item.get("date", ""),
                    changes=item.get("changes", [])
                ))
            return entries
        return []

    def get_latest_changelog_entry(self) -> Optional[ChangelogEntry]:
        entries = self.get_changelog_entries(limit=1)
        return entries[0] if entries else None

    def get_changelog_url(self) -> Optional[str]:
        remote_data = self._fetch_remote_version_info()
        if remote_data:
            return remote_data.get("changelog_url", "")
        return None

    def check_for_updates(self, force: bool = False) -> Tuple[bool, Optional[UpdateInfo]]:
        import time
        import urllib.request
        import urllib.error

        if not force and self._check_cache:
            cache_time, cached_has_update, cached_info = self._check_cache
            if time.time() - cache_time < self.CHECK_CACHE_DURATION:
                logger.debug("Returning cached update check result")
                return cached_has_update, cached_info

        check_url = self.get_version_check_url()
        if not check_url:
            logger.warning("Version check URL not configured")
            return False, None

        try:
            req = urllib.request.Request(check_url)
            req.add_header("User-Agent", "YHModsManager-Update-Checker")
            req.add_header("Cache-Control", "no-cache")

            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

            self._remote_data_cache = (time.time(), data)

            latest_version = data.get("latest_version", "")
            current_version = self.get_current_version()

            if self._compare_versions(latest_version, current_version) > 0:
                current_platform = Platform.current().value
                platforms = data.get("platforms", {})
                platform_info = platforms.get(current_platform, {})

                download_url = platform_info.get("download_url", "")
                if download_url:
                    update_info = UpdateInfo(
                        version=latest_version,
                        release_date=data.get("release_date", ""),
                        release_notes=data.get("release_notes", ""),
                        download_url=download_url,
                        file_size=platform_info.get("file_size", 0),
                        file_name=platform_info.get("file_name", "")
                    )
                    self._check_cache = (time.time(), True, update_info)
                    return True, update_info
                else:
                    logger.warning(f"No download available for platform: {current_platform}")

            self._check_cache = (time.time(), False, None)
            return False, None

        except urllib.error.HTTPError as e:
            logger.error(f"HTTP error checking for updates: {e.code}")
            return False, None
        except urllib.error.URLError as e:
            logger.error(f"URL error checking for updates: {e.reason}")
            return False, None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON response: {e}")
            return False, None
        except Exception as e:
            logger.error(f"Error checking for updates: {e}")
            return False, None

    @staticmethod
    def _compare_versions(v1: str, v2: str) -> int:
        def parse_version(v):
            parts = v.split(".")
            result = []
            for part in parts:
                try:
                    result.append(int(part))
                except ValueError:
                    result.append(0)
            return result

        parts1 = parse_version(v1)
        parts2 = parse_version(v2)

        max_len = max(len(parts1), len(parts2))
        parts1.extend([0] * (max_len - len(parts1)))
        parts2.extend([0] * (max_len - len(parts2)))

        for p1, p2 in zip(parts1, parts2):
            if p1 > p2:
                return 1
            elif p1 < p2:
                return -1
        return 0

    @staticmethod
    def download_update(
            update_info: UpdateInfo,
            progress_callback: Callable[[int, int], None] = None
    ) -> Optional[str]:
        import urllib.request

        app_dir = get_app_data_dir()
        update_temp_dir = os.path.join(app_dir, ".update_temp")
        os.makedirs(update_temp_dir, exist_ok=True)
        download_path = os.path.join(update_temp_dir, update_info.file_name)

        try:
            req = urllib.request.Request(update_info.download_url)
            req.add_header("User-Agent", "YHModsManager-Update-Downloader")

            with urllib.request.urlopen(req, timeout=60) as response:
                total_size = int(response.headers.get("Content-Length", update_info.file_size))
                downloaded = 0
                chunk_size = 8192

                with open(download_path, "wb") as f:
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total_size)

            return download_path

        except Exception as e:
            logger.error(f"Failed to download update: {e}")
            if os.path.exists(update_temp_dir):
                shutil.rmtree(update_temp_dir)
            return None

    def install_update(self, download_path: str) -> Tuple[bool, str]:
        if not os.path.exists(download_path):
            return False, "Download file not found"

        app_dir = get_app_data_dir()
        extract_dir = os.path.join(app_dir, ".update_extract")

        try:
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            os.makedirs(extract_dir)

            with zipfile.ZipFile(download_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            items = os.listdir(extract_dir)
            if len(items) == 1 and os.path.isdir(os.path.join(extract_dir, items[0])):
                source_dir = os.path.join(extract_dir, items[0])
            else:
                source_dir = extract_dir

            new_exe = self._find_executable_in_dir(source_dir)
            if not new_exe:
                return False, "No executable found in update package"

            current_exe = self._get_current_exe_path()
            if not current_exe:
                return False, "Cannot determine current executable path"

            return self._prepare_update_for_platform(new_exe, current_exe, app_dir, extract_dir, download_path)

        except Exception as e:
            logger.error(f"Failed to prepare update: {e}")
            return False, str(e)

    @staticmethod
    def _find_executable_in_dir(source_dir: str) -> Optional[str]:
        platform_obj = Platform.current()

        for item in os.listdir(source_dir):
            item_path = os.path.join(source_dir, item)
            if platform_obj.is_windows():
                if item.endswith(".exe") and os.path.isfile(item_path):
                    return item_path
            elif platform_obj.is_macos():
                if item.endswith(".app") or (os.path.isfile(item_path) and os.access(item_path, os.X_OK)):
                    return item_path
            else:
                if os.path.isfile(item_path) and os.access(item_path, os.X_OK):
                    return item_path
        return None

    def _prepare_update_for_platform(self, new_exe: str, current_exe: str, app_dir: str, extract_dir: str, download_path: str) -> Tuple[bool, str]:
        platform_obj = Platform.current()

        if platform_obj.is_windows():
            return self._prepare_windows_update(new_exe, current_exe, app_dir, extract_dir, download_path)
        elif platform_obj.is_macos():
            return self._prepare_macos_update()
        else:
            return self._prepare_linux_update()

    def _prepare_windows_update(self, new_exe: str, current_exe: str, app_dir: str, extract_dir: str, download_path: str) -> Tuple[bool, str]:
        return True, "Update prepared. Restart required."

    @staticmethod
    def _prepare_macos_update() -> Tuple[bool, str]:
        return False, "macOS update not yet implemented"

    @staticmethod
    def _prepare_linux_update() -> Tuple[bool, str]:
        return False, "Linux update not yet implemented"

    @staticmethod
    def _get_current_exe_path() -> Optional[str]:
        import sys
        if getattr(sys, 'frozen', False):
            return sys.executable
        return None

    @staticmethod
    def _create_windows_update_script(new_exe: str, current_exe: str, app_dir: str, extract_dir: str, download_path: str) -> str:
        update_temp_dir = os.path.dirname(download_path)
        marker_file = os.path.join(app_dir, ".update_complete")

        bat_content = f'''@echo off
chcp 65001 >nul 2>&1
title 更新中

echo ========================================
echo           程序更新中...
echo ========================================
echo.

echo [1/2] 替换程序文件...
if exist "{current_exe}.bak" del /f /q "{current_exe}.bak" 2>nul
if exist "{current_exe}" move /y "{current_exe}" "{current_exe}.bak" >nul 2>&1
copy /y "{new_exe}" "{current_exe}" >nul 2>&1

rd /s /q "{extract_dir}" 2>nul
rd /s /q "{update_temp_dir}" 2>nul
del /f /q "{current_exe}.bak" 2>nul

echo completed > "{marker_file}"

echo.
echo ========================================
echo           更新完成！
echo ========================================

(goto) 2>nul & del /f /q "%~f0"
'''
        bat_path = os.path.join(app_dir, "update_helper.bat")
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)

        return bat_path

    @staticmethod
    def execute_update_restart():
        import subprocess

        platform_obj = Platform.current()
        app_dir = get_app_data_dir()

        if platform_obj.is_windows():
            bat_path = os.path.join(app_dir, "update_helper.bat")
            
            if os.path.exists(bat_path):
                subprocess.Popen(
                    ["cmd", "/c", bat_path],
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )

    @staticmethod
    def check_update_complete_marker() -> bool:
        app_dir = get_app_data_dir()
        marker_file = os.path.join(app_dir, ".update_complete")

        if os.path.exists(marker_file):
            try:
                with open(marker_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                os.remove(marker_file)
                return content == "completed"
            except Exception as e:
                logger.error(f"Failed to read update complete marker: {e}")
        return False

    @staticmethod
    def get_update_complete_marker_path() -> str:
        app_dir = get_app_data_dir()
        return os.path.join(app_dir, ".update_complete")

    @staticmethod
    def cleanup_temp_files():
        app_dir = get_app_data_dir()
        temp_dirs = [".update_backup", ".update_extract"]

        for dir_name in temp_dirs:
            dir_path = os.path.join(app_dir, dir_name)
            if os.path.exists(dir_path):
                try:
                    shutil.rmtree(dir_path)
                except Exception as e:
                    logger.warning(f"Failed to cleanup {dir_name}: {e}")


_update_service: Optional[UpdateService] = None


def get_update_service() -> UpdateService:
    global _update_service
    if _update_service is None:
        _update_service = UpdateService()
    return _update_service
