"""
Mod UI操作模块
专注于UI列表的操作逻辑，不包含业务逻辑
业务逻辑委托给 ModService 处理
"""

from typing import List, TYPE_CHECKING

from yh_mods_manager_sdk.enum_types import ListType

if TYPE_CHECKING:
    from .mod_service import ModService
    from ui.draggable_list import DraggableListWidget
    from ui.widgets import ModListItem


class ModOperations:
    """Mod UI操作类 - 仅处理UI层面的列表操作
    
    职责：
    1. 列表项的移动（UI层面）
    2. 列表项的重排序（UI层面）
    3. 获取选中的Mod ID
    
    不负责：
    - Mod启用/禁用的业务逻辑（由ModService处理）
    - 依赖验证（由ModService处理）
    - 拓扑排序（由ModService处理）
    """

    def __init__(
            self,
            mod_service: 'ModService',
            enabled_list: 'DraggableListWidget',
            disabled_list: 'DraggableListWidget'
    ):
        self._service = mod_service
        self.enabled_list = enabled_list
        self.disabled_list = disabled_list
        self._enabled_search_text = ''
        self._disabled_search_text = ''

    @property
    def mod_service(self) -> 'ModService':
        return self._service

    def set_search_texts(self, enabled: str = '', disabled: str = ''):
        self._enabled_search_text = enabled
        self._disabled_search_text = disabled

    def get_unenabled_mod_ids(self) -> List[str]:
        if not self._service.all_mods:
            return []
        return [mod.id for mod in self._service.all_mods if not self._service.is_mod_enabled(mod.id)]

    def move_items_between_lists(
            self,
            affected_mod_ids: List[str],
            enable: bool,
            insert_pos: int = -1
    ) -> List['ModListItem']:
        if not affected_mod_ids:
            return []

        affected_set = set(affected_mod_ids)
        moved_items = []

        if enable:
            source_list = self.disabled_list
            target_list = self.enabled_list
        else:
            source_list = self.enabled_list
            target_list = self.disabled_list

        items_to_move = []
        for i in range(source_list.count() - 1, -1, -1):
            item = source_list.item(i)
            if item and item.mod.id in affected_set:
                items_to_move.append(source_list.takeItem(i))

        for item in items_to_move:
            item.update_display()
            if 0 <= insert_pos < target_list.count():
                target_list.insertItem(insert_pos, item)
            else:
                target_list.addItem(item)
            moved_items.append(item)

        return moved_items

    def reorder_list(self, list_type: ListType) -> List[str]:
        if list_type == ListType.ENABLED:
            list_widget = self.enabled_list
            has_filter = bool(self._enabled_search_text.strip())
            current_order = list(self._service.enabled_mod_order)
        else:
            list_widget = self.disabled_list
            has_filter = bool(self._disabled_search_text.strip())
            current_order = list(self._service.disabled_mod_order)

        visible_order = []
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item:
                item.order = i + 1
                item.update_display()
                visible_order.append(item.mod.id)

        if not has_filter:
            return visible_order

        visible_set = set(visible_order)
        new_order = []
        visible_idx = 0
        for mod_id in current_order:
            if mod_id in visible_set:
                if visible_idx < len(visible_order):
                    new_order.append(visible_order[visible_idx])
                    visible_idx += 1
            else:
                new_order.append(mod_id)
        while visible_idx < len(visible_order):
            new_order.append(visible_order[visible_idx])
            visible_idx += 1

        return new_order

    def move_mod_up(self) -> bool:
        selected = self.enabled_list.selectedItems()
        if not selected:
            return False
        rows = sorted([self.enabled_list.row(item) for item in selected])
        if rows[0] == 0:
            return False

        self.enabled_list.begin_batch_operation()
        try:
            for row in rows:
                item = self.enabled_list.takeItem(row)
                self.enabled_list.insertItem(row - 1, item)
            for item in selected:
                item.setSelected(True)
        finally:
            self.enabled_list.end_batch_operation()

        return True

    def move_mod_down(self) -> bool:
        selected = self.enabled_list.selectedItems()
        if not selected:
            return False
        rows = sorted([self.enabled_list.row(item) for item in selected], reverse=True)
        if rows[0] == self.enabled_list.count() - 1:
            return False

        self.enabled_list.begin_batch_operation()
        try:
            for row in rows:
                item = self.enabled_list.takeItem(row)
                self.enabled_list.insertItem(row + 1, item)
            for item in selected:
                item.setSelected(True)
        finally:
            self.enabled_list.end_batch_operation()

        return True

    @staticmethod
    def get_selected_mod_ids(list_widget) -> List[str]:
        return [
            item.mod.id for item in list_widget.selectedItems()
            if item
        ]

    @staticmethod
    def update_items_display(list_widget):
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item:
                item.update_display()
