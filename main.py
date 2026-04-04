import os
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from core.config_manager import ConfigManager
from plugin_system.plugin_loader import get_plugin_loader
from yh_mods_manager_sdk import GameDetectorBase
from ui.draggable_list import DraggableListWidget
from ui.i18n import load_qt_translations
from ui.theme_manager import init_theme_manager, get_theme_manager
from ui.views.main_window import MainWindow
from utils.app_logger import init_app_logger, get_logger
from utils.crash_handler import init_crash_handler, get_crash_handler
from utils.file_utils import ensure_app_directories, get_resource_path
from utils.steam_detector import SteamDetector


def _init_sdk_extensions():
    """初始化SDK扩展，注入主程序实现"""
    GameDetectorBase.set_steam_detector(
        detect_func=SteamDetector.detect_steam_install_path,
        get_libraries_func=SteamDetector.get_steam_libraries
    )


def main():
    _init_sdk_extensions()

    app_dir = ensure_app_directories()

    init_app_logger("NightOcean's Mods Manager", app_dir)
    logger = get_logger(__name__)
    logger.info("Application starting...")

    crash_handler = init_crash_handler("NightOcean's Mods Manager", os.path.join(app_dir, "logs", "crash"))

    app = QApplication(sys.argv)

    if sys.platform == 'win32':
        icon_path = get_resource_path(os.path.join('icons', 'app_icon.ico'))
    else:
        icon_path = get_resource_path(os.path.join('icons', 'app_icon.png'))
    
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    saved_lang = ConfigManager.get_saved_language()
    load_qt_translations(app, saved_lang)

    user_config_dir = os.path.join(app_dir, "config")
    init_theme_manager(config_dir=user_config_dir)

    DraggableListWidget.set_game_mime_type("bannerlord")
    window = MainWindow()

    crash_handler.update_crash_info({
        "当前游戏": window.game_adapter.game_id if window.game_adapter else "None",
        "当前配置": window.current_profile_name,
    })

    theme_manager = get_theme_manager()
    theme_manager._config_manager = window.config_manager
    theme_manager.init_app_theme(app, window.config_manager, window.base_font_size)

    app.aboutToQuit.connect(cleanup_on_exit)

    if window.config_manager.is_window_maximized():
        window.showMaximized()
    else:
        window.show()

    sys.exit(app.exec())


def cleanup_on_exit():
    logger = get_logger(__name__)
    logger.info("Application shutting down...")

    crash_handler = get_crash_handler()
    crash_handler.mark_normal_exit()

    plugin_loader = get_plugin_loader()
    plugin_loader.cleanup()
    logger.info("Application shutdown complete")


if __name__ == "__main__":
    main()
