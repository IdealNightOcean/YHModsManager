import logging
from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QSplitter, QDialog, QStatusBar,
    QStackedWidget
)

from core import init_user_config
from core.config_manager import ConfigManager
from core.highlight_rule_manager import init_highlight_rule_manager
from core.manager_collection import get_manager_collection, init_manager_collection
from core.metadata_manager import GameMetadataManager, ModMetadataManager
from core.mod_filter_manager import init_mod_filter_manager
from core.mod_manager import ModManager
from core.mod_operations import ModOperations
from core.mod_parser import ModParser, create_mod_parser
from core.mod_service import ModService
from plugin_system import GamePaths, get_plugin_loader
from yh_mods_manager_sdk import ListType, Mod, ModProfile
from ui.dependency_lines import DependencyLinesWidget, DependencyLegendWidget
from ui.dialogs.game_settings_dialog import GameSettingsDialog
from ui.i18n import init_i18n, tr, Language
from ui.styles import apply_theme, get_ui_constant
from ui.theme_manager import get_theme_manager
from ui.toast_widget import ToastManager
from ui.views.mixins import (
    MenuMixin, ToolBarMixin, ProfileMixin, ModOperationsMixin,
    ListRefreshMixin, DependencyMixin, SelectionMixin, ContextMenuMixin,
    GameSwitchMixin, SaveImportMixin, UnsavedChangesMixin
)
from ui.views.mod_update_view import ModUpdateView
from ui.widgets import InfoPanel, ListPanel
from ui.widgets.mod_update_table import LoadingOverlay
from utils.debouncer import Debouncer
from utils.list_selection import ListSelectionManager
from utils.search import SearchDebouncer, StructuredSearchParser
from workers.scan_worker import ScanWorker

logger = logging.getLogger(__name__)


