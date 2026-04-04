import logging
import subprocess
import webbrowser
from typing import List, Optional, Set

from PyQt6.QtWidgets import QMessageBox, QMenu

from core.manager_collection import get_manager_collection
from plugin_system import get_plugin_loader
from yh_mods_manager_sdk import Mod, ModType, ModIssueStatus
from yh_mods_manager_sdk.enum_extension import EnumExtension
from ui.i18n import tr
from ui.toast_widget import ToastManager
from utils.mod_ui_utils import ModUIUtils

logger = logging.getLogger(__name__)


class ContextMenuMixin:
    def _show_mod_context_menu(self, pos):
        item = self.sender().itemAt(pos)
        if not item:
            return

        selected_mods = self._get_selected_mods_for_context_menu()
        if not selected_mods:
            return

        is_multi_select = len(selected_mods) > 1
        menu = QMenu(self)

        self._add_enable_disable_actions(menu, selected_mods, is_multi_select)
        menu.addSeparator()

        self._add_tag_actions(menu, selected_mods, is_multi_select)
        self._add_color_actions(menu, selected_mods, is_multi_select)
        self._add_ignore_issue_actions(menu, selected_mods, is_multi_select)
        menu.addSeparator()

        self._add_copy_actions(menu, selected_mods, is_multi_select)
        self._add_open_actions(menu, selected_mods, is_multi_select)
        menu.addSeparator()

        self._add_delete_actions(menu, selected_mods, is_multi_select)

        self._add_plugin_menu_items(menu, selected_mods)

        menu.exec(self.sender().mapToGlobal(pos))

    def _get_selected_mods_for_context_menu(self) -> List[Mod]:
        selected_ids = self._selection_manager.get_selected_ids()
        if not selected_ids:
            item = self.sender().currentItem()
            if item:
                return [item.mod]
            return []

        mods = []
        for mod_id in selected_ids:
            mod = self._find_mod_by_id(mod_id)
            if mod:
                mods.append(mod)
        return mods

    def _add_enable_disable_actions(self, menu: QMenu, selected_mods: List[Mod], is_multi_select: bool):
        deletable_mods = [m for m in selected_mods if m.mod_type not in (ModType.CORE, ModType.DLC)]
        if not deletable_mods:
            return

        if self.sender() == self.disabled_list:
            enable_action = menu.addAction(tr("enable"))
            mod_ids = [m.id for m in deletable_mods]
            enable_action.triggered.connect(lambda: self._enable_mods(mod_ids))
        else:
            disable_action = menu.addAction(tr("disable"))
            mod_ids = [m.id for m in deletable_mods]
            disable_action.triggered.connect(lambda: self._disable_mods(mod_ids))

    def _add_tag_actions(self, menu: QMenu, selected_mods: List[Mod], is_multi_select: bool):
        add_tag_menu = menu.addMenu(tr("add_common_tag"))
        enabled_tags = self.user_config.get_enabled_tags()
        if enabled_tags:
            for tag_config in enabled_tags:
                display_name = tr(tag_config.name) if tag_config.name.startswith("tag_") else tag_config.name
                tag_action = add_tag_menu.addAction(display_name)
                tag_action.triggered.connect(
                    lambda checked, t=tag_config.name, mods=selected_mods: self._batch_add_tag_to_mods(mods, t))
        else:
            no_tag_action = add_tag_menu.addAction(tr("no_common_tags"))
            no_tag_action.setEnabled(False)

        remove_tag_menu = menu.addMenu(tr("remove_common_tag"))
        if enabled_tags:
            for tag_config in enabled_tags:
                display_name = tr(tag_config.name) if tag_config.name.startswith("tag_") else tag_config.name
                tag_action = remove_tag_menu.addAction(display_name)
                tag_action.triggered.connect(
                    lambda checked, t=tag_config.name, mods=selected_mods: self._batch_remove_tag_from_mods(mods, t))
        else:
            no_tag_action = remove_tag_menu.addAction(tr("no_common_tags"))
            no_tag_action.setEnabled(False)

    def _add_color_actions(self, menu: QMenu, selected_mods: List[Mod], is_multi_select: bool):
        color_menu = menu.addMenu(tr("set_color"))
        no_color_action = color_menu.addAction(tr("no_color"))
        no_color_action.triggered.connect(lambda: self._batch_set_mod_color(selected_mods, None))
        color_menu.addSeparator()
        enabled_colors = self.user_config.get_enabled_colors()
        for color_option in enabled_colors:
            display_name = tr(color_option.name_key)
            color_action = color_menu.addAction(display_name)
            color_action.triggered.connect(
                lambda checked, c=color_option.color, mods=selected_mods: self._batch_set_mod_color(mods, c))

    def _add_ignore_issue_actions(self, menu: QMenu, selected_mods: List[Mod], is_multi_select: bool):
        ignore_menu = menu.addMenu(tr("ignore_issue"))

        for issue_status in EnumExtension.PREDEFINE_MOD_ISSUES_STATUS:
            display_name = tr(EnumExtension.get_issue_label_key(issue_status))
            action = ignore_menu.addAction(display_name)
            action.triggered.connect(
                lambda checked, s=issue_status, mods=selected_mods: self._batch_set_ignored_issue(mods, s, True))

        clear_ignore_menu = menu.addMenu(tr("clear_ignore_issue"))

        for issue_status in EnumExtension.PREDEFINE_MOD_ISSUES_STATUS:
            display_name = tr(EnumExtension.get_issue_label_key(issue_status))
            action = clear_ignore_menu.addAction(display_name)
            action.triggered.connect(
                lambda checked, s=issue_status, mods=selected_mods: self._batch_set_ignored_issue(mods, s, False))

    def _add_copy_actions(self, menu: QMenu, selected_mods: List[Mod], is_multi_select: bool):
        if is_multi_select:
            return

        mod = selected_mods[0]
        copy_name_action = menu.addAction(tr("copy_mod_name"))
        copy_name_action.triggered.connect(lambda: self._copy_mod_name(mod))

        copy_id_action = menu.addAction(tr("copy_mod_id"))
        copy_id_action.triggered.connect(lambda: self._copy_mod_id(mod.id))

        if mod.custom_color:
            menu.addSeparator()
            copy_color_action = menu.addAction(tr("copy_mod_color"))
            copy_color_action.triggered.connect(lambda: self._copy_mod_color(mod.custom_color))

    @staticmethod
    def _copy_mod_name(mod: Mod):
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(mod.name)
        ToastManager.show(tr("copied_to_clipboard").format(mod.name))

    @staticmethod
    def _copy_mod_id(mod_id: str):
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(mod_id)
        ToastManager.show(tr("copied_to_clipboard").format(mod_id))

    @staticmethod
    def _add_open_actions(menu: QMenu, selected_mods: List[Mod], is_multi_select: bool):
        if is_multi_select:
            return

        mod = selected_mods[0]

        open_folder_action = menu.addAction(tr("open_local_folder"))
        open_folder_action.triggered.connect(lambda: ModUIUtils.open_mod_folder(mod))

        if mod.mod_type == ModType.WORKSHOP and mod.workshop_id:
            open_workshop_action = menu.addAction(tr("open_workshop_page"))
            open_workshop_action.triggered.connect(lambda: ModUIUtils.open_workshop_page(mod))

    def _add_delete_actions(self, menu: QMenu, selected_mods: List[Mod], is_multi_select: bool):
        deletable_mods = [m for m in selected_mods if m.mod_type not in (ModType.CORE, ModType.DLC)]
        if not deletable_mods:
            return

        delete_action = menu.addAction(tr("delete_mod"))
        delete_action.triggered.connect(lambda: self._batch_delete_mods_with_confirm(deletable_mods))

        # steam_mods = [m for m in deletable_mods if m.mod_type == ModType.WORKSHOP and m.workshop_id]
        # if steam_mods:
        #     unsubscribe_action = menu.addAction(tr("unsubscribe_and_delete"))
        #     unsubscribe_action.triggered.connect(lambda: self._batch_unsubscribe_and_delete_mods(deletable_mods))

    def _add_plugin_menu_items(self, menu: QMenu, selected_mods: List[Mod]):
        manager_collection = get_manager_collection()
        if self.game_adapter:
            plugin_menu_items = self.game_adapter.get_context_menu_items(selected_mods, manager_collection)
            if plugin_menu_items:
                menu.addSeparator()
                for item in plugin_menu_items:
                    action_id = item.get("action_id", "")
                    label = item.get("label", "")
                    enabled = item.get("enabled", True)
                    action = menu.addAction(label)
                    action.setEnabled(enabled)
                    action.triggered.connect(
                        lambda checked, aid=action_id: self._on_plugin_context_menu_action(aid, selected_mods))

        for feature_plugin in get_plugin_loader().get_available_feature_plugins().values():
            plugin_menu_items = feature_plugin.get_context_menu_items(selected_mods, manager_collection)
            if plugin_menu_items:
                menu.addSeparator()
                for item in plugin_menu_items:
                    action_id = item.get("action_id", "")
                    label = item.get("label", "")
                    enabled = item.get("enabled", True)
                    action = menu.addAction(label)
                    action.setEnabled(enabled)
                    action.triggered.connect(
                        lambda checked, aid=action_id, fp=feature_plugin: self._on_feature_plugin_context_menu_action(
                            fp, aid, selected_mods))

    def _on_plugin_context_menu_action(self, action_id: str, selected_mods: List):
        manager_collection = get_manager_collection()
        if self.game_adapter:
            self.game_adapter.on_mod_list_action(action_id, selected_mods, manager_collection)

    @staticmethod
    def _on_feature_plugin_context_menu_action(feature_plugin, action_id: str, selected_mods: List):
        from core.manager_collection import get_manager_collection
        manager_collection = get_manager_collection()
        feature_plugin.on_mod_list_action(action_id, selected_mods, manager_collection)

    def _batch_add_tag_to_mods(self, mods: List[Mod], tag: str):
        success_count = 0
        for mod in mods:
            if self.mod_service.add_tag_to_mod(mod.id, tag):
                success_count += 1

        if success_count > 0:
            self._refresh_list_items()
            current_mod_id = self.info_panel.get_current_mod_id()
            if current_mod_id in [m.id for m in mods]:
                self.info_panel.refresh_theme()

            if len(mods) == 1:
                ToastManager.show(tr("tag_added_success").format(tag, mods[0].display_name))
            else:
                ToastManager.show(tr("batch_tag_added_success").format(tag, success_count, len(mods)))

    def _batch_remove_tag_from_mods(self, mods: List[Mod], tag: str):
        success_count = 0
        for mod in mods:
            if tag in mod.tags:
                if self.mod_service.remove_tag_from_mod(mod.id, tag):
                    success_count += 1

        if success_count > 0:
            self._refresh_list_items()
            current_mod_id = self.info_panel.get_current_mod_id()
            if current_mod_id in [m.id for m in mods]:
                self.info_panel.refresh_theme()

            if len(mods) == 1:
                ToastManager.show(tr("tag_removed_success").format(tag, mods[0].display_name))
            else:
                ToastManager.show(tr("batch_tag_removed_success").format(tag, success_count, len(mods)))

    def _batch_set_ignored_issue(self, mods: List[Mod], issue: ModIssueStatus, ignored: bool):
        operations = [(mod.id, issue, ignored) for mod in mods]
        affected_ids = self.mod_service.batch_set_ignored_issues(operations)

        if affected_ids:
            self._refresh_list_items()
            self._update_disable_list_statistics()
            self._update_enable_list_statistics()
            current_mod_id = self.info_panel.get_current_mod_id()
            if current_mod_id in affected_ids:
                self.info_panel.refresh_theme()

            action_text = tr("issue_ignored") if ignored else tr("issue_unignored")
            if len(mods) == 1:
                ToastManager.show(tr("issue_ignore_set_success").format(mods[0].display_name, action_text))
            else:
                ToastManager.show(tr("batch_issue_ignore_set_success").format(len(affected_ids), action_text))

    def _batch_set_mod_color(self, mods: List[Mod], color: Optional[str]):
        success_count = 0
        for mod in mods:
            if self.mod_service.set_mod_color(mod.id, color):
                success_count += 1

        if success_count > 0:
            self._refresh_list_items()
            current_mod_id = self.info_panel.get_current_mod_id()
            if current_mod_id in [m.id for m in mods]:
                self.info_panel.refresh_theme()

            if len(mods) == 1:
                color_text = color if color else tr("no_color")
                ToastManager.show(tr("color_set_success").format(color_text, mods[0].display_name))
            else:
                color_text = color if color else tr("no_color")
                ToastManager.show(tr("batch_color_set_success").format(color_text, success_count, len(mods)))

    @staticmethod
    def _copy_mod_color(color: str):
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(color)
        ToastManager.show(tr("copied_to_clipboard").format(color))

    def _batch_delete_mods_with_confirm(self, mods: List[Mod]):
        if not mods:
            return

        count = len(mods)
        if count == 1:
            message = tr("confirm_delete_mod").format(mods[0].display_name)
        else:
            mod_names = ", ".join([m.display_name for m in mods[:5]])
            if count > 5:
                mod_names += f" ... ({count - 5} more)"
            message = tr("confirm_delete_mods").format(count, mod_names)

        reply = QMessageBox.question(
            self,
            tr("confirm_delete"),
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            success_count = 0
            failed_count = 0
            deleted_ids: List[str] = []

            for mod in mods:
                result = self.mod_service.delete_mod(mod.id)
                if result.success:
                    success_count += 1
                    deleted_ids.append(mod.id)
                else:
                    failed_count += 1

            self._refresh_enabled_list()
            self._refresh_disabled_list()
            self._update_status()

            if success_count > 0:
                if count == 1:
                    ToastManager.show(tr("mod_deleted_success").format(mods[0].display_name))
                else:
                    ToastManager.show(tr("batch_mod_deleted_success").format(success_count))

                from core.event_bus import get_event_bus
                event_bus = get_event_bus()
                for mod_id in deleted_ids:
                    event_bus.emit_mod_deleted(mod_id, source="main_window")

            if failed_count > 0:
                QMessageBox.warning(self, tr("error_title"), tr("batch_mod_delete_partial_failed").format(failed_count))

    def _batch_unsubscribe_and_delete_mods(self, mods: List[Mod]):
        steam_running = False
        try:
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq steam.exe'],
                                    capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            steam_running = 'steam.exe' in result.stdout.lower()
        except (subprocess.SubprocessError, OSError, FileNotFoundError) as e:
            logger.warning(f"Failed to check if Steam is running: {e}")

        if not steam_running:
            QMessageBox.warning(self, tr("error_title"), tr("steam_not_running"))
            return

        steam_mods = [m for m in mods if m.mod_type == ModType.WORKSHOP and m.workshop_id]
        local_mods = [m for m in mods if m.mod_type == ModType.LOCAL]

        count = len(mods)
        steam_count = len(steam_mods)
        local_count = len(local_mods)

        if count == 1:
            message = tr("confirm_unsubscribe_and_delete").format(mods[0].display_name)
        else:
            message_parts = []
            if steam_count > 0:
                message_parts.append(tr("steam_mods_count").format(steam_count))
            if local_count > 0:
                message_parts.append(tr("local_mods_count").format(local_count))
            message = tr("confirm_batch_unsubscribe_and_delete").format(count, "\n".join(message_parts))

        reply = QMessageBox.question(
            self,
            tr("confirm_unsubscribe"),
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            workshop_ids: Set[str] = set()
            for mod in steam_mods:
                if mod.workshop_id:
                    workshop_ids.add(mod.workshop_id)

            for workshop_id in workshop_ids:
                unsubscribe_url = f"steam://unsubscribe/{workshop_id}"
                webbrowser.open(unsubscribe_url)

            success_count = 0
            failed_count = 0
            deleted_ids: List[str] = []

            for mod in mods:
                result = self.mod_service.delete_mod(mod.id)
                if result.success:
                    success_count += 1
                    deleted_ids.append(mod.id)
                else:
                    failed_count += 1

            self._refresh_enabled_list()
            self._refresh_disabled_list()
            self._update_status()

            if success_count > 0:
                if count == 1:
                    ToastManager.show(tr("mod_unsubscribed_success").format(mods[0].display_name))
                else:
                    ToastManager.show(tr("batch_mod_deleted_success").format(success_count))

                from core.event_bus import get_event_bus
                event_bus = get_event_bus()
                for mod_id in deleted_ids:
                    event_bus.emit_mod_deleted(mod_id, source="main_window")

            if failed_count > 0:
                QMessageBox.warning(self, tr("error_title"), tr("batch_mod_delete_partial_failed").format(failed_count))

    def _on_highlight_rules_changed(self, event):
        self.enabled_list.viewport().update()
        self.disabled_list.viewport().update()
