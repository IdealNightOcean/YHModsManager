import logging
from typing import List

from PyQt6.QtWidgets import QMessageBox

from core.event_bus import get_event_bus
from core.manager_collection import get_manager_collection
from plugin_system import get_plugin_loader
from yh_mods_manager_sdk import ListType, ModIssueStatus
from yh_mods_manager_sdk.enum_extension import EnumExtension, get_issue_extension
from ui.i18n import tr

logger = logging.getLogger(__name__)


class ModOperationsMixin:
    def _enable_selected_mods(self):
        mod_ids = self._mod_operations.get_selected_mod_ids(self.disabled_list)
        self._enable_mods(mod_ids)

    def _on_disabled_double_click(self, item):
        if item:
            self._enable_mods([item.mod.id])

    def _enable_mods(self, mod_ids: List[str], insert_pos: int = -1):
        result = self.mod_service.enable_mods(mod_ids, insert_pos)
        self._refresh_lists_for_mod_change(result.affected_mods, enable=True, insert_pos=insert_pos)
        self._sync_enabled_order_from_ui()
        self._invalidate_dependency_cache()
        self._auto_validate_load_order()
        self._update_dependency_lines()
        self._mark_unsaved()

        event_bus = get_event_bus()
        for mod_id in result.affected_mods:
            event_bus.emit_mod_state_changed(mod_id, True, source="main_window")

    def _disable_mods(self, mod_ids: List[str], insert_pos: int = -1):
        result = self.mod_service.disable_mods(mod_ids, insert_pos)
        self._refresh_lists_for_mod_change(result.affected_mods, enable=False, insert_pos=insert_pos)
        self._invalidate_dependency_cache()
        self._auto_validate_load_order()
        self._update_dependency_lines()
        self._mark_unsaved()

        event_bus = get_event_bus()
        for mod_id in result.affected_mods:
            event_bus.emit_mod_state_changed(mod_id, False, source="main_window")

    def _refresh_lists_for_mod_change(self, affected_mod_ids: List[str], enable: bool, insert_pos: int = -1):
        if not affected_mod_ids:
            return

        with self._batch_update_both_lists():
            self._mod_operations.move_items_between_lists(affected_mod_ids, enable, insert_pos)

        first_mod = self.mod_service.get_mod_by_id(affected_mod_ids[0])
        if first_mod:
            self._update_info_panel(first_mod)

    def _update_all_enabled_mods_status(self):
        with self._batch_update_context(self.enabled_list):
            self._mod_operations.update_items_display(self.enabled_list)

    def _disable_selected_mods(self):
        mod_ids = self._mod_operations.get_selected_mod_ids(self.enabled_list)
        self._disable_mods(mod_ids)

    def _on_enabled_double_click(self, item):
        if item:
            self._disable_mods([item.mod.id])

    def _on_mods_moved_to_enabled(self, mod_ids: List[str], _source_type: ListType, drop_pos: int):
        try:
            self._enable_mods(mod_ids, drop_pos)
        except RuntimeError as e:
            logger.warning(f"Failed to enable mods {mod_ids}: {e}")

    def _on_mods_moved_to_disabled(self, mod_ids: List[str], _source_type: ListType, drop_pos: int):
        try:
            insert_pos = min(drop_pos, len(self.mod_service.disabled_mod_order))
            self._disable_mods(mod_ids, insert_pos)
        except RuntimeError as e:
            logger.warning(f"Failed to disable mods {mod_ids}: {e}")

    def _reorder_disabled_list(self):
        self.disabled_list.setUpdatesEnabled(False)
        self.disabled_list.blockSignals(True)
        try:
            new_order = self._mod_operations.reorder_list(ListType.DISABLED)
        finally:
            self.disabled_list.blockSignals(False)
            self.disabled_list.setUpdatesEnabled(True)
            self.disabled_list.viewport().update()
        self.mod_service.reorder_disabled_mods(new_order)

    def _sync_enabled_order_from_ui(self):
        new_order = self._mod_operations.reorder_list(ListType.ENABLED)
        self.mod_service.reorder_enabled_mods(new_order)

    def _reorder_enabled_list(self):
        self.enabled_list.setUpdatesEnabled(False)
        self.enabled_list.blockSignals(True)
        try:
            new_order = self._mod_operations.reorder_list(ListType.ENABLED)
        finally:
            self.enabled_list.blockSignals(False)
            self.enabled_list.setUpdatesEnabled(True)
            self.enabled_list.viewport().update()
        self.mod_service.reorder_enabled_mods(new_order)
        self._auto_validate_load_order()
        self._update_dependency_lines()
        self._mark_unsaved()

    def _enable_all_mods(self):
        mod_ids = self._mod_operations.get_unenabled_mod_ids()
        if mod_ids:
            self._enable_mods(mod_ids)
            self._refresh_disabled_list()

    def _disable_all_mods(self):
        self.mod_service.disable_all_mods()
        self._refresh_enabled_list()
        self._refresh_disabled_list()
        self._update_status()
        self._invalidate_dependency_cache()
        self._update_dependency_lines()

    def _move_mod_up(self):
        if not self._mod_operations.move_mod_up():
            return
        self.enabled_list.viewport().update()
        self._reorder_enabled_list()

    def _move_mod_down(self):
        if not self._mod_operations.move_mod_down():
            return
        self.enabled_list.viewport().update()
        self._reorder_enabled_list()

    def _simple_sort(self):
        if not self.mod_service.resolver:
            QMessageBox.warning(self, tr("error_title"), tr("please_scan_first"))
            return
        reply = QMessageBox.question(self, tr("confirm_sort_title"), tr("confirm_sort_message"),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        manager_collection = get_manager_collection()
        all_mods = self.mod_service.all_mods

        sort_providers = []
        if self.game_adapter:
            sort_providers.append(self.game_adapter)
        sort_providers.extend(get_plugin_loader().get_available_feature_plugins().values())

        sorted = False
        for provider in sort_providers:
            custom_result = provider.custom_topological_sort(all_mods, manager_collection)
            if custom_result is not None:
                sorted_ids = [mod.id for mod in custom_result]
                self.mod_service.reorder_enabled_mods(sorted_ids)
                sorted = True
                break

        if not sorted:
            success, sorted_ids, error = self.mod_service.sort_topologically()
            if not success:
                QMessageBox.warning(self, tr("sort_error"), error)
                return

        self._refresh_enabled_list()
        self._auto_validate_load_order()
        self.status_bar.showMessage(tr("sort_completed"))
        self._mark_unsaved()

    def _check_issues(self):
        if not self.mod_service.resolver:
            QMessageBox.warning(self, tr("error_title"), tr("please_scan_first"))
            return
        result, _ = self.mod_service.validate_all()
        self._run_dynamic_error_checks()
        self._refresh_list_items()
        self._update_status()

        enabled_order = self.mod_manager.enabled_mod_order
        all_issues = self._collect_enabled_mod_issues(enabled_order)

        if not all_issues:
            QMessageBox.information(self, tr("validation_result"), tr("no_issues_found"))
        else:
            from PyQt6.QtCore import QTimer
            from ui.dialogs.validation_result_dialog import ValidationResultDialog
            QTimer.singleShot(100, lambda: ValidationResultDialog.show_errors(all_issues, self.base_font_size, self,
                                                                              enabled_order))

    def _collect_enabled_mod_issues(self, enabled_order: List[str]) -> List[str]:
        issues = []
        mod_cache = {mod.id: mod for mod in self.mod_manager.all_mods}
        status_extension = get_issue_extension()

        for mod_id in enabled_order:
            mod = mod_cache.get(mod_id)
            if not mod or mod.issue_status == ModIssueStatus.NORMAL:
                continue

            for issue_type in EnumExtension.PREDEFINE_MOD_ISSUES_STATUS:
                if mod.has_visible_issue(issue_type):
                    label = status_extension.get_issue_label_key(issue_type)
                    details = mod.get_issue_details(issue_type)
                    if details:
                        if issue_type == ModIssueStatus.MISSING_DEPENDENCIES:
                            deps_str = ", ".join(details)
                            issues.append(f"[{mod_id}]'{mod.display_name}': {label} ({deps_str})")
                        else:
                            for detail in details:
                                issues.append(f"[{mod_id}]'{mod.display_name}': {detail}")
                    else:
                        issues.append(f"[{mod_id}]'{mod.display_name}': {label}")

        return issues

    def _run_dynamic_error_checks(self):
        manager_collection = get_manager_collection()
        all_mods = self.mod_service.all_mods
        game_metadata = self._game_metadata_manager.get_metadata()

        if not game_metadata:
            return

        if self.game_adapter:
            try:
                self.game_adapter.dynamic_error_check(all_mods, game_metadata, manager_collection)
            except Exception as e:
                logger.error(f"Game adapter dynamic_error_check failed: {e}")

        for feature_plugin in get_plugin_loader().get_available_feature_plugins().values():
            try:
                feature_plugin.dynamic_error_check(all_mods, game_metadata, manager_collection)
            except Exception as e:
                logger.error(f"Feature plugin dynamic_error_check failed: {e}")

    def _auto_validate_load_order(self):
        self._validate_debouncer.trigger()

    def _do_auto_validate_load_order(self):
        if not self.mod_service.resolver:
            return
        self.mod_service.validate_all()
        self._run_dynamic_error_checks()
        self._refresh_list_items()
        self._update_status()
