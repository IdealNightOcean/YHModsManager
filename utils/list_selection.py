from typing import Set, Optional, Dict

from yh_mods_manager_sdk import ListType, ListItemState


class ListSelectionManager:
    """统一的列表选择管理器 - 管理两个列表的选择状态"""

    def __init__(self):
        self._selected_mod_ids: Set[str] = set()
        self._primary_selection: Optional[str] = None
        self._active_list: Optional[ListType] = None
        self._selection_state: Dict[str, ListItemState] = {}

    def clear_selection(self):
        """清除所有选择"""
        self._selected_mod_ids.clear()
        self._primary_selection = None
        self._active_list = None
        self._selection_state.clear()

    def select_single(self, mod_id: str, list_type: ListType) -> ListItemState:
        """单选一个项"""
        self.clear_selection()
        self._selected_mod_ids.add(mod_id)
        self._primary_selection = mod_id
        self._active_list = list_type
        state = ListItemState.GLOBAL_SELECTED | ListItemState.SELECTED
        self._selection_state[mod_id] = state
        return state

    def add_to_selection(self, mod_id: str, list_type: ListType) -> bool:
        """添加到多选 - 只能添加到同一个列表"""
        if self._active_list and self._active_list != list_type:
            return False

        self._active_list = list_type
        self._selected_mod_ids.add(mod_id)
        self._primary_selection = mod_id

        if len(self._selected_mod_ids) == 1:
            self._selection_state[mod_id] = ListItemState.GLOBAL_SELECTED | ListItemState.SELECTED
        else:
            for mid in self._selected_mod_ids:
                self._selection_state[mid] = ListItemState.MULTI_SELECTED | ListItemState.SELECTED

        return True

    def remove_from_selection(self, mod_id: str):
        """从选择中移除"""
        self._selected_mod_ids.discard(mod_id)
        self._selection_state.pop(mod_id, None)

        if self._primary_selection == mod_id:
            if self._selected_mod_ids:
                self._primary_selection = next(iter(self._selected_mod_ids))
            else:
                self._primary_selection = None
                self._active_list = None

        if len(self._selected_mod_ids) == 1:
            remaining_id = next(iter(self._selected_mod_ids))
            self._selection_state[remaining_id] = ListItemState.GLOBAL_SELECTED | ListItemState.SELECTED

    def get_state(self, mod_id: str) -> ListItemState:
        """获取指定mod的状态"""
        return self._selection_state.get(mod_id, ListItemState.NONE)

    def is_selected(self, mod_id: str) -> bool:
        """是否被选中"""
        return mod_id in self._selected_mod_ids

    def is_multi_select(self) -> bool:
        """是否处于多选状态"""
        return len(self._selected_mod_ids) > 1

    def get_selected_ids(self) -> Set[str]:
        """获取所有选中的mod id"""
        return self._selected_mod_ids.copy()

    def get_primary_selection(self) -> Optional[str]:
        """获取主选中项"""
        return self._primary_selection

    def get_active_list(self) -> Optional[ListType]:
        """获取当前活动列表"""
        return self._active_list

    def can_select_in_list(self, list_type: ListType) -> bool:
        """检查是否可以在指定列表中选择"""
        return self._active_list is None or self._active_list == list_type
