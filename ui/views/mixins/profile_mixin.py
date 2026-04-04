import json
import logging
import os
from typing import Optional

from PyQt6.QtWidgets import QFileDialog, QMessageBox, QInputDialog

from yh_mods_manager_sdk import ModProfile
from ui.i18n import tr
from utils.profile_serializer import ProfileSerializer

logger = logging.getLogger(__name__)


class ProfileMixin:
    current_profile: Optional[ModProfile]
    current_profile_name: str

    def _create_new_profile(self):
        if not self._prompt_unsaved_changes_for_switch():
            return
        name, ok = QInputDialog.getText(self, tr("new_profile"), tr("profile_name"))
        if ok and name:
            if self.config_manager.get_profile(name):
                QMessageBox.warning(self, tr("error_title"), tr("profile_exists"))
                return
            profile = self.mod_manager.create_profile(name)
            if profile:
                self.current_profile_name = name
                self._refresh_profiles(name)
                self._on_profile_changed(name, skip_unsaved_check=True)

    def _save_current_profile(self):
        if not self.current_profile:
            name, ok = QInputDialog.getText(self, tr("save_profile"), tr("profile_name"))
            if ok and name:
                if self.config_manager.get_profile(name):
                    reply = QMessageBox.question(self, tr("overwrite"), tr("overwrite_profile").format(name),
                                                 QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    if reply != QMessageBox.StandardButton.Yes:
                        return
                self.mod_manager.create_profile(name)
                self.current_profile_name = name
                self._refresh_profiles(name)
                self.current_profile = self.config_manager.get_profile(name)
                self._on_profile_changed(name, skip_unsaved_check=True)
        else:
            self.mod_service.save_to_profile(self.current_profile_name, self.current_profile)
            self._refresh_profiles(self.current_profile_name)
            self.status_bar.showMessage(tr("profile_saved"))
        self._mark_saved()

    def _delete_current_profile(self):
        if not self.current_profile:
            return
        if not self._check_unsaved_changes():
            reply = QMessageBox.question(
                self,
                tr("delete_profile"),
                tr("unsaved_changes_message") + "\n\n" + tr("confirm_delete_profile").format(self.current_profile_name),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        else:
            reply = QMessageBox.question(self, tr("delete_profile"),
                                         tr("confirm_delete_profile").format(self.current_profile_name),
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
        success, next_profile_name = self.config_manager.delete_profile(self.current_profile_name)
        if success:
            self.current_profile = None
            self.current_profile_name = ""
            if next_profile_name:
                self._refresh_profiles(next_profile_name)
                self._on_profile_changed(next_profile_name, skip_unsaved_check=True)
            else:
                self._refresh_profiles()
                self._update_status()

    def _rename_current_profile(self):
        if not self.current_profile:
            return
        old_name = self.current_profile_name
        new_name, ok = QInputDialog.getText(self, tr("rename"), tr("profile_name"), text=old_name)
        if ok and new_name and new_name != old_name:
            if self.config_manager.get_profile(new_name):
                QMessageBox.warning(self, tr("error_title"), tr("profile_exists"))
                return
            if self.config_manager.rename_profile(old_name, new_name):
                self.current_profile = self.config_manager.get_profile(new_name)
                self.current_profile_name = new_name
                self._refresh_profiles(new_name)
                self.status_bar.showMessage(tr("profile_renamed").format(old_name, new_name))

    def _on_profile_changed(self, profile_name: str, skip_unsaved_check: bool = False):
        if not skip_unsaved_check:
            if not self._prompt_unsaved_changes_for_switch():
                self.profile_bar.set_current_profile(self.current_profile_name)
                return
        profile = self.config_manager.get_profile(profile_name)
        if not profile:
            return

        self.current_profile = profile
        self.current_profile_name = profile_name
        self.config_manager.set_last_profile(profile_name)

        self.mod_service.load_profile(profile)

        self._selection_manager.clear_selection()
        self.enabled_list.clearSelection()
        self.disabled_list.clearSelection()

        self._refresh_enabled_list()
        self._refresh_disabled_list()
        self._update_all_enabled_mods_status()
        self._auto_validate_load_order()
        self._update_status()
        self._invalidate_dependency_cache()
        self._update_dependency_lines()
        self._mark_saved()

    def _export_profile(self):
        if not self.current_profile:
            QMessageBox.warning(self, tr("error_title"), tr("no_profile_selected"))
            return
        default_filename = f"{self.current_profile_name}.json"
        file_path, _ = QFileDialog.getSaveFileName(self, tr("export_profile"), default_filename, "JSON Files (*.json)")
        if file_path:
            self._save_current_profile()
            self.mod_manager.export_profile(self.current_profile_name, file_path)
            self.status_bar.showMessage(tr("profile_exported"))

    def _import_profile(self):
        file_path, _ = QFileDialog.getOpenFileName(self, tr("import_profile"), "", "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                import_game_id = data.get("game_id", "")
                current_game_id = self.game_adapter.game_id if self.game_adapter else ""
                if import_game_id and current_game_id and import_game_id != current_game_id:
                    QMessageBox.warning(self, tr("import_check_title"),
                                        tr("import_game_id_mismatch").format(import_game_id, current_game_id))
                    return

                profile_data = data.get("profile", data)
                profile = ProfileSerializer.deserialize(profile_data)

                import_game_version = data.get("game_version", profile.game_version)
                current_game_version = self.parser.game_version if self.parser else ""
                version_mismatch = import_game_version and current_game_version and import_game_version != current_game_version

                if "name" in data:
                    base_name = data["name"]
                else:
                    base_name = os.path.splitext(os.path.basename(file_path))[0]

                profile_name = base_name
                counter = 1
                existing_profile = self.config_manager.get_profile(profile_name)
                name_conflict = existing_profile is not None

                missing_mods = []
                valid_ids = {mod.id for mod in self.mod_service.all_mods}
                for mod_id in profile.mod_order:
                    if mod_id not in valid_ids:
                        mod = self.mod_service.get_mod_by_id(mod_id)
                        display_name = mod.name if mod else mod_id
                        original_id = mod.original_id if mod else mod_id
                        workshop_id = mod.workshop_id if mod else None
                        missing_mods.append({
                            "id": original_id,
                            "display_name": display_name,
                            "workshop_id": workshop_id
                        })

                warnings = []
                if version_mismatch:
                    warnings.append(tr("import_version_mismatch").format(import_game_version, current_game_version))

                if warnings or name_conflict:
                    msg_box = QMessageBox(self)
                    msg_box.setWindowTitle(tr("import_check_title"))
                    msg_box.setIcon(QMessageBox.Icon.Warning)

                    warning_text = ""
                    if warnings:
                        warning_text = tr("import_warnings") + ":\n• " + "\n• ".join(warnings)
                    if name_conflict:
                        if warning_text:
                            warning_text += "\n\n"
                        warning_text += tr("profile_name_conflict").format(profile_name)

                    msg_box.setText(warning_text)
                    msg_box.setStandardButtons(QMessageBox.StandardButton.Cancel)
                    btn_continue = None
                    btn_overwrite = None
                    btn_rename = None
                    if name_conflict:
                        btn_overwrite = msg_box.addButton(tr("overwrite"), QMessageBox.ButtonRole.ActionRole)
                        btn_rename = msg_box.addButton(tr("auto_rename"), QMessageBox.ButtonRole.ActionRole)
                    else:
                        btn_continue = msg_box.addButton(tr("continue_import"), QMessageBox.ButtonRole.ActionRole)
                    msg_box.exec()

                    clicked = msg_box.clickedButton()
                    if btn_continue and clicked == btn_continue:
                        pass
                    elif name_conflict and clicked == btn_overwrite:
                        self.config_manager.delete_profile(profile_name)
                    elif name_conflict and clicked == btn_rename:
                        while profile_name in self.config_manager.profiles:
                            profile_name = f"{base_name}_{counter}"
                            counter += 1
                    else:
                        return

                if not self._prompt_unsaved_changes_for_switch():
                    return

                if missing_mods:
                    from ui.widgets.missing_mods_dialog import MissingModsDialog
                    if not MissingModsDialog.check_and_show(missing_mods, profile_name, self.base_font_size, self):
                        return

                if current_game_version:
                    profile.game_version = current_game_version
                self.config_manager.profiles[profile_name] = profile
                self.config_manager.save_profile(profile_name, profile, self.mod_service.get_mod_by_id)
                self._refresh_profiles(profile_name)
                self._on_profile_changed(profile_name, skip_unsaved_check=True)
                self.status_bar.showMessage(tr("profile_imported").format(profile_name))
            except Exception as e:
                logger.error(f"Failed to import profile: {e}")
                QMessageBox.warning(self, tr("error_title"), str(e))

    def _export_mod_metadata(self):
        file_path, _ = QFileDialog.getSaveFileName(self, tr("export_mod_metadata"), "", "JSON Files (*.json)")
        if file_path:
            self.mod_manager.export_metadata(file_path)
            self.status_bar.showMessage(tr("metadata_exported"))

    def _import_mod_metadata(self):
        file_path, _ = QFileDialog.getOpenFileName(self, tr("import_mod_metadata"), "", "JSON Files (*.json)")
        if file_path:
            try:
                if self.mod_manager.import_metadata(file_path):
                    self._refresh_list_items()
                    self.status_bar.showMessage(tr("metadata_imported"))
            except Exception as e:
                logger.error(f"Failed to import metadata from {file_path}: {e}")
                QMessageBox.warning(self, tr("error_title"), str(e))

    def _refresh_profiles(self, current_name: str = None):
        profiles = self.config_manager.get_all_profiles()
        self.profile_bar.set_profiles(list(profiles.keys()), current_name)

    def _refresh_profile_combo(self):
        profiles = self.config_manager.get_all_profiles()
        result = self.config_manager.restore_last_profile_with_fallback()
        if result:
            profile_name, profile = result
            self.profile_bar.set_profiles(list(profiles.keys()), profile_name)
            self.current_profile = profile
            self.current_profile_name = profile_name
        else:
            self.profile_bar.set_profiles(list(profiles.keys()))
