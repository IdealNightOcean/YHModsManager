"""
应用日志系统模块
提供统一的日志记录功能，支持行为日志和错误日志
与崩溃日志处理器协同工作
"""

import json
import logging
import sys
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Optional, Dict, Any

LOG_CONFIG_FILENAME = "log_config.json"

DEFAULT_LOG_CONFIG = {
    "console_enabled": True,
    "file_enabled": True,
    "level": "INFO",
    "max_days": 30,
    "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    "date_format": "%Y-%m-%d %H:%M:%S"
}


class AppLogger:
    """应用日志管理器
    
    功能：
    1. 统一的日志记录接口
    2. 支持控制台和文件双输出
    3. 按日期自动分割日志文件
    4. 可配置的日志级别
    5. 自动清理过期日志
    """

    LOG_DIR = "logs"
    LOG_FILENAME = "app.log"

    _instance: Optional["AppLogger"] = None
    _initialized: bool = False

    def __init__(self, app_name: str = "App", app_dir: Optional[str] = None):
        self.app_name = app_name
        self._app_dir = app_dir
        self._config: Dict[str, Any] = {}
        self._log_dir: Optional[Path] = None
        self._root_logger: Optional[logging.Logger] = None
        self._file_handler: Optional[logging.Handler] = None
        self._console_handler: Optional[logging.Handler] = None

    @property
    def log_dir(self) -> Path:
        if self._log_dir:
            return self._log_dir
        if self._app_dir:
            return Path(self._app_dir) / self.LOG_DIR
        return Path(self.LOG_DIR)

    def set_log_dir(self, log_dir: str):
        self._log_dir = Path(log_dir)

    def _load_config(self) -> Dict[str, Any]:
        config_path = self._get_config_path()
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                    return {**DEFAULT_LOG_CONFIG, **user_config}
            except Exception:
                pass
        return DEFAULT_LOG_CONFIG.copy()

    def _get_config_path(self) -> Path:
        if self._app_dir:
            return Path(self._app_dir) / "config" / LOG_CONFIG_FILENAME
        return Path("config") / LOG_CONFIG_FILENAME

    def init(self, config_dir: Optional[str] = None):
        if self._initialized:
            return

        if config_dir:
            self._app_dir = config_dir

        self._config = self._load_config()

        self._setup_logger()
        self._initialized = True

    def _setup_logger(self):
        self._root_logger = logging.getLogger()
        self._root_logger.setLevel(self._get_log_level())

        self._clear_existing_handlers()

        log_format = self._config.get("format", DEFAULT_LOG_CONFIG["format"])
        date_format = self._config.get("date_format", DEFAULT_LOG_CONFIG["date_format"])
        formatter = logging.Formatter(log_format, datefmt=date_format)

        if self._config.get("file_enabled", True):
            self._setup_file_handler(formatter)

        if self._config.get("console_enabled", True):
            self._setup_console_handler(formatter)

        logging.getLogger(__name__).debug("App logger initialized")

    def _get_log_level(self) -> int:
        level_str = self._config.get("level", "INFO").upper()
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        return level_map.get(level_str, logging.INFO)

    def _clear_existing_handlers(self):
        for handler in self._root_logger.handlers[:]:
            self._root_logger.removeHandler(handler)

    def _setup_file_handler(self, formatter: logging.Formatter):
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)

            log_file = self.log_dir / self.LOG_FILENAME

            self._file_handler = TimedRotatingFileHandler(
                log_file,
                when="midnight",
                interval=1,
                backupCount=self._config.get("max_days", 30),
                encoding="utf-8"
            )
            self._file_handler.setFormatter(formatter)
            self._file_handler.setLevel(self._get_log_level())
            self._root_logger.addHandler(self._file_handler)

        except Exception as e:
            print(f"Failed to setup file handler: {e}", file=sys.stderr)

    def _setup_console_handler(self, formatter: logging.Formatter):
        self._console_handler = logging.StreamHandler(sys.stdout)
        self._console_handler.setFormatter(formatter)
        self._console_handler.setLevel(self._get_log_level())
        self._root_logger.addHandler(self._console_handler)

    def set_level(self, level: str):
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        new_level = level_map.get(level.upper(), logging.INFO)

        self._root_logger.setLevel(new_level)
        if self._file_handler:
            self._file_handler.setLevel(new_level)
        if self._console_handler:
            self._console_handler.setLevel(new_level)

        self._config["level"] = level.upper()

    def enable_console(self, enabled: bool = True):
        if self._console_handler:
            if enabled:
                if self._console_handler not in self._root_logger.handlers:
                    self._root_logger.addHandler(self._console_handler)
            else:
                if self._console_handler in self._root_logger.handlers:
                    self._root_logger.removeHandler(self._console_handler)

    def enable_file(self, enabled: bool = True):
        if self._file_handler:
            if enabled:
                if self._file_handler not in self._root_logger.handlers:
                    self._root_logger.addHandler(self._file_handler)
            else:
                if self._file_handler in self._root_logger.handlers:
                    self._root_logger.removeHandler(self._file_handler)

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        return logging.getLogger(name)

    def cleanup_old_logs(self) -> int:
        removed_count = 0
        try:
            max_days = self._config.get("max_days", 30)
            cutoff_time = datetime.now().timestamp() - (max_days * 24 * 60 * 60)

            for log_file in self.log_dir.glob("*.log*"):
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    removed_count += 1

        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to cleanup old logs: {e}")

        return removed_count

    def get_log_files(self) -> list:
        if not self.log_dir.exists():
            return []

        return sorted(
            self.log_dir.glob("*.log*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

    @staticmethod
    def read_log_file(filepath: str) -> Optional[str]:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to read log file {filepath}: {e}")
            return None

    def clear_all_logs(self) -> bool:
        try:
            for log_file in self.get_log_files():
                log_file.unlink()
            logging.getLogger(__name__).info("All logs cleared")
            return True
        except Exception as e:
            logging.getLogger(__name__).error(f"Failed to clear logs: {e}")
            return False


_app_logger: Optional[AppLogger] = None


def get_app_logger() -> AppLogger:
    global _app_logger
    if _app_logger is None:
        _app_logger = AppLogger()
    return _app_logger


def init_app_logger(app_name: str = "App", app_dir: Optional[str] = None) -> AppLogger:
    global _app_logger
    _app_logger = AppLogger(app_name, app_dir)
    _app_logger.init(app_dir)
    return _app_logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
