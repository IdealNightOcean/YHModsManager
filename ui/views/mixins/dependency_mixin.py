import logging
from typing import Dict, List, Optional

from yh_mods_manager_sdk import Mod
from ui.widgets import ModListItem
from utils.mod_ui_utils import ModUIUtils

logger = logging.getLogger(__name__)


class DependencyMixin:
    _cached_dependency_map: Dict[str, List[str]]
    _dependency_map_dirty: bool

    def _init_dependency_lines_geometry(self):
        self.dependency_lines_widget.setGeometry(self.enabled_list.viewport().rect())

    def _invalidate_dependency_cache(self):
        self._dependency_map_dirty = True

    def _update_dependency_lines(self):
        self._dependency_debouncer.trigger()

    def _do_update_dependency_lines(self):
        if self._dependency_map_dirty:
            self._cached_dependency_map = self._build_dependency_map()
            self._dependency_map_dirty = False

        self.dependency_lines_widget.update_dependencies(self._cached_dependency_map)

        mod_names: Dict[str, str] = {}
        for item in ModUIUtils.iterate_list_items(self.enabled_list, ModListItem):
            mod_names[item.mod.id] = item.mod.display_name
        self.legend_widget.set_mod_names(mod_names)

        self.enabled_list.viewport().update()

    def _on_dependency_colors_updated(self):
        color_manager = self.dependency_lines_widget.get_color_manager()
        self.legend_widget.set_color_manager(color_manager)

    def _build_dependency_map(self) -> Dict[str, List[str]]:
        dep_map: Dict[str, List[str]] = {}
        mod_id_to_mod: Dict[str, Mod] = {}
        enabled_mod_ids: List[str] = []

        for item in ModUIUtils.iterate_list_items(self.enabled_list, ModListItem):
            mod_id_to_mod[item.mod.id] = item.mod
            enabled_mod_ids.append(item.mod.id)

        resolver = self.mod_service.resolver
        if not resolver:
            return dep_map

        id_comparer = resolver.id_comparer
        enabled_set = set(enabled_mod_ids)

        for item in ModUIUtils.iterate_list_items(self.enabled_list, ModListItem):
            mod = item.mod
            if not mod.depended_modules:
                continue

            dep_ids: List[str] = []
            for dep_original_id in mod.depended_modules:
                matched_ids = id_comparer.get_all_mod_ids_by_original_id(dep_original_id, enabled_set)
                for matched_id in matched_ids:
                    if matched_id in mod_id_to_mod and matched_id not in dep_ids:
                        dep_ids.append(matched_id)

            if dep_ids:
                dep_map[mod.id] = dep_ids

        return dep_map

    def _on_legend_clicked(self, mod_id: str):
        self._locate_mod(mod_id)

    def _toggle_dependency_lines(self):
        self.dependency_lines_widget.toggle_lines()
        self.legend_widget.set_show_lines(self.dependency_lines_widget.is_showing_lines())
        self.enabled_list.viewport().update()

    def _on_highlight_changed(self, mod_id: Optional[str]):
        self.legend_widget.set_highlight_mod(mod_id, is_selected=False)
