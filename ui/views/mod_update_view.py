"""
MOD更新管理界面
独立的MOD更新监控界面，展示MOD的更新状态
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

from PyQt6.QtCore import Qt, pyqtSignal, QThread, QTimer
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QStackedWidget, QApplication, QTableWidgetItem
)

from core.config_manager import ConfigManager
from core.event_bus import EventType, Event, get_event_bus
from core.mod_service import ModService
from yh_mods_manager_sdk import Mod, ModType
from yh_mods_manager_sdk import PlatformUtils
from services.steam_service import SteamAPIService, SteamModInfo, create_steam_service
from ui.i18n import tr
from ui.styles import get_calculated_font_size, FontSize, get_ui_constant
from ui.theme_manager import get_theme_manager
from ui.toast_widget import ToastManager
from ui.widgets.mod_update_table import ModUpdateTable, EmptyStateWidget, LoadingOverlay
from utils.file_utils import get_app_data_dir
from utils.mod_ui_utils import ModUIUtils

logger = logging.getLogger(__name__)


class TableDataRow:
    """表格行数据 - 在后台线程准备"""
    __slots__ = ['mod_id', 'display_name', 'local_time', 'local_time_text',
                 'steam_time', 'steam_time_text', 'mod_type', 'is_enabled']

    def __init__(self):
        self.mod_id: str = ""
        self.display_name: str = ""
        self.local_time: Optional[datetime] = None
        self.local_time_text: str = ""
        self.steam_time: Optional[datetime] = None
        self.steam_time_text: str = ""
        self.mod_type: ModType = ModType.LOCAL
        self.is_enabled: bool = False


class DataLoadWorker(QThread):
    """数据加载工作线程 - 在后台准备所有表格数据"""

    progress = pyqtSignal(str)
    data_ready = pyqtSignal(list, dict)
    error = pyqtSignal(str)

    def __init__(self, mods: List[Mod], steam_service: Optional[SteamAPIService],
                 fetch_steam: bool = True):
        super().__init__()
        self._mods = mods
        self._steam_service = steam_service
        self._fetch_steam = fetch_steam

    def run(self):
        try:
            self.progress.emit("collecting_local")
            local_times = self._collect_local_update_times()

            steam_info: Dict[str, SteamModInfo] = {}
            if self._fetch_steam and self._steam_service:
                workshop_ids = [mod.workshop_id for mod in self._mods
                                if mod.mod_type == ModType.WORKSHOP and mod.workshop_id]
                if workshop_ids:
                    self.progress.emit(f"fetching_steam:{len(workshop_ids)}")
                    steam_info = self._steam_service.fetch_mod_info(workshop_ids)

            rows = self._prepare_table_rows(local_times, steam_info)
            self.data_ready.emit(rows, steam_info)
        except Exception as e:
            logger.error(f"Error in DataLoadWorker.run: {e}", exc_info=True)
            self.error.emit(str(e))

    def _collect_local_update_times(self) -> Dict[str, datetime]:
        result = {}
        for mod in self._mods:
            if mod.path and os.path.exists(mod.path):
                try:
                    mtime = os.path.getmtime(mod.path)
                    result[mod.id] = datetime.fromtimestamp(mtime)
                except (OSError, IOError) as e:
                    logger.debug(f"Failed to get mtime for {mod.path}: {e}")
        return result

    def _prepare_table_rows(self, local_times: Dict[str, datetime],
                            steam_info: Dict[str, SteamModInfo]) -> List[TableDataRow]:
        rows = []

        for mod in self._mods:
            row = TableDataRow()
            row.mod_id = mod.id
            row.display_name = mod.display_name

            local_time = local_times.get(mod.id)
            row.local_time = local_time
            row.local_time_text = self._format_datetime(local_time) if local_time else ""

            if mod.workshop_id and mod.workshop_id in steam_info:
                steam_time = steam_info[mod.workshop_id].update_time
                row.steam_time = steam_time
                row.steam_time_text = self._format_datetime(steam_time) if steam_time else ""
            else:
                row.steam_time = None
                row.steam_time_text = ""

            row.mod_type = mod.mod_type
            row.is_enabled = mod.is_enabled
            rows.append(row)

        return rows

    @staticmethod
    def _format_datetime(dt: datetime) -> str:
        return dt.strftime("%Y-%m-%d %H:%M") if dt else ""


class ModUpdateView(QWidget):
    """MOD更新管理界面
    
    功能：
    1. 展示MOD更新状态列表
    2. 支持Steam创意工坊更新检测
    3. 响应主界面事件实现增量更新
    4. 支持游戏切换时数据清空
    """

    refresh_requested = pyqtSignal()

    def __init__(self, config_manager: ConfigManager, mod_service: ModService,
                 base_font_size: int = 12, parent=None):
        super().__init__(parent)
        self._config_manager = config_manager
        self._mod_service = mod_service
        self._base_font_size = base_font_size

        self._steam_service: Optional[SteamAPIService] = None
        self._data_worker: Optional[DataLoadWorker] = None
        self._is_data_loaded = False
        self._current_game_id: Optional[str] = None
        self._pending_mods: List[Mod] = []

        self._local_update_times: Dict[str, datetime] = {}
        self._steam_info: Dict[str, SteamModInfo] = {}

        self._pending_updates: List[Tuple[str, str, Any]] = []
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._process_pending_updates)

        self._pending_rows: List[TableDataRow] = []
        self._row_load_batch_size = 50
        self._row_load_timer = QTimer()
        self._row_load_timer.setSingleShot(True)
        self._row_load_timer.timeout.connect(self._load_next_row_batch)

        self._event_bus = get_event_bus()

        self._setup_ui()
        self._connect_signals()
        self._init_steam_service()

    def _setup_ui(self):
        min_width = get_ui_constant('mod_update_view', 'min_width', 800)
        min_height = get_ui_constant('mod_update_view', 'min_height', 500)
        self.setMinimumSize(min_width, min_height)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self._toolbar = self._create_toolbar()
        layout.addWidget(self._toolbar)

        self._stack = QStackedWidget()

        self._table = ModUpdateTable(self._base_font_size)
        self._table.open_local_folder_requested.connect(self._on_open_local_folder)
        self._table.open_workshop_requested.connect(self._on_open_workshop)
        self._table.copy_mod_name_requested.connect(self._on_copy_mod_name)
        self._table.copy_mod_id_requested.connect(self._on_copy_mod_id)
        self._stack.addWidget(self._table)

        self._empty_widget = EmptyStateWidget(self._base_font_size)
        self._stack.addWidget(self._empty_widget)

        self._stack.setCurrentWidget(self._empty_widget)
        layout.addWidget(self._stack, 1)

        self._loading_overlay = LoadingOverlay(self._base_font_size, self)
        self._loading_overlay.setGeometry(self.rect())
        self._loading_overlay.hide()

    def _create_toolbar(self) -> QWidget:
        toolbar = QWidget()
        toolbar.setProperty("widgetType", "update_toolbar")
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        self._refresh_btn = QPushButton(tr("mod_update_refresh"))
        self._refresh_btn.setProperty("buttonType", "standard")
        self._refresh_btn.clicked.connect(self._on_refresh_clicked)
        layout.addWidget(self._refresh_btn)

        layout.addStretch()

        self._steam_status_label = QLabel()
        self._update_steam_status_label()
        self._steam_status_label.setProperty("labelType", "steam_status")
        font = self._steam_status_label.font()
        font.setPointSize(get_calculated_font_size(self._base_font_size, FontSize.SMALL))
        self._steam_status_label.setFont(font)
        layout.addWidget(self._steam_status_label)

        return toolbar

    def _update_steam_status_label(self):
        if self._config_manager.is_steam_monitor_disabled():
            self._steam_status_label.setText(tr("mod_update_steam_disabled"))
        else:
            self._steam_status_label.setText(tr("mod_update_steam_enabled"))

    def _connect_signals(self):
        self._event_bus.subscribe(EventType.MOD_STATE_CHANGED, self._on_mod_state_changed)
        self._event_bus.subscribe(EventType.MOD_LOCAL_UPDATED, self._on_mod_local_updated)
        self._event_bus.subscribe(EventType.MOD_DELETED, self._on_mod_deleted)
        self._event_bus.subscribe(EventType.MOD_ADDED, self._on_mod_added)
        self._event_bus.subscribe(EventType.GAME_CHANGED, self._on_game_changed)

        theme_manager = get_theme_manager()
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _init_steam_service(self):
        cache_dir = self._get_cache_dir()
        self._steam_service = create_steam_service(cache_dir)

    @staticmethod
    def _get_cache_dir() -> str:
        app_dir = get_app_data_dir()
        cache_dir = os.path.join(app_dir, 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir

    def _on_theme_changed(self):
        self._table.apply_style()
        self._update_steam_status_label()
        self._toolbar.style().unpolish(self._toolbar)
        self._toolbar.style().polish(self._toolbar)

    def set_current_game(self, game_id: str):
        if self._current_game_id != game_id:
            self._current_game_id = game_id
            self._is_data_loaded = False
            self._table.clear_data()
            self._local_update_times.clear()
            self._steam_info.clear()
            self._stack.setCurrentWidget(self._empty_widget)
            self._update_status(tr("mod_update_status_ready"))

    def load_data(self):
        if self._is_data_loaded:
            logger.debug("Data already loaded, skipping")
            return

        logger.info("Starting load_data")
        self._show_loading()
        self._update_status(tr("mod_update_loading"))

        QTimer.singleShot(10, self._load_mods_async)

    def _load_mods_async(self):
        logger.debug("In _load_mods_async")
        try:
            mods = self._mod_service.all_mods
            logger.info(f"Got {len(mods) if mods else 0} mods")

            if not mods:
                self._stack.setCurrentWidget(self._empty_widget)
                self._update_status(tr("mod_update_empty"))
                self._hide_loading()
                return

            logger.debug("Starting data worker")
            QTimer.singleShot(10, lambda: self._start_data_worker(mods))
        except Exception as e:
            logger.error(f"Error in _load_mods_async: {e}")
            self._hide_loading()
            self._update_status(f"Error: {e}")

    def _start_data_worker(self, mods: List[Mod]):
        logger.debug(f"_start_data_worker called with {len(mods)} mods")

        if self._data_worker is not None:
            try:
                if self._data_worker.isRunning():
                    logger.debug("Previous worker still running, scheduling deletion")
                    self._data_worker.finished.connect(self._data_worker.deleteLater)
            except RuntimeError:
                logger.debug("Previous worker already deleted")
            finally:
                self._data_worker = None

        fetch_steam = not self._config_manager.is_steam_monitor_disabled()
        logger.debug(f"Fetch steam: {fetch_steam}")
        self._pending_mods = mods
        self._data_worker = DataLoadWorker(mods, self._steam_service, fetch_steam)
        self._data_worker.progress.connect(self._on_worker_progress)
        self._data_worker.data_ready.connect(self._on_data_ready)
        self._data_worker.error.connect(self._on_worker_error)
        self._data_worker.finished.connect(self._on_worker_finished)
        logger.debug("Starting worker thread")
        self._data_worker.start()
        logger.debug(f"Worker thread started, isRunning: {self._data_worker.isRunning()}")

    def _on_worker_finished(self):
        logger.debug("Worker finished")
        sender = self.sender()
        if sender:
            sender.deleteLater()
        self._data_worker = None

    def _on_worker_progress(self, message: str):
        logger.debug(f"Worker progress: {message}")
        if message == "collecting_local":
            self._update_status(tr("mod_update_collecting_local"))
        elif message.startswith("fetching_steam:"):
            count = message.split(":")[1]
            self._update_status(tr("mod_update_fetching_steam").format(count))
        else:
            self._update_status(message)

    def _on_data_ready(self, rows: List[TableDataRow], steam_info: Dict[str, SteamModInfo]):
        logger.info(f"Data ready: {len(rows)} rows")
        self._steam_info = steam_info

        if len(rows) <= self._row_load_batch_size:
            self._table.set_rows_data(rows)
            self._stack.setCurrentWidget(self._table)
            self._is_data_loaded = True
            self._hide_loading()
            self._update_status(tr("mod_update_status_loaded").format(len(rows)))
        else:
            self._pending_rows = rows
            self._table.setRowCount(0)
            self._table.setEnabled(True)
            self._stack.setCurrentWidget(self._table)
            self._update_status(tr("mod_update_loading"))
            QTimer.singleShot(10, self._load_next_row_batch)

    def _load_next_row_batch(self):
        if not self._pending_rows:
            self._is_data_loaded = True
            self._hide_loading()
            self._update_status(tr("mod_update_status_loaded").format(self._table.rowCount()))
            if self._table.is_first_load:
                self._table.sortByColumn(self._table.COLUMN_LOCAL_UPDATE, Qt.SortOrder.DescendingOrder)
                self._table.current_sort_column = self._table.COLUMN_LOCAL_UPDATE
                self._table.current_sort_order = False
                self._table.is_first_load = False
            else:
                self._table.sortByColumn(self._table.current_sort_column,
                                         Qt.SortOrder.AscendingOrder if self._table.current_sort_order else Qt.SortOrder.DescendingOrder)
            return

        batch = self._pending_rows[:self._row_load_batch_size]
        self._pending_rows = self._pending_rows[self._row_load_batch_size:]

        logger.debug(f"Loading batch of {len(batch)} rows, {len(self._pending_rows)} remaining")

        self._table.setUpdatesEnabled(False)
        try:
            type_map = {
                ModType.CORE: tr("mod_type_core"),
                ModType.DLC: tr("mod_type_dlc"),
                ModType.WORKSHOP: tr("mod_type_workshop"),
                ModType.LOCAL: tr("mod_type_local")
            }

            start_row = self._table.rowCount()
            self._table.setRowCount(start_row + len(batch))

            for idx, row_data in enumerate(batch):
                row_idx = start_row + idx

                self._table.mod_types[row_data.mod_id] = row_data.mod_type

                name_item = QTableWidgetItem(row_data.display_name)
                name_item.setData(Qt.ItemDataRole.UserRole, row_data.mod_id)
                self._table.setItem(row_idx, 0, name_item)

                local_text = row_data.local_time_text if row_data.local_time_text else tr("mod_update_unknown")
                local_item = QTableWidgetItem(local_text)
                local_item.setData(Qt.ItemDataRole.UserRole,
                                   row_data.local_time.timestamp() if row_data.local_time else 0)
                self._table.setItem(row_idx, 1, local_item)

                steam_text = row_data.steam_time_text if row_data.steam_time_text else "--"
                steam_item = QTableWidgetItem(steam_text)
                steam_item.setData(Qt.ItemDataRole.UserRole, row_data.steam_time)
                self._table.setItem(row_idx, 2, steam_item)

                type_text = type_map.get(row_data.mod_type, tr("mod_type_local"))
                type_item = QTableWidgetItem(type_text)
                self._table.setItem(row_idx, 3, type_item)

                enabled_text = tr("yes") if row_data.is_enabled else tr("no")
                enabled_item = QTableWidgetItem(enabled_text)
                enabled_item.setData(Qt.ItemDataRole.UserRole, row_data.is_enabled)
                self._table.setItem(row_idx, 4, enabled_item)
        finally:
            self._table.setUpdatesEnabled(True)

        self._update_status(
            tr("mod_update_loading") + f" ({self._table.rowCount()} / {self._table.rowCount() + len(self._pending_rows)})")

        self._row_load_timer.start(10)

    def _on_worker_error(self, error: str):
        logger.error(f"Worker error: {error}")
        self._hide_loading()
        self._update_status(tr("mod_update_status_steam_error").format(error))

    def _show_loading(self):
        self._loading_overlay.setGeometry(self.rect())
        self._loading_overlay.show_overlay(tr("mod_update_loading"))

    def _hide_loading(self):
        self._loading_overlay.hide_overlay()

    def _on_refresh_clicked(self):
        self._is_data_loaded = False
        self._steam_info.clear()
        self.load_data()

    def _on_open_local_folder(self, mod_id: str):
        mod = self._mod_service.get_mod_by_id(mod_id)
        ModUIUtils.open_mod_folder(mod)

    def _on_open_workshop(self, mod_id: str):
        mod = self._mod_service.get_mod_by_id(mod_id)
        if mod and mod.workshop_id:
            PlatformUtils.open_workshop_page(mod.workshop_id)

    def _on_copy_mod_name(self, mod_id: str):
        mod = self._mod_service.get_mod_by_id(mod_id)
        if mod:
            clipboard = QApplication.clipboard()
            clipboard.setText(mod.name)
            ToastManager.show(tr("copied_to_clipboard").format(mod.name))

    @staticmethod
    def _on_copy_mod_id(mod_id: str):
        clipboard = QApplication.clipboard()
        clipboard.setText(mod_id)
        ToastManager.show(tr("copied_to_clipboard").format(mod_id))

    def _on_mod_state_changed(self, event: Event):
        if event.mod_id:
            self._pending_updates.append(('state', event.mod_id, event.data.get("is_enabled", False)))
            self._schedule_update()

    def _on_mod_local_updated(self, event: Event):
        if event.mod_id:
            self._pending_updates.append(('local_time', event.mod_id, datetime.now()))
            self._schedule_update()

    def _on_mod_deleted(self, event: Event):
        if event.mod_id:
            self._pending_updates.append(('delete', event.mod_id, None))
            self._schedule_update()

    def _on_mod_added(self, event: Event):
        if event.mod_id:
            self._pending_updates.append(('add', event.mod_id, None))
            self._schedule_update()

    def _schedule_update(self):
        if not self._update_timer.isActive():
            self._update_timer.start(50)

    def _process_pending_updates(self):
        if not self._pending_updates:
            return

        updates_by_mod = {}
        for update_type, mod_id, data in self._pending_updates:
            if mod_id not in updates_by_mod:
                updates_by_mod[mod_id] = {}
            updates_by_mod[mod_id][update_type] = data

        self._pending_updates.clear()

        for mod_id, updates in updates_by_mod.items():
            if 'delete' in updates:
                self._table.remove_mod(mod_id)
                self._update_status(tr("mod_update_status_mod_removed").format(mod_id))
                continue

            if 'add' in updates:
                mod = self._mod_service.get_mod_by_id(mod_id)
                if mod:
                    local_time = None
                    if mod.path and os.path.exists(mod.path):
                        try:
                            mtime = os.path.getmtime(mod.path)
                            local_time = datetime.fromtimestamp(mtime)
                        except (OSError, IOError) as e:
                            logger.debug(f"Failed to get mtime for {mod.path}: {e}")
                    self._table.add_mod(mod, local_time)
                    self._stack.setCurrentWidget(self._table)

            if 'state' in updates:
                self._table.update_mod_state(mod_id, updates['state'])

            if 'local_time' in updates:
                self._table.update_mod_local_time(mod_id, updates['local_time'])

    def _on_game_changed(self, event: Event):
        if event.game_id:
            self.set_current_game(event.game_id)
            if self.isVisible():
                self.load_data()

    def _update_status(self, message: str):
        self._loading_overlay.set_status(message)

    def on_steam_monitor_setting_changed(self, disabled: bool):
        self._update_steam_status_label()
        self._table.set_steam_monitor_enabled(not disabled)

        if not disabled and self._is_data_loaded:
            mods = self._mod_service.all_mods
            if mods:
                self._start_data_worker(mods)

    def refresh_theme(self):
        self._table.apply_style()
        self._update_steam_status_label()
        self._toolbar.style().unpolish(self._toolbar)
        self._toolbar.style().polish(self._toolbar)

    def cleanup(self):
        self._event_bus.unsubscribe(EventType.MOD_STATE_CHANGED, self._on_mod_state_changed)
        self._event_bus.unsubscribe(EventType.MOD_LOCAL_UPDATED, self._on_mod_local_updated)
        self._event_bus.unsubscribe(EventType.MOD_DELETED, self._on_mod_deleted)
        self._event_bus.unsubscribe(EventType.MOD_ADDED, self._on_mod_added)
        self._event_bus.unsubscribe(EventType.GAME_CHANGED, self._on_game_changed)

        if self._update_timer.isActive():
            self._update_timer.stop()

        if self._row_load_timer.isActive():
            self._row_load_timer.stop()

        self._pending_rows.clear()

        if self._data_worker is not None:
            try:
                if self._data_worker.isRunning():
                    self._data_worker.terminate()
                    self._data_worker.wait()
            except RuntimeError as e:
                logger.debug(f"Worker termination error: {e}")
            finally:
                self._data_worker = None
