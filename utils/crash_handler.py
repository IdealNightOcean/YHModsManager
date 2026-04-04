"""
崩溃日志处理器模块
只在程序真正崩溃（非正常退出）时保存崩溃日志
普通错误应通过 logger.error() 记录到普通日志
"""

import atexit
import logging
import os
import platform
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable, List, Dict, Any

logger = logging.getLogger(__name__)


class CrashHandler:
    """崩溃日志处理器
    
    功能：
    1. 只在程序非正常退出时保存崩溃日志
    2. 捕获未处理的致命异常
    3. 记录详细的崩溃信息到日志文件
    4. 提供日志清理功能
    
    设计原则：
    - 崩溃日志只记录导致程序终止的致命错误
    - 普通错误应通过 logger.error() 记录到普通日志
    - 使用 atexit 检测程序是否正常退出
    """

    CRASH_LOG_SUBDIR = "crash"
    MAX_LOG_FILES = 10
    MAX_LOG_SIZE_MB = 5

    def __init__(self, app_name: str = "App", log_dir: Optional[str] = None):
        self.app_name = app_name
        self._log_dir = log_dir
        self._original_excepthook = None
        self._crash_callbacks: List[Callable] = []
        self._is_installed = False
        self._crash_info: Dict[str, Any] = {}
        self._is_normal_exit = False
        self._pending_exception: Optional[tuple] = None

    @property
    def log_dir(self) -> Path:
        if self._log_dir:
            return Path(self._log_dir)
        return Path("logs") / self.CRASH_LOG_SUBDIR

    def set_log_dir(self, log_dir: str):
        self._log_dir = log_dir

    def set_crash_info(self, key: str, value: Any):
        self._crash_info[key] = value

    def update_crash_info(self, info: Dict[str, Any]):
        self._crash_info.update(info)

    def add_crash_callback(self, callback: Callable):
        self._crash_callbacks.append(callback)

    def install(self):
        if self._is_installed:
            return

        self._original_excepthook = sys.excepthook
        sys.excepthook = self._handle_exception

        atexit.register(self._save_crash_log_on_exit)

        self._is_installed = True
        logger.debug("Crash handler installed")

    def uninstall(self):
        if not self._is_installed:
            return

        if self._original_excepthook:
            sys.excepthook = self._original_excepthook

        atexit.unregister(self._save_crash_log_on_exit)

        self._is_installed = False
        logger.debug("Crash handler uninstalled")

    def mark_normal_exit(self):
        self._is_normal_exit = True

    def _handle_exception(self, exc_type, exc_value, exc_traceback):
        if exc_traceback is None:
            if self._original_excepthook:
                self._original_excepthook(exc_type, exc_value, exc_traceback)
            return

        self._pending_exception = (exc_type, exc_value, exc_traceback)

        logger.error(
            f"Uncaught exception: {exc_type.__name__}: {exc_value}\n"
            + "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        )

        for callback in self._crash_callbacks:
            try:
                callback(exc_type, exc_value, exc_traceback)
            except Exception as e:
                logger.error(f"Crash callback failed: {e}")

        if self._original_excepthook:
            self._original_excepthook(exc_type, exc_value, exc_traceback)

    def _save_crash_log_on_exit(self):
        if self._is_normal_exit:
            return

        if self._pending_exception is None:
            return

        exc_type, exc_value, exc_traceback = self._pending_exception
        self._save_crash_log(exc_type, exc_value, exc_traceback)

    def _save_crash_log(self, exc_type, exc_value, exc_traceback) -> Optional[str]:
        try:
            self._ensure_log_dir()

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"crash_{timestamp}.log"
            filepath = self.log_dir / filename

            crash_content = self._format_crash_log(exc_type, exc_value, exc_traceback)

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(crash_content)

            logger.info(f"Crash log saved to: {filepath}")

            self._cleanup_old_logs()

            return str(filepath)

        except Exception as e:
            logger.error(f"Failed to save crash log: {e}")
            return None

    def _format_crash_log(self, exc_type, exc_value, exc_traceback) -> str:
        lines = ["=" * 60, f"崩溃日志 - {self.app_name}", "=" * 60, "",
                 f"崩溃时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "", "-" * 40, "系统信息", "-" * 40,
                 f"操作系统: {platform.system()} {platform.release()}", f"Python 版本: {platform.python_version()}",
                 f"Python 实现: {platform.python_implementation()}", f"架构: {platform.machine()}",
                 f"处理器: {platform.processor() or 'Unknown'}", "", "-" * 40, "异常信息", "-" * 40,
                 f"异常类型: {exc_type.__name__}", f"异常消息: {str(exc_value)}", "", "-" * 40, "堆栈跟踪", "-" * 40]

        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        lines.extend(tb_lines)
        lines.append("")

        if self._crash_info:
            lines.append("-" * 40)
            lines.append("应用状态信息")
            lines.append("-" * 40)
            for key, value in self._crash_info.items():
                lines.append(f"{key}: {value}")
            lines.append("")

        lines.append("-" * 40)
        lines.append("环境变量")
        lines.append("-" * 40)
        for key in ['PATH', 'PYTHONPATH', 'PYTHONHOME', 'APPDATA', 'LOCALAPPDATA', 'HOME']:
            value = os.environ.get(key, '(未设置)')
            if len(value) > 200:
                value = value[:200] + '...'
            lines.append(f"{key}: {value}")
        lines.append("")

        lines.append("=" * 60)
        lines.append("日志结束")
        lines.append("=" * 60)

        return "\n".join(lines)

    def _ensure_log_dir(self):
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _cleanup_old_logs(self):
        try:
            log_files = sorted(
                self.log_dir.glob("crash_*.log"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            while len(log_files) > self.MAX_LOG_FILES:
                old_file = log_files.pop()
                old_file.unlink()
                logger.debug(f"Removed old crash log: {old_file}")

            for log_file in log_files[:self.MAX_LOG_FILES]:
                size_mb = log_file.stat().st_size / (1024 * 1024)
                if size_mb > self.MAX_LOG_SIZE_MB:
                    log_file.unlink()
                    logger.debug(f"Removed oversized crash log: {log_file}")

        except Exception as e:
            logger.error(f"Failed to cleanup old logs: {e}")

    def get_crash_logs(self) -> List[Path]:
        if not self.log_dir.exists():
            return []

        return sorted(
            self.log_dir.glob("crash_*.log"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

    def get_latest_crash_log(self) -> Optional[Path]:
        logs = self.get_crash_logs()
        return logs[0] if logs else None

    @staticmethod
    def read_crash_log(filepath: str) -> Optional[str]:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read crash log {filepath}: {e}")
            return None

    def clear_all_logs(self) -> bool:
        try:
            for log_file in self.get_crash_logs():
                log_file.unlink()
            logger.info("All crash logs cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear crash logs: {e}")
            return False


_crash_handler: Optional[CrashHandler] = None


def get_crash_handler(app_name: str = "App", log_dir: Optional[str] = None) -> CrashHandler:
    global _crash_handler
    if _crash_handler is None:
        _crash_handler = CrashHandler(app_name, log_dir)
    return _crash_handler


def init_crash_handler(app_name: str = "App", log_dir: Optional[str] = None) -> CrashHandler:
    global _crash_handler
    _crash_handler = CrashHandler(app_name, log_dir)
    _crash_handler.install()
    return _crash_handler
