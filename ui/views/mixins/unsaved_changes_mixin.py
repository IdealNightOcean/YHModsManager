from typing import List

from PyQt6.QtWidgets import QMessageBox

from ui.i18n import tr


class UnsavedChangesMixin:
    _has_unsaved_changes: bool
    _saved_enabled_order: List[str]

    def _mark_saved(self):
        self._has_unsaved_changes = False
        self._saved_enabled_order = list(self.mod_service.enabled_mod_order)

    def _mark_unsaved(self):
        if not self._has_unsaved_changes:
            self._has_unsaved_changes = True

    def _check_unsaved_changes(self) -> bool:
        if not self._has_unsaved_changes:
            return True
        if self._saved_enabled_order == list(self.mod_service.enabled_mod_order):
            return True
        return False

    def _prompt_unsaved_changes(self, title_key: str, message_key: str, save_btn_key: str = "save") -> bool:
        if self._check_unsaved_changes():
            return True
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(tr(title_key))
        msg_box.setText(tr(message_key))
        msg_box.setIcon(QMessageBox.Icon.Warning)
        save_btn = msg_box.addButton(tr(save_btn_key), QMessageBox.ButtonRole.AcceptRole)
        discard_btn = msg_box.addButton(tr("discard_changes"), QMessageBox.ButtonRole.DestructiveRole)
        msg_box.exec()
        clicked_btn = msg_box.clickedButton()
        if clicked_btn == save_btn:
            self._save_current_profile()
            return True
        elif clicked_btn == discard_btn:
            return True
        return False

    def _prompt_unsaved_changes_for_switch(self) -> bool:
        return self._prompt_unsaved_changes(
            "unsaved_changes_title",
            "unsaved_changes_message",
            "save_and_continue"
        )

    def _prompt_unsaved_changes_for_exit(self) -> bool:
        return self._prompt_unsaved_changes(
            "confirm_exit",
            "confirm_exit_unsaved",
            "save"
        )

    def closeEvent(self, event):
        if not self._prompt_unsaved_changes_for_exit():
            event.ignore()
            return
        if not self.isMaximized():
            self.config_manager.set_window_size(self.width(), self.height())
        self.config_manager.set_window_maximized(self.isMaximized())

        if self.game_adapter:
            self.config_manager.save_current_state(
                game_id=self.game_adapter.game_id,
                profile_name=self.current_profile_name
            )
        self.mod_manager.save_metadata()
        event.accept()
