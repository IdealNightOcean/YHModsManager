import logging
import os

from PyQt6.QtWidgets import QFileDialog, QMessageBox

from core.manager_collection import get_manager_collection
from yh_mods_manager_sdk import ModProfile
from ui.i18n import tr
from ui.toast_widget import ToastManager

logger = logging.getLogger(__name__)


class SaveImportMixin:
    def _update_save_import_action(self):
        has_parser = bool(self.game_adapter and self.game_adapter.get_save_parser_capabilities())
        self.import_from_save_action.setEnabled(has_parser)

        if has_parser:
            self.import_from_save_action.setToolTip("")
        else:
            self.import_from_save_action.setToolTip(tr("no_save_parser_tooltip"))

    def _import_from_save(self):
        if not self.game_adapter or not self.game_adapter.get_save_parser_capabilities():
            QMessageBox.warning(self, tr("error_title"), tr("no_save_parser_tooltip"))
            return

        save_filter = self.game_adapter.get_save_file_filter()
        default_save_dir_path = self.config_manager.get_default_save_dir_path() if self.config_manager else ""
        save_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("select_save_file"),
            default_save_dir_path,
            save_filter
        )

        if not save_path:
            return

        manager_collection = get_manager_collection()

        parse_result = self.game_adapter.parse_save_file(save_path, manager_collection)

        if not parse_result.success:
            QMessageBox.warning(self, tr("error_title"), parse_result.error_message or tr("save_parse_failed"))
            return

        if not parse_result.mod_order:
            QMessageBox.information(self, tr("info"), tr("save_no_mods"))
            return

        temp_profile = self.game_adapter.create_save_import_profile(parse_result, manager_collection)

        self._show_save_import_dialog(temp_profile, save_path)

    def _show_save_import_dialog(self, temp_profile: ModProfile, save_path: str):
        base_name = os.path.splitext(os.path.basename(save_path))[0]

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle(tr("import_from_save"))
        msg_box.setIcon(QMessageBox.Icon.Question)

        mod_count = len(temp_profile.mod_order)
        msg_box.setText(tr("save_import_options").format(mod_count, base_name))

        btn_create_new = msg_box.addButton(tr("create_new_profile"), QMessageBox.ButtonRole.ActionRole)
        btn_overwrite = msg_box.addButton(tr("overwrite_current"), QMessageBox.ButtonRole.ActionRole)

        msg_box.exec()

        clicked = msg_box.clickedButton()

        if clicked == btn_create_new:
            self._create_profile_from_save_import(temp_profile, base_name)
        elif clicked == btn_overwrite:
            self._apply_save_import_to_current_profile(temp_profile)

    def _create_profile_from_save_import(self, temp_profile: ModProfile, base_name: str):
        profile_name = base_name
        counter = 1

        while profile_name in self.config_manager.profiles:
            profile_name = f"{base_name}_{counter}"
            counter += 1

        missing_mods = self._check_missing_mods(temp_profile.mod_order)

        if missing_mods:
            from ui.widgets.missing_mods_dialog import MissingModsDialog
            if not MissingModsDialog.check_and_show(missing_mods, profile_name, self.base_font_size, self):
                return

        if not self._prompt_unsaved_changes_for_switch():
            return

        if self.parser:
            temp_profile.game_version = self.parser.game_version

        self.config_manager.profiles[profile_name] = temp_profile
        self.config_manager.save_profile(profile_name, temp_profile, self.mod_service.get_mod_by_id)

        self._refresh_profiles(profile_name)
        self._on_profile_changed(profile_name, skip_unsaved_check=True)
        self.status_bar.showMessage(tr("save_import_created").format(profile_name))

    def _apply_save_import_to_current_profile(self, temp_profile: ModProfile):
        if not self.current_profile:
            ToastManager.show(tr("no_profile_selected"))
            return

        missing_mods = self._check_missing_mods(temp_profile.mod_order)

        if missing_mods:
            from ui.widgets.missing_mods_dialog import MissingModsDialog
            if not MissingModsDialog.check_and_show(missing_mods, self.current_profile_name, self.base_font_size, self):
                return

        self._apply_profile_mod_order(temp_profile.mod_order)
        self._save_current_profile()
        self.status_bar.showMessage(tr("save_import_applied").format(self.current_profile_name))

    def _check_missing_mods(self, mod_order: list) -> list:
        missing_mods = []
        valid_ids = {mod.id for mod in self.mod_service.all_mods}

        for mod_id in mod_order:
            if mod_id not in valid_ids:
                mod = self.mod_service.get_mod_by_id(mod_id)
                display_name = mod.name if mod else mod_id
                missing_mods.append({
                    "id": mod_id,
                    "display_name": display_name
                })

        return missing_mods

    def _apply_profile_mod_order(self, mod_order: list):
        self.mod_service.disable_all_mods()

        for mod_id in mod_order:
            mod = self.mod_service.get_mod_by_id(mod_id)
            if mod:
                self.mod_service.enable_mod(mod_id)

        self._refresh_enabled_list()
        self._refresh_disabled_list()
        self._update_status()
        self._selection_manager.clear_selection()
        self.info_panel.set_current_mod(None)
        self._update_dependency_lines()
        self._auto_validate_load_order()
