"""
对话框模块
"""

from .about_dialog import AboutDialog
from .game_settings_dialog import GameSettingsDialog
from .settings_dialog import SettingsDialog
from .update_dialog import ChangelogDialog, UpdateCheckDialog, UpdateNotificationDialog
from .validation_result_dialog import ValidationResultDialog

__all__ = [
    'GameSettingsDialog',
    'SettingsDialog',
    'ValidationResultDialog',
    'AboutDialog',
    'ChangelogDialog',
    'UpdateCheckDialog',
    'UpdateNotificationDialog',
]
