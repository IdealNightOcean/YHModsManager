import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QToolBar, QWidget, QSizePolicy, QPushButton, QLabel

from core.manager_collection import get_manager_collection
from ui.i18n import tr
from ui.styles import FontSize, get_calculated_font_size
from ui.widgets import ProfileBar

logger = logging.getLogger(__name__)


class ToolBarMixin:
    def _create_tool_bar(self):
        toolbar = QToolBar(tr("toolbar_main"))
        self.addToolBar(toolbar)

        self.scan_btn = QPushButton(tr("refresh_mods"))
        self.scan_btn.clicked.connect(self._scan_mods)
        self.scan_btn.setProperty("buttonType", "standard")
        toolbar.addWidget(self.scan_btn)
        toolbar.addSeparator()

        self.simple_sort_btn = QPushButton(tr("simple_sort"))
        self.simple_sort_btn.clicked.connect(self._simple_sort)
        self.simple_sort_btn.setProperty("buttonType", "standard")
        toolbar.addWidget(self.simple_sort_btn)

        self.check_issues_btn = QPushButton(tr("check_issues"))
        self.check_issues_btn.clicked.connect(self._check_issues)
        self.check_issues_btn.setProperty("buttonType", "standard")
        toolbar.addWidget(self.check_issues_btn)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer)

        self.game_info_label = QLabel()
        self.game_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.game_info_label.setProperty("labelType", "game_info")
        font = self.game_info_label.font()
        font.setPointSize(get_calculated_font_size(self.base_font_size, FontSize.MEDIUM))
        font.setBold(True)
        self.game_info_label.setFont(font)
        toolbar.addWidget(self.game_info_label)

        spacer2 = QWidget()
        spacer2.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        toolbar.addWidget(spacer2)

        self.launch_native_btn = QPushButton(tr("launch_game_native"))
        self.launch_native_btn.clicked.connect(self._launch_game_native)
        self.launch_native_btn.setProperty("buttonType", "standard")
        toolbar.addWidget(self.launch_native_btn)

        self.launch_steam_btn = QPushButton(tr("launch_game_steam"))
        self.launch_steam_btn.clicked.connect(self._launch_game_steam)
        self.launch_steam_btn.setProperty("buttonType", "standard")
        toolbar.addWidget(self.launch_steam_btn)

        toolbar.addSeparator()

        self._switch_view_btn = QPushButton(tr("switch_to_update_view"))
        self._switch_view_btn.clicked.connect(self._toggle_view)
        self._switch_view_btn.setProperty("buttonType", "standard")
        toolbar.addWidget(self._switch_view_btn)

        margin_spacer = QWidget()
        margin_spacer.setFixedWidth(8)
        toolbar.addWidget(margin_spacer)

        self._update_game_info_label()

    def _update_game_info_label(self):
        if not self.game_adapter:
            self.game_info_label.setText("")
            return

        game_name = self.config_manager.get_display_game_name() if self.config_manager else ""
        if not game_name:
            game_info = self.game_adapter.get_game_info()
            game_name = game_info.default_name if game_info else self.game_adapter.game_id
        game_version = self.parser.game_version if self.parser else ""

        if game_version:
            if not game_version.startswith("v") and not game_version.startswith("V"):
                game_version = f"v{game_version}"
            self.game_info_label.setText(f"{game_name}  |  {game_version}")
        else:
            self.game_info_label.setText(game_name)

    def _toggle_view(self):
        if self._view_switcher.currentWidget() == self._main_view:
            self._view_switcher.setCurrentWidget(self._mod_update_view)
            self._switch_view_btn.setText(tr("switch_to_main_view"))
            self._mod_update_view.load_data()
        else:
            self._view_switcher.setCurrentWidget(self._main_view)
            self._switch_view_btn.setText(tr("switch_to_update_view"))

    def _create_profile_bar(self) -> ProfileBar:
        self.profile_bar = ProfileBar(self.base_font_size)
        self.profile_bar.profile_changed.connect(self._on_profile_changed)
        self.profile_bar.new_profile_clicked.connect(self._create_new_profile)
        self.profile_bar.save_profile_clicked.connect(self._save_current_profile)
        self.profile_bar.rename_profile_clicked.connect(self._rename_current_profile)
        self.profile_bar.delete_profile_clicked.connect(self._delete_current_profile)
        return self.profile_bar

    def _refresh_toolbar_button_styles(self):
        for btn in [self.scan_btn, self.simple_sort_btn, self.check_issues_btn, self.launch_native_btn,
                    self.launch_steam_btn]:
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _launch_game_native(self):
        from PyQt6.QtWidgets import QMessageBox

        game_dir_path = self.config_manager.get_game_dir_path()
        if not game_dir_path:
            QMessageBox.warning(self, tr("error_title"), tr("msg_no_game_dir_path"))
            return

        self._save_current_profile()

        manager_collection = get_manager_collection()
        success, error_msg = self.game_adapter.prepare_for_launch(manager_collection)
        if success:
            logger.info(f"prepare_for_launch: {success}, {error_msg}")
        else:
            logger.warning(f"prepare_for_launch: {success}, {error_msg}")
            QMessageBox.warning(self, tr("error_title"), error_msg if error_msg else tr("launch_prepare_failed"))
            return

        success, error_msg = self.game_adapter.launch_game_native(manager_collection)

        if success:
            logger.info(f"launch_game_native: {success}, {error_msg}")
        else:
            logger.warning(f"launch_game_native: {success}, {error_msg}")
            QMessageBox.warning(self, tr("error_title"), error_msg if error_msg else tr("game_exe_not_found"))

    def _launch_game_steam(self):
        from PyQt6.QtWidgets import QMessageBox

        self._save_current_profile()

        manager_collection = get_manager_collection()
        success, error_msg = self.game_adapter.prepare_for_launch(manager_collection)

        if success:
            logger.info(f"prepare_for_launch: {success}, {error_msg}")
        else:
            logger.warning(f"prepare_for_launch: {success}, {error_msg}")
            QMessageBox.warning(self, tr("error_title"), error_msg if error_msg else tr("launch_prepare_failed"))
            return

        success, error_msg = self.game_adapter.launch_game_steam(manager_collection)

        if success:
            logger.info(f"launch_game_steam: {success}, {error_msg}")
        else:
            logger.warning(f"launch_game_steam: {success}, {error_msg}")
            QMessageBox.warning(self, tr("error_title"), error_msg if error_msg else tr("steam_launch_failed"))

    def _show_settings_dialog(self):
        from ui.dialogs.settings_dialog import SettingsDialog
        dialog = SettingsDialog(self, self.config_manager)
        dialog.config_changed.connect(self._on_settings_config_changed)

        dialog.network_settings_tab.settings_changed.connect(self._on_network_settings_changed)

        dialog.exec()
        self.info_panel.refresh_theme()

    def _on_settings_config_changed(self):
        self.info_panel.refresh_theme()

    def _on_network_settings_changed(self):
        steam_disabled = self.config_manager.is_steam_monitor_disabled()
        self._mod_update_view.on_steam_monitor_setting_changed(steam_disabled)
