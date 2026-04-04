"""
MOD更新表格组件
展示MOD更新信息的表格，支持排序和增量更新
"""

from datetime import datetime
from typing import Dict, List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QTableWidget, QTableWidgetItem, QWidget, QVBoxLayout,
    QLabel, QHeaderView, QAbstractItemView, QFrame, QMenu
)

from yh_mods_manager_sdk import Mod, ModType
from services.steam_service import SteamModInfo
from ui.i18n import tr
from ui.styles import get_calculated_font_size, FontSize


class ModUpdateTable(QTableWidget):
    """MOD更新信息表格
    
    展示MOD的更新状态，支持：
    - 表头点击排序
    - 单行增量更新
    - 空数据状态提示
    """

    COLUMN_NAME = 0
    COLUMN_LOCAL_UPDATE = 1
    COLUMN_STEAM_UPDATE = 2
    COLUMN_TYPE = 3
    COLUMN_ENABLED = 4

    SORT_ORDER_ASC = True
    SORT_ORDER_DESC = False

    open_local_folder_requested = pyqtSignal(str)
    open_workshop_requested = pyqtSignal(str)
    copy_mod_name_requested = pyqtSignal(str)
    copy_mod_id_requested = pyqtSignal(str)

    def __init__(self, base_font_size: int = 12, parent=None):
        super().__init__(parent)
        self._base_font_size = base_font_size
        self._mods: Dict[str, Mod] = {}
        self.mod_types: Dict[str, ModType] = {}
        self._steam_info: Dict[str, SteamModInfo] = {}
        self._local_update_times: Dict[str, datetime] = {}
        self.current_sort_column = self.COLUMN_LOCAL_UPDATE
        self.current_sort_order = False
        self._steam_monitor_enabled = True
        self.is_first_load = True

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        self.setColumnCount(5)
        self.setHorizontalHeaderLabels([
            tr("mod_update_col_name"),
            tr("mod_update_col_local"),
            tr("mod_update_col_steam"),
            tr("mod_update_col_type"),
            tr("mod_update_col_enabled")
        ])

        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.setAlternatingRowColors(True)
        self.verticalHeader().setVisible(False)

        header = self.horizontalHeader()
        header.setSectionResizeMode(self.COLUMN_NAME, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(self.COLUMN_LOCAL_UPDATE, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COLUMN_STEAM_UPDATE, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COLUMN_TYPE, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(self.COLUMN_ENABLED, QHeaderView.ResizeMode.ResizeToContents)

        header.setSectionsClickable(True)

        self.setShowGrid(False)
        self.apply_style()

    def apply_style(self):

        self.setProperty("tableType", "mod_update")

    def _connect_signals(self):
        self.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._context_menu)

    def _on_header_clicked(self, column: int):
        if self.current_sort_column == column:
            self.current_sort_order = not self.current_sort_order
        else:
            self.current_sort_column = column
            self.current_sort_order = True

        self.sortByColumn(column,
                          Qt.SortOrder.AscendingOrder if self.current_sort_order else Qt.SortOrder.DescendingOrder)

    # noinspection PyUnresolvedReferences
    def _context_menu(self, pos):
        item = self.itemAt(pos)
        if not item:
            return

        row = item.row()
        name_item = self.item(row, self.COLUMN_NAME)
        if not name_item:
            return

        mod_id = name_item.data(Qt.ItemDataRole.UserRole)
        if not mod_id:
            return

        mod_type = self.mod_types.get(mod_id)
        if not mod_type:
            return

        menu = QMenu(self)
        menu.setProperty("menuType", "context")

        open_folder_action = menu.addAction(tr("open_local_folder"))
        open_folder_action.triggered.connect(lambda: self.open_local_folder_requested.emit(mod_id))

        if mod_type == ModType.WORKSHOP:
            open_workshop_action = menu.addAction(tr("open_workshop_page"))
            open_workshop_action.triggered.connect(lambda: self.open_workshop_requested.emit(mod_id))

        menu.addSeparator()

        copy_name_action = menu.addAction(tr("copy_mod_name"))
        copy_name_action.triggered.connect(lambda: self.copy_mod_name_requested.emit(mod_id))

        copy_id_action = menu.addAction(tr("copy_mod_id"))
        copy_id_action.triggered.connect(lambda: self.copy_mod_id_requested.emit(mod_id))

        menu.exec(self.viewport().mapToGlobal(pos))

    def set_steam_monitor_enabled(self, enabled: bool):
        self._steam_monitor_enabled = enabled
        self._refresh_steam_column_display()

    def set_rows_data(self, rows):
        self.setUpdatesEnabled(False)
        try:
            self.setRowCount(len(rows))

            type_map = {
                ModType.CORE: tr("mod_type_core"),
                ModType.DLC: tr("mod_type_dlc"),
                ModType.WORKSHOP: tr("mod_type_workshop"),
                ModType.LOCAL: tr("mod_type_local")
            }

            for row_idx, row_data in enumerate(rows):
                self.mod_types[row_data.mod_id] = row_data.mod_type

                name_item = QTableWidgetItem(row_data.display_name)
                name_item.setData(Qt.ItemDataRole.UserRole, row_data.mod_id)
                self.setItem(row_idx, self.COLUMN_NAME, name_item)

                local_text = row_data.local_time_text if row_data.local_time_text else tr("mod_update_unknown")
                local_item = QTableWidgetItem(local_text)
                local_item.setData(Qt.ItemDataRole.UserRole,
                                   row_data.local_time.timestamp() if row_data.local_time else 0)
                self.setItem(row_idx, self.COLUMN_LOCAL_UPDATE, local_item)

                steam_text = row_data.steam_time_text if row_data.steam_time_text else "--"
                steam_item = QTableWidgetItem(steam_text)
                steam_item.setData(Qt.ItemDataRole.UserRole, row_data.steam_time)
                self.setItem(row_idx, self.COLUMN_STEAM_UPDATE, steam_item)

                type_text = type_map.get(row_data.mod_type, tr("mod_type_local"))
                type_item = QTableWidgetItem(type_text)
                self.setItem(row_idx, self.COLUMN_TYPE, type_item)

                enabled_text = tr("yes") if row_data.is_enabled else tr("no")
                enabled_item = QTableWidgetItem(enabled_text)
                enabled_item.setData(Qt.ItemDataRole.UserRole, row_data.is_enabled)
                self.setItem(row_idx, self.COLUMN_ENABLED, enabled_item)

            if self.is_first_load:
                self.sortByColumn(self.COLUMN_LOCAL_UPDATE, Qt.SortOrder.DescendingOrder)
                self.current_sort_column = self.COLUMN_LOCAL_UPDATE
                self.current_sort_order = False
                self.is_first_load = False
            else:
                self.sortByColumn(self.current_sort_column,
                                  Qt.SortOrder.AscendingOrder if self.current_sort_order else Qt.SortOrder.DescendingOrder)

            self._update_empty_state()
        finally:
            self.setUpdatesEnabled(True)

    def set_data(self, mods: List[Mod], steam_info: Dict[str, SteamModInfo] = None,
                 local_update_times: Dict[str, datetime] = None):
        self._mods = {mod.id: mod for mod in mods}
        self._steam_info = steam_info or {}
        self._local_update_times = local_update_times or {}
        self._refresh_table()

    def _refresh_table(self):
        self.setRowCount(len(self._mods))

        for row, (mod_id, mod) in enumerate(self._mods.items()):
            self._set_row_data(row, mod)

        self._update_empty_state()

    def _set_row_data(self, row: int, mod: Mod):
        name_item = QTableWidgetItem(mod.display_name)
        name_item.setData(Qt.ItemDataRole.UserRole, mod.id)
        self.setItem(row, self.COLUMN_NAME, name_item)

        local_time = self._local_update_times.get(mod.id)
        local_text = self._format_datetime(local_time) if local_time else tr("mod_update_unknown")
        local_item = QTableWidgetItem(local_text)
        local_item.setData(Qt.ItemDataRole.UserRole, local_time)
        self.setItem(row, self.COLUMN_LOCAL_UPDATE, local_item)

        if self._steam_monitor_enabled and mod.workshop_id:
            steam_info = self._steam_info.get(mod.workshop_id)
            steam_time = steam_info.update_time if steam_info else None
            steam_text = self._format_datetime(steam_time) if steam_time else tr("mod_update_unknown")
        else:
            steam_text = "--"
        steam_item = QTableWidgetItem(steam_text)
        steam_item.setData(Qt.ItemDataRole.UserRole,
                           steam_info.update_time if mod.workshop_id and (
                               steam_info := self._steam_info.get(mod.workshop_id)) else None)
        self.setItem(row, self.COLUMN_STEAM_UPDATE, steam_item)

        type_text = self._get_mod_type_text(mod.mod_type)
        type_item = QTableWidgetItem(type_text)
        self.setItem(row, self.COLUMN_TYPE, type_item)

        enabled_text = tr("yes") if mod.is_enabled else tr("no")
        enabled_item = QTableWidgetItem(enabled_text)
        enabled_item.setData(Qt.ItemDataRole.UserRole, mod.is_enabled)
        self.setItem(row, self.COLUMN_ENABLED, enabled_item)

    def _refresh_steam_column_display(self):
        for row in range(self.rowCount()):
            name_item = self.item(row, self.COLUMN_NAME)
            if not name_item:
                continue

            mod_id = name_item.data(Qt.ItemDataRole.UserRole)
            mod = self._mods.get(mod_id)
            if not mod:
                continue

            steam_item = self.item(row, self.COLUMN_STEAM_UPDATE)
            if not steam_item:
                steam_item = QTableWidgetItem()
                self.setItem(row, self.COLUMN_STEAM_UPDATE, steam_item)

            if self._steam_monitor_enabled and mod.workshop_id:
                steam_info = self._steam_info.get(mod.workshop_id)
                steam_time = steam_info.update_time if steam_info else None
                steam_text = self._format_datetime(steam_time) if steam_time else tr("mod_update_unknown")
                steam_item.setData(Qt.ItemDataRole.UserRole, steam_time)
            else:
                steam_text = "--"
                steam_item.setData(Qt.ItemDataRole.UserRole, None)
            steam_item.setText(steam_text)

    @staticmethod
    def _get_mod_type_text(mod_type: ModType) -> str:
        type_map = {
            ModType.CORE: tr("mod_type_core"),
            ModType.DLC: tr("mod_type_dlc"),
            ModType.WORKSHOP: tr("mod_type_workshop"),
            ModType.LOCAL: tr("mod_type_local")
        }
        return type_map.get(mod_type, tr("mod_type_local"))

    @staticmethod
    def _format_datetime(dt: datetime) -> str:
        if not dt:
            return ""
        return dt.strftime("%Y-%m-%d %H:%M")

    def _update_empty_state(self):
        if self.rowCount() == 0:
            self.setEnabled(False)
        else:
            self.setEnabled(True)

    def update_mod_state(self, mod_id: str, is_enabled: bool):
        for row in range(self.rowCount()):
            name_item = self.item(row, self.COLUMN_NAME)
            if name_item and name_item.data(Qt.ItemDataRole.UserRole) == mod_id:
                enabled_item = self.item(row, self.COLUMN_ENABLED)
                if enabled_item:
                    enabled_item.setText(tr("yes") if is_enabled else tr("no"))
                    enabled_item.setData(Qt.ItemDataRole.UserRole, is_enabled)
                mod = self._mods.get(mod_id)
                if mod:
                    mod.is_enabled = is_enabled
                break

    def update_mod_local_time(self, mod_id: str, update_time: datetime):
        for row in range(self.rowCount()):
            name_item = self.item(row, self.COLUMN_NAME)
            if name_item and name_item.data(Qt.ItemDataRole.UserRole) == mod_id:
                local_item = self.item(row, self.COLUMN_LOCAL_UPDATE)
                if local_item:
                    local_item.setText(self._format_datetime(update_time))
                    local_item.setData(Qt.ItemDataRole.UserRole, update_time)
                self._local_update_times[mod_id] = update_time
                break

    def add_mod(self, mod: Mod, local_update_time: datetime = None):
        if mod.id in self._mods:
            return

        self.setUpdatesEnabled(False)
        try:
            self._mods[mod.id] = mod
            if local_update_time:
                self._local_update_times[mod.id] = local_update_time

            self.insertRow(self.rowCount())
            self._set_row_data(self.rowCount() - 1, mod)
            self._update_empty_state()
        finally:
            self.setUpdatesEnabled(True)

    def remove_mod(self, mod_id: str):
        self.setUpdatesEnabled(False)
        try:
            for row in range(self.rowCount()):
                name_item = self.item(row, self.COLUMN_NAME)
                if name_item and name_item.data(Qt.ItemDataRole.UserRole) == mod_id:
                    self.removeRow(row)
                    if mod_id in self._mods:
                        del self._mods[mod_id]
                    if mod_id in self._local_update_times:
                        del self._local_update_times[mod_id]
                    break
            self._update_empty_state()
        finally:
            self.setUpdatesEnabled(True)

    def clear_data(self):
        self._mods.clear()
        self._steam_info.clear()
        self._local_update_times.clear()
        self.setRowCount(0)
        self._update_empty_state()


class EmptyStateWidget(QWidget):
    """空数据状态提示组件"""

    def __init__(self, base_font_size: int = 12, parent=None):
        super().__init__(parent)
        self._base_font_size = base_font_size
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._label = QLabel(tr("mod_update_empty"))
        self._label.setProperty("labelType", "empty_message")
        font = self._label.font()
        font.setPointSize(get_calculated_font_size(self._base_font_size, FontSize.LARGE))
        self._label.setFont(font)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._label)

    def set_message(self, message: str):
        self._label.setText(message)


class LoadingOverlay(QWidget):
    """加载中遮罩组件"""

    def __init__(self, base_font_size: int = 12, parent=None):
        super().__init__(parent)
        self._base_font_size = base_font_size
        self._setup_ui()
        self.hide()

    def _setup_ui(self):
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._container = QFrame()
        self._container.setProperty("frameType", "loading_container")
        container_layout = QVBoxLayout(self._container)
        container_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.setSpacing(12)

        self._label = QLabel(tr("mod_update_loading"))
        self._label.setProperty("labelType", "loading_label")
        font = self._label.font()
        font.setPointSize(get_calculated_font_size(self._base_font_size, FontSize.LARGE))
        self._label.setFont(font)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self._label)

        self._status_label = QLabel()
        self._status_label.setProperty("labelType", "status_label")
        font = self._status_label.font()
        font.setPointSize(get_calculated_font_size(self._base_font_size, FontSize.MEDIUM))
        self._status_label.setFont(font)
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        container_layout.addWidget(self._status_label)

        layout.addWidget(self._container)

    def show_overlay(self, message: str = None):
        if message:
            self._label.setText(message)
        self.show()
        self.raise_()

    def set_status(self, status: str):
        self._status_label.setText(status)

    def hide_overlay(self):
        self.hide()
