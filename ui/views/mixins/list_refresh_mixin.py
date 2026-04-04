import os

from PyQt6.QtWidgets import QListWidget

from ui.i18n import tr
from ui.widgets import ModListItem
from utils.mod_ui_utils import ModUIUtils


class ListRefreshMixin:
    def _batch_update_context(self, list_widget: QListWidget):
        class BatchContext:
            def __init__(self, lw):
                self.lw = lw

            def __enter__(self):
                self.lw.setUpdatesEnabled(False)
                self.lw.blockSignals(True)
                self.lw.begin_batch_operation()
                return self

            def __exit__(self, *args):
                self.lw.end_batch_operation()
                self.lw.blockSignals(False)
                self.lw.setUpdatesEnabled(True)
                self.lw.viewport().update()

        return BatchContext(list_widget)

    def _batch_update_both_lists(self):
        class DualBatchContext:
            def __init__(self, lw1, lw2):
                self.lw1, self.lw2 = lw1, lw2

            def __enter__(self):
                for lw in (self.lw1, self.lw2):
                    lw.setUpdatesEnabled(False)
                    lw.blockSignals(True)
                    lw.begin_batch_operation()
                return self

            def __exit__(self, *args):
                for lw in (self.lw1, self.lw2):
                    lw.end_batch_operation()
                    lw.blockSignals(False)
                    lw.setUpdatesEnabled(True)
                    lw.viewport().update()

        return DualBatchContext(self.disabled_list, self.enabled_list)

    def _refresh_disabled_list(self):
        self._clear_selection()
        with self._batch_update_context(self.disabled_list):
            self.disabled_list.clear()
            parsed = self.search_parser.parse(self.disabled_search.text())
            type_filter = self.disabled_panel.get_type_filter_value()
            filter_only_mode = self.disabled_panel.is_filter_only_mode()

            all_disabled_mods = list(self.mod_service.get_disabled_mods())
            all_disabled_mods.sort(key=lambda m: m.display_name.lower())

            for real_idx, mod in enumerate(all_disabled_mods):
                matches_search = self.search_parser.matches(mod, parsed)
                matches_type = not type_filter or mod.mod_type == type_filter

                if filter_only_mode:
                    if matches_search and matches_type:
                        self.disabled_list.addItem(ModListItem(mod, show_order=True, order=real_idx + 1))
                else:
                    is_masked = not (matches_search and matches_type)
                    self.disabled_list.addItem(
                        ModListItem(mod, show_order=True, order=real_idx + 1, is_masked=is_masked))
            self._update_disable_list_statistics()

    def _refresh_enabled_list(self):
        self._clear_selection()
        with self._batch_update_context(self.enabled_list):
            self.enabled_list.clear()
            parsed = self.search_parser.parse(self.enabled_search.text())
            type_filter = self.enabled_panel.get_type_filter_value()
            filter_only_mode = self.enabled_panel.is_filter_only_mode()

            for real_idx, mod_id in enumerate(self.mod_service.enabled_mod_order):
                mod = self.mod_service.get_mod_by_id(mod_id)
                if not mod:
                    continue

                matches_search = self.search_parser.matches(mod, parsed)
                matches_type = not type_filter or mod.mod_type == type_filter

                if filter_only_mode:
                    if matches_search and matches_type:
                        self.enabled_list.addItem(ModListItem(mod, show_order=True, order=real_idx + 1))
                else:
                    is_masked = not (matches_search and matches_type)
                    self.enabled_list.addItem(
                        ModListItem(mod, show_order=True, order=real_idx + 1, is_masked=is_masked))

            self._update_enable_list_statistics()

    def _update_status(self):
        total = len(self.mod_service.all_mods)
        enabled = self.enabled_list.count()
        profile = self.current_profile_name if self.current_profile_name else tr("none")
        game_dir_path = self.config_manager.get_game_dir_path()
        path_info = f" | {tr('game_dir_path_set')}: {os.path.basename(game_dir_path)}" if game_dir_path else ""
        self.status_bar.showMessage(tr("status_format").format(total, enabled, profile, path_info))
        self._update_disable_list_statistics()
        self._update_enable_list_statistics()

    def _update_disable_list_statistics(self):
        disabled_count = self.disabled_list.count()
        disabled_issue_count = ModUIUtils.count_items_with_condition(
            self.disabled_list,
            lambda item: item.mod.has_visible_static_issue(),
            ModListItem
        )
        self.disabled_panel.set_count(disabled_count, disabled_issue_count)

    def _update_enable_list_statistics(self):
        enabled_count = self.enabled_list.count()
        enabled_issue_count = ModUIUtils.count_items_with_condition(
            self.enabled_list,
            lambda item: item.mod.has_any_visible_issue(),
            ModListItem
        )
        self.enabled_panel.set_count(enabled_count, enabled_issue_count)

    def _do_filter_disabled(self, text: str):
        self._mod_operations.set_search_texts(disabled=text)
        self._refresh_disabled_list()

    def _do_filter_enabled(self, text: str):
        self._mod_operations.set_search_texts(enabled=text)
        self._refresh_enabled_list()
        self._update_dependency_lines()

    def _refresh_list_items(self):
        with self._batch_update_both_lists():
            for item in ModUIUtils.iterate_list_items(self.enabled_list, ModListItem):
                item.update_display()
            for item in ModUIUtils.iterate_list_items(self.disabled_list, ModListItem):
                item.update_display()

    def _clear_mod_lists(self):
        self.enabled_list.clear()
        self.disabled_list.clear()
        self.mod_manager.clear_all()
        self.info_panel.set_current_mod(None)

        from core.manager_collection import get_manager_collection
        manager_collection = get_manager_collection()
        if manager_collection:
            manager_collection.clear_game_data()
