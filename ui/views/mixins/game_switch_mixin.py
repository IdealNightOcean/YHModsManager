import logging

from PyQt6.QtWidgets import QMessageBox

from core.event_bus import get_event_bus
from plugin_system import get_plugin_loader
from ui.i18n import tr
from ui.toast_widget import ToastManager

logger = logging.getLogger(__name__)


class GameSwitchMixin:
    def _switch_game(self, game_id: str):
        current_game_id = ""
        current_game_name = ""
        if self.game_adapter:
            current_game_id = self.game_adapter.game_id
            game_info = self.game_adapter.get_game_info()
            current_game_name = self.config_manager.get_game_display_name(current_game_id,
                                                                          game_info.default_name if game_info else current_game_id)

        if game_id == current_game_id:
            return

        if not self._prompt_unsaved_changes_for_switch():
            return

        loader = get_plugin_loader()
        target_adapter = loader.get_adapter(game_id)
        target_game_name = game_id
        if target_adapter:
            game_info = target_adapter.get_game_info()
            target_game_name = self.config_manager.get_game_display_name(game_id,
                                                                         game_info.default_name if game_info else game_id)

        reply = QMessageBox.question(
            self,
            tr("switch_game"),
            tr("confirm_switch_game").format(current_game_name, target_game_name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        if self.game_adapter:
            self.mod_manager.save_metadata()
            self.config_manager.save_current_state(
                game_id=self.game_adapter.game_id,
                profile_name=self.current_profile_name
            )

        if loader.set_current_plugin(game_id):
            self.game_adapter = loader.get_current_adapter()
            self.config_manager.set_game_adapter(self.game_adapter)

            self._game_metadata_manager.set_current_game(game_id)
            self._mod_metadata_manager.set_current_game(game_id)

            self._clear_mod_lists()
            self._refresh_game_menu()
            self._refresh_plugin_menu()
            self._refresh_profile_combo()
            self._update_window_title()
            self._update_game_info_label()
            self._update_save_import_action()

            self._mod_update_view.set_current_game(game_id)

            event_bus = get_event_bus()
            event_bus.emit_game_changed(game_id, source="main_window")

            self._load_game_settings()

            game_info = self.game_adapter.get_game_info()
            display_name = game_info.default_name if game_info else game_id
            ToastManager.show(tr("game_switched").format(display_name))
        else:
            ToastManager.show(tr("game_switch_failed"))

    def _load_game_settings(self):
        paths = self.config_manager.get_game_dir_paths_with_detection()

        if paths.game_dir_path:
            from core.mod_parser import create_mod_parser
            self.parser = create_mod_parser(
                self.game_adapter, paths,
                i18n=self.i18n
            )
            self._scan_mods()
        else:
            self._select_game_dir_path()

    def _update_window_title(self):
        game_name = self.config_manager.get_display_game_name() if self.config_manager else ""
        if not game_name and self.game_adapter:
            game_info = self.game_adapter.get_game_info()
            game_name = game_info.default_name if game_info else ""
        if game_name:
            self.setWindowTitle(f"{game_name} - {tr('app_name')}")
        else:
            self.setWindowTitle(tr("app_name"))