class MainWindow(
    MenuMixin,
    ToolBarMixin,
    ProfileMixin,
    ModOperationsMixin,
    ListRefreshMixin,
    DependencyMixin,
    SelectionMixin,
    ContextMenuMixin,
    GameSwitchMixin,
    SaveImportMixin,
    UnsavedChangesMixin,
    QMainWindow
):
    def __init__(self):
        super().__init__()

        loader = get_plugin_loader()
        available_games = []
        try:
            loader.initialize()
            available_games = loader.get_available_plugins()
        except Exception as e:
            logger.error(f"Plugin initialization failed: {e}")

        if available_games:
            temp_config = ConfigManager()
            last_game_id = temp_config.get_last_game()

            if last_game_id and last_game_id in available_games:
                loader.set_current_plugin(last_game_id)
            else:
                loader.set_current_plugin(available_games[0])

        self.game_adapter = loader.get_current_adapter()
        if self.game_adapter is None:
            logger.warning("No game plugin loaded, some features will be unavailable")

        self.config_manager = ConfigManager(game_adapter=self.game_adapter)

        self._game_metadata_manager = GameMetadataManager()
        self._mod_metadata_manager = ModMetadataManager()

        self.mod_manager = ModManager(self.config_manager)
        self.mod_service = ModService(self.mod_manager)

        self._highlight_rule_manager = init_highlight_rule_manager()
        self._mod_filter_manager = init_mod_filter_manager()

        user_config_dir = self.config_manager.config_dir

        saved_lang = self.config_manager.get_language()
        initial_language = None
        try:
            initial_language = Language(saved_lang)
        except ValueError:
            logger.debug(f"Invalid language setting: {saved_lang}, using default")

        self.i18n = init_i18n(user_config_dir, initial_language)
        self.user_config = init_user_config(user_config_dir)
        self.search_parser = StructuredSearchParser(self.user_config)

        theme_manager = get_theme_manager()

        init_manager_collection(
            config_manager=self.config_manager,
            mod_manager=self.mod_manager,
            game_metadata_manager=self._game_metadata_manager,
            mod_metadata_manager=self._mod_metadata_manager,
            highlight_rule_manager=self._highlight_rule_manager,
            mod_filter_manager=self._mod_filter_manager,
            i18n=self.i18n,
            theme_manager=theme_manager,
        )

        manager_collection = get_manager_collection()
        loader.initialize_feature_plugins(manager_collection)

        self.parser: Optional[ModParser] = None
        self.current_profile: Optional[ModProfile] = None
        self.current_profile_name: str = ""
        self._selection_manager = ListSelectionManager()
        self._selection_just_changed: bool = False
        self.scan_worker: Optional[ScanWorker] = None

        self.disabled_search_debouncer = SearchDebouncer(self._do_filter_disabled)
        self.enabled_search_debouncer = SearchDebouncer(self._do_filter_enabled)

        self._dependency_debouncer = Debouncer(
            self._do_update_dependency_lines,
            config_key="dependency_update_delay"
        )
        self._validate_debouncer = Debouncer(
            self._do_auto_validate_load_order,
            config_key="validate_delay"
        )

        self._cached_dependency_map: Dict[str, List[str]] = {}
        self._dependency_map_dirty: bool = True
        self._has_unsaved_changes: bool = False
        self._saved_enabled_order: List[str] = []

        self._init_ui()
        self._init_connections()
        self._load_settings()
        ToastManager.init(self, self.base_font_size)

        from plugin_system.plugin_events import get_event_bus as get_plugin_event_bus, PluginEventType
        get_plugin_event_bus().subscribe(PluginEventType.MOD_HIGHLIGHT_RULES_CHANGED, self._on_highlight_rules_changed)

    def _init_ui(self):
        self._update_window_title()
        min_width = get_ui_constant('main_window', 'min_width', 1200)
        min_height = get_ui_constant('main_window', 'min_height', 700)
        self.setMinimumSize(min_width, min_height)
        self.base_font_size = self.config_manager.get_font_size()
        self._create_menu_bar()
        self._create_tool_bar()
        self._create_central_widget()
        self._create_status_bar()
        self._init_mod_operations()
        self._update_save_import_action()

    def _create_central_widget(self):
        self._central_widget = QWidget()
        self.setCentralWidget(self._central_widget)

        main_layout = QVBoxLayout(self._central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        self._view_switcher = QStackedWidget()

        self._main_view = QWidget()
        main_view_layout = QVBoxLayout(self._main_view)
        main_view_layout.setContentsMargins(0, 0, 0, 0)
        main_view_layout.setSpacing(5)

        profile_bar = self._create_profile_bar()
        main_view_layout.addWidget(profile_bar)

        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        info_panel = self._create_info_panel()
        content_splitter.addWidget(info_panel)

        lists_splitter = QSplitter(Qt.Orientation.Horizontal)
        disabled_panel = self._create_disabled_panel()
        lists_splitter.addWidget(disabled_panel)
        enabled_panel = self._create_enabled_panel()
        lists_splitter.addWidget(enabled_panel)
        legend_panel = self._create_legend_panel()
        lists_splitter.addWidget(legend_panel)

        lists_splitter.setSizes(get_ui_constant('main_window', 'lists_splitter_sizes', [300, 500, 160]))
        lists_splitter.setStretchFactor(0, 1)
        lists_splitter.setStretchFactor(1, 1)
        lists_splitter.setStretchFactor(2, 0)
        content_splitter.addWidget(lists_splitter)

        content_splitter.setSizes(get_ui_constant('main_window', 'content_splitter_sizes', [400, 900]))
        content_splitter.setStretchFactor(0, 0)
        content_splitter.setStretchFactor(1, 1)
        main_view_layout.addWidget(content_splitter, 1)

        self._view_switcher.addWidget(self._main_view)

        self._mod_update_view = ModUpdateView(
            self.config_manager,
            self.mod_service,
            self.base_font_size
        )
        self._view_switcher.addWidget(self._mod_update_view)

        self._view_switcher.setCurrentWidget(self._main_view)
        main_layout.addWidget(self._view_switcher, 1)

        self._loading_overlay = LoadingOverlay(self.base_font_size, self._central_widget)
        self._loading_overlay.hide()

    def _create_disabled_panel(self) -> QWidget:
        self.disabled_panel = ListPanel(ListType.DISABLED, self.base_font_size)
        self.disabled_list = self.disabled_panel.get_list_widget()
        self.disabled_search = self.disabled_panel.search_input

        self.disabled_list.mods_moved.connect(self._on_mods_moved_to_disabled)
        self.disabled_list.items_dropped.connect(self._reorder_disabled_list)
        self.disabled_list.itemSelectionChanged.connect(lambda: self._on_selection_changed(self.disabled_list))
        self.disabled_list.itemClicked.connect(self._on_item_clicked)
        self.disabled_list.itemDoubleClicked.connect(self._on_disabled_double_click)
        self.disabled_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.disabled_list.customContextMenuRequested.connect(self._show_mod_context_menu)
        self.disabled_list.clear_selection_requested.connect(self._clear_selection)

        self.disabled_panel.enable_selected_clicked.connect(self._enable_selected_mods)
        self.disabled_panel.enable_all_clicked.connect(self._enable_all_mods)
        self.disabled_panel.search_changed.connect(self.disabled_search_debouncer.update)
        self.disabled_panel.type_filter_changed.connect(lambda: self._refresh_disabled_list())
        self.disabled_panel.filter_mode_changed.connect(lambda: self._refresh_disabled_list())
        return self.disabled_panel

    def _create_enabled_panel(self) -> QWidget:
        self.enabled_panel = ListPanel(ListType.ENABLED, self.base_font_size)
        self.enabled_list = self.enabled_panel.get_list_widget()
        self.enabled_search = self.enabled_panel.search_input

        self.enabled_list.mods_moved.connect(self._on_mods_moved_to_enabled)
        self.enabled_list.items_dropped.connect(self._reorder_enabled_list)
        self.enabled_list.itemSelectionChanged.connect(lambda: self._on_selection_changed(self.enabled_list))
        self.enabled_list.itemClicked.connect(self._on_item_clicked)
        self.enabled_list.itemDoubleClicked.connect(self._on_enabled_double_click)
        self.enabled_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.enabled_list.customContextMenuRequested.connect(self._show_mod_context_menu)
        self.enabled_list.clear_selection_requested.connect(self._clear_selection)

        self.enabled_panel.move_up_clicked.connect(self._move_mod_up)
        self.enabled_panel.move_down_clicked.connect(self._move_mod_down)
        self.enabled_panel.disable_selected_clicked.connect(self._disable_selected_mods)
        self.enabled_panel.disable_all_clicked.connect(self._disable_all_mods)
        self.enabled_panel.search_changed.connect(self.enabled_search_debouncer.update)
        self.enabled_panel.type_filter_changed.connect(lambda: self._refresh_enabled_list())
        self.enabled_panel.filter_mode_changed.connect(lambda: self._refresh_enabled_list())

        self.dependency_lines_widget = DependencyLinesWidget(self.enabled_list.viewport())
        self.dependency_lines_widget.set_list_widget(self.enabled_list)
        self.enabled_list.set_dependency_widget(self.dependency_lines_widget)
        self.dependency_lines_widget.setParent(self.enabled_list.viewport())
        self.dependency_lines_widget.show()

        QTimer.singleShot(100, self._init_dependency_lines_geometry)
        return self.enabled_panel

    def _create_legend_panel(self) -> QWidget:
        self.legend_widget = DependencyLegendWidget(base_font_size=self.base_font_size)
        self.legend_widget.legend_clicked.connect(self._on_legend_clicked)
        self.legend_widget.toggle_lines_requested.connect(self._toggle_dependency_lines)
        self.enabled_list.highlight_changed.connect(self._on_highlight_changed)
        self.dependency_lines_widget.colors_updated.connect(self._on_dependency_colors_updated)
        return self.legend_widget

    def _create_info_panel(self) -> QWidget:
        self.info_panel = InfoPanel(
            self.mod_manager,
            self.user_config,
            self.base_font_size,
            self.config_manager
        )
        self.info_panel.color_changed.connect(self._on_mod_color_changed)
        self.info_panel.tags_changed.connect(self._refresh_list_items)
        self.info_panel.custom_name_changed.connect(self._refresh_list_items)
        self.info_panel.locate_mod_requested.connect(self._locate_mod)
        self.info_panel.issues_ignored_changed.connect(self._on_issues_ignored_changed)
        return self.info_panel

    def _on_issues_ignored_changed(self):
        self._refresh_list_items()
        self._update_disable_list_statistics()
        self._update_enable_list_statistics()

    def _create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(tr("ready"))

    def _init_mod_operations(self):
        self._mod_operations = ModOperations(
            self.mod_service,
            self.enabled_list,
            self.disabled_list
        )

    def _init_connections(self):
        theme_manager = get_theme_manager()
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _on_theme_changed(self):
        apply_theme(QApplication.instance(), self.base_font_size)
        self.info_panel.refresh_theme()
        self._update_disable_list_statistics()
        self._update_enable_list_statistics()
        self._refresh_list_items()
        self._refresh_toolbar_button_styles()
        self.disabled_panel.refresh_styles()
        self.enabled_panel.refresh_styles()
        self.profile_bar.refresh_styles()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_loading_overlay') and self._loading_overlay.isVisible():
            self._loading_overlay.setGeometry(self._central_widget.rect())

    def _load_settings(self):
        from PyQt6.QtWidgets import QMessageBox

        if not self.game_adapter:
            QMessageBox.warning(
                self,
                tr("no_game_plugin_title"),
                tr("no_game_plugin_message")
            )
            return

        paths = self.config_manager.get_game_dir_paths_with_detection()

        game_id = self.game_adapter.game_id
        if game_id:
            self.config_manager.set_last_game(game_id)

        width, height = self.config_manager.get_window_size()
        self.resize(width, height)

        self._refresh_profiles()
        result = self.config_manager.restore_last_profile_with_fallback()
        if result:
            profile_name, profile = result
            self.profile_bar.set_profiles(list(self.config_manager.get_all_profiles().keys()), profile_name)
            self.current_profile = profile
            self.current_profile_name = profile_name

        if paths.game_dir_path:
            self.parser = create_mod_parser(
                self.game_adapter, paths,
                i18n=self.i18n
            )
            self._scan_mods()
        else:
            QTimer.singleShot(100, self._select_game_dir_path)

        QTimer.singleShot(500, self._check_startup_updates)

    def _check_startup_updates(self):
        from services.update_service import get_update_service
        from ui.dialogs.update_dialog import UpdateNotificationDialog, ChangelogDialog

        update_service = get_update_service()

        if update_service.check_update_complete_marker():
            changelog_dialog = ChangelogDialog(self, self.base_font_size, limit=1)
            changelog_dialog.setWindowTitle(tr("update_success_title"))
            changelog_dialog.exec()

        if self.config_manager.is_update_check_disabled():
            return

        has_update, update_info = update_service.check_for_updates()
        if has_update and update_info:
            dialog = UpdateNotificationDialog(update_info, self, self.base_font_size)
            dialog.update_now.connect(lambda: self._start_update_process(update_info))
            dialog.disable_check.connect(self._disable_update_check)
            dialog.exec()

    def _start_update_process(self, update_info):
        from ui.dialogs.update_dialog import UpdateCheckDialog
        dialog = UpdateCheckDialog(self, self.base_font_size)
        dialog.exec()

    def _disable_update_check(self):
        self.config_manager.set_update_check_disabled(True)

    def _select_game_dir_path(self):
        current_paths = GamePaths(
            game_dir_path=self.config_manager.get_game_dir_path(),
            workshop_dir_path=self.config_manager.get_workshop_dir_path(),
            game_config_dir_path=self.config_manager.get_config_dir_path(),
            local_mod_dir_path=self.config_manager.get_local_mod_dir_path(),
            custom_paths=self.config_manager.get_custom_paths()
        )
        dialog = GameSettingsDialog(current_paths, self, game_adapter=self.game_adapter,
                                    config_manager=self.config_manager)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_paths = dialog.get_paths()
            if new_paths:
                self.config_manager.set_game_dir_path(new_paths.game_dir_path)
                self.config_manager.set_workshop_dir_path(new_paths.workshop_dir_path)
                self.config_manager.set_game_config_dir_path(new_paths.game_config_dir_path)
                self.config_manager.set_local_mod_dir_path(new_paths.local_mod_dir_path)
                self.config_manager.set_custom_paths(new_paths.custom_paths)
                self._update_window_title()
                self._update_game_info_label()
                self._refresh_plugin_menu()
                self.parser = create_mod_parser(
                    self.game_adapter, new_paths,
                    i18n=self.i18n
                )
                self._scan_mods()

    def _scan_mods(self):
        from PyQt6.QtWidgets import QMessageBox

        if not self.parser:
            QMessageBox.warning(self, tr("error_title"), tr("msg_no_game_dir_path"))
            return
        if self.scan_worker and self.scan_worker.isRunning():
            return
        self.mod_manager.save_metadata()
        self._show_scan_loading()
        self.scan_worker = ScanWorker(self.parser)
        self.scan_worker.progress.connect(self._on_scan_progress)
        self.scan_worker.finished.connect(self._on_scan_finished)
        self.scan_worker.error.connect(self._on_scan_error)
        self.scan_worker.start()

    def _show_scan_loading(self):
        self._loading_overlay.setGeometry(self._central_widget.rect())
        self._loading_overlay.show_overlay(tr("scan_mods_loading"))
        self._loading_overlay.set_status(tr("scan_mods_scanning"))

    def _hide_scan_loading(self):
        self._loading_overlay.hide_overlay()

    def _on_scan_progress(self, message: str):
        self.status_bar.showMessage(message)
        self._loading_overlay.set_status(message)

    def _on_scan_error(self, error_msg: str):
        self._hide_scan_loading()
        from ui.toast_widget import ToastManager
        ToastManager.show(f"插件错误: {error_msg}")
        logger.error(f"Scan error: {error_msg}")

    def _on_scan_finished(self, mods: List[Mod]):
        self._hide_scan_loading()
        case_sensitive = self.game_adapter.is_case_sensitive_id() if self.game_adapter else False
        self.mod_manager.set_mods(mods, case_sensitive=case_sensitive)

        if self.parser:
            self.mod_manager.set_game_version(self.parser.game_version)

        if self.game_adapter:
            try:
                game_id = self.game_adapter.game_id

                paths = GamePaths(
                    game_dir_path=self.config_manager.get_game_dir_path(),
                    workshop_dir_path=self.config_manager.get_workshop_dir_path(),
                    game_config_dir_path=self.config_manager.get_config_dir_path(),
                    local_mod_dir_path=self.config_manager.get_local_mod_dir_path(),
                    game_version=self.parser.game_version if self.parser else ""
                )
                game_metadata = self.game_adapter.load_game_metadata(paths)
                manager_collection = get_manager_collection()
                game_metadata = self.game_adapter.update_game_metadata(game_metadata, manager_collection)
                self._game_metadata_manager.receive_metadata(game_id, game_metadata)
                self._game_metadata_manager.set_current_game(game_id)

                mods_metadata = []
                for mod in mods:
                    mod_metadata = self.game_adapter.load_mod_metadata(mod)
                    mod_metadata = self.game_adapter.update_mod_metadata(mod, mod_metadata, manager_collection)
                    mods_metadata.append(mod_metadata)
                self._mod_metadata_manager.receive_batch_metadata(game_id, mods_metadata)
                self._mod_metadata_manager.set_current_game(game_id)

                self.game_adapter.static_error_check(mods, game_metadata)

                for feature_plugin in get_plugin_loader().get_available_feature_plugins().values():
                    try:
                        feature_plugin.static_error_check(mods, game_metadata)
                    except Exception as e:
                        logger.error(f"Feature plugin static_error_check failed: {e}")
            except Exception as e:
                logger.error(f"Plugin metadata loading failed: {e}")

        if self.current_profile:
            self.mod_service.load_profile(self.current_profile)
        self._refresh_enabled_list()
        self._refresh_disabled_list()
        self._update_all_enabled_mods_status()
        self._auto_validate_load_order()
        self._update_status()
        self._update_game_info_label()
        QTimer.singleShot(100, self._init_dependency_lines_geometry)
        self._invalidate_dependency_cache()
        QTimer.singleShot(110, self._update_dependency_lines)
