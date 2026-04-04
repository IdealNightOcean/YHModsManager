from typing import Optional

from plugin_system.plugin_events import get_event_bus, PluginEventType
from yh_mods_manager_sdk import ListType, Mod
from ui.widgets import ModListItem
from utils.mod_ui_utils import ModUIUtils


class SelectionMixin:
    _selection_just_changed: bool

    def _on_item_clicked(self, item):
        if not item:
            return
        sender_list = self.sender()
        if self._selection_just_changed:
            self._selection_just_changed = False
            return
        if self._selection_manager.is_selected(item.mod.id) and item.isSelected():
            sender_list.blockSignals(True)
            sender_list.clearSelection()
            sender_list.blockSignals(False)
            self._selection_manager.remove_from_selection(item.mod.id)
            self._update_selection_ui()
            dep_widget = self.enabled_list.get_dependency_widget()
            if dep_widget:
                dep_widget.set_highlight_mod(None, is_selected=True)
            self.legend_widget.set_highlight_mod(None, is_selected=True)

    def _on_selection_changed(self, source_list):
        self._selection_just_changed = True
        list_type = ListType.ENABLED if source_list == self.enabled_list else ListType.DISABLED
        selected_items = source_list.selectedItems()
        if not self._selection_manager.can_select_in_list(list_type):
            other_list = self.disabled_list if source_list == self.enabled_list else self.enabled_list
            other_list.blockSignals(True)
            other_list.clearSelection()
            other_list.blockSignals(False)
            self._selection_manager.clear_selection()
            if selected_items:
                for item in selected_items:
                    if item:
                        self._selection_manager.add_to_selection(item.mod.id, list_type)
            self._update_selection_ui()
            return
        self._selection_manager.clear_selection()
        if selected_items:
            for item in selected_items:
                if item:
                    self._selection_manager.add_to_selection(item.mod.id, list_type)
        self._update_selection_ui()

    def _update_selection_ui(self):
        primary_id = self._selection_manager.get_primary_selection()
        if primary_id:
            mod = self._find_mod_by_id(primary_id)
            self._update_info_panel(mod)
        else:
            self._update_info_panel(None)
        self.enabled_list.viewport().update()
        self.disabled_list.viewport().update()
        dep_widget = self.enabled_list.get_dependency_widget()
        if dep_widget:
            dep_widget.set_highlight_mod(primary_id, is_selected=True)
        self.legend_widget.set_highlight_mod(primary_id, is_selected=True)

        get_event_bus().publish(
            PluginEventType.MOD_SELECTION_CHANGED,
            {
                "selected_ids": self._selection_manager.get_selected_ids(),
                "primary_id": primary_id,
                "list_type": self._selection_manager.get_active_list(),
                "is_multi": self._selection_manager.is_multi_select()
            }
        )

    def _clear_selection(self):
        self._selection_manager.clear_selection()
        self._update_selection_ui()

    def _find_mod_by_id(self, mod_id: str) -> Optional[Mod]:
        item = ModUIUtils.find_item_by_mod_id(self.enabled_list, mod_id, ModListItem)
        if item:
            return item.mod
        item = ModUIUtils.find_item_by_mod_id(self.disabled_list, mod_id, ModListItem)
        if item:
            return item.mod
        return None

    def _set_global_selected_mod(self, mod_id: Optional[str], list_type: Optional[ListType] = None):
        self._selection_manager.clear_selection()
        self.enabled_list.blockSignals(True)
        self.disabled_list.blockSignals(True)
        self.enabled_list.clearSelection()
        self.disabled_list.clearSelection()
        if mod_id and list_type:
            self._selection_manager.select_single(mod_id, list_type)
            target_list = self.enabled_list if list_type == ListType.ENABLED else self.disabled_list
            item = ModUIUtils.find_item_by_mod_id(target_list, mod_id, ModListItem)
            if item:
                target_list.setCurrentItem(item)
        self.enabled_list.blockSignals(False)
        self.disabled_list.blockSignals(False)
        self._update_selection_ui()

    def _update_info_panel(self, mod: Optional[Mod]):
        self.info_panel.set_current_mod(mod)

    def _on_mod_color_changed(self, _mod_id: str, _color):
        self._refresh_list_items()

    def _locate_mod(self, mod_id: str):
        if not mod_id:
            return
        for list_widget in [self.enabled_list, self.disabled_list]:
            item = ModUIUtils.find_item_by_mod_id(list_widget, mod_id, ModListItem)
            if item:
                list_type = ListType.ENABLED if list_widget == self.enabled_list else ListType.DISABLED
                list_widget.setCurrentItem(item)
                list_widget.scrollToItem(item)
                self._update_info_panel(item.mod)
                self._set_global_selected_mod(item.mod.id, list_type)
                return
