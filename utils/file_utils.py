import hashlib
import logging
import os
import shutil
import sys
from pathlib import Path
from typing import Optional

from send2trash import send2trash

logger = logging.getLogger(__name__)


def get_resource_path(relative_path: str) -> str:
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def get_app_data_dir() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ensure_app_directories() -> str:
    app_dir = get_app_data_dir()

    directories = [
        os.path.join(app_dir, "config"),
        os.path.join(app_dir, "config", "i18n"),
        os.path.join(app_dir, "config", "themes"),
        os.path.join(app_dir, "plugins"),
        os.path.join(app_dir, "plugins", "game"),
        os.path.join(app_dir, "plugins", "feature"),
        os.path.join(app_dir, "cache"),
        os.path.join(app_dir, "cache", "plugins_code"),
        os.path.join(app_dir, "logs"),
        os.path.join(app_dir, "logs", "crash"),
    ]

    for directory in directories:
        FileUtils.ensure_directory(directory)

    return app_dir


class FileUtils:
    @staticmethod
    def delete_file(filepath: str, use_trash: bool = True) -> bool:
        try:
            path = Path(filepath)
            if not path.exists():
                return True

            if use_trash:
                try:

                    send2trash(str(path))
                    logger.debug(f"Moved to trash: {filepath}")
                    return True
                except ImportError:
                    logger.debug("send2trash not available, using permanent delete")

            path.unlink()
            logger.debug(f"Deleted file: {filepath}")
            return True

        except (IOError, OSError) as e:
            logger.error(f"Failed to delete file {filepath}: {e}")
            return False

    @staticmethod
    def file_exists(filepath: str) -> bool:
        return Path(filepath).exists()

    @staticmethod
    def ensure_directory(dirpath: str) -> bool:
        try:
            Path(dirpath).mkdir(parents=True, exist_ok=True)
            return True
        except (IOError, OSError) as e:
            logger.error(f"Failed to create directory {dirpath}: {e}")
            return False

    @staticmethod
    def read_file(filepath: str, encoding: str = "utf-8") -> Optional[str]:
        try:
            with open(filepath, "r", encoding=encoding) as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read file {filepath}: {e}")
            return None

    @staticmethod
    def calculate_checksum(file_path: str) -> str:
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    @staticmethod
    def delete_path(path: str, use_trash: bool = True) -> bool:
        if not path or not os.path.exists(path):
            return False

        try:
            if use_trash:
                try:

                    send2trash(path)
                    return True
                except ImportError:
                    logger.debug("send2trash not available, using permanent delete")

            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)
            return True
        except (IOError, OSError) as e:
            logger.warning(f"Failed to delete path {path}: {e}")
        return False
