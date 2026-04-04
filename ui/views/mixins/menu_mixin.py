import logging
from typing import Dict

from PyQt6.QtGui import QAction, QActionGroup
from PyQt6.QtWidgets import QMenu

from core.manager_collection import get_manager_collection
from plugin_system import get_plugin_loader
from ui.i18n import tr
from ui.toast_widget import ToastManager

logger = logging.getLogger(__name__)


class MenuMixin:
    _plugin_menu_actions: Dict[str, QAction]
    _feature_plugin_menu_actions: Dict[str, QAction]

    def _create_menu_bar(self):
        menubar = self.menuBar()

        self._game_action = None

        game_settings_action = QAction(tr("game_settings"), self)
        game_settings_action.triggered.connect(self._select_game_dir_path)
        menubar.addAction(game_settings_action)

        self._create_game_menu(menubar)

        profile_menu = menubar.addMenu(tr("menu_profile"))
        new_profile_action = QAction(tr("new_profile"), self)
        new_profile_action.triggered.connect(self._create_new_profile)
        profile_menu.addAction(new_profile_action)

        save_profile_action = QAction(tr("save_profile"), self)
        save_profile_action.triggered.connect(self._save_current_profile)
        profile_menu.addAction(save_profile_action)
        profile_menu.addSeparator()

        export_action = QAction(tr("export_profile"), self)
        export_action.triggered.connect(self._export_profile)
        profile_menu.addAction(export_action)

        import_action = QAction(tr("import_profile"), self)
        import_action.triggered.connect(self._import_profile)
        profile_menu.addAction(import_action)
        profile_menu.addSeparator()

        export_metadata_action = QAction(tr("export_mod_metadata"), self)
        export_metadata_action.triggered.connect(self._export_mod_metadata)
        profile_menu.addAction(export_metadata_action)

        import_metadata_action = QAction(tr("import_mod_metadata"), self)
        import_metadata_action.triggered.connect(self._import_mod_metadata)
        profile_menu.addAction(import_metadata_action)
        profile_menu.addSeparator()

        self.import_from_save_action = QAction(tr("import_from_save"), self)
        self.import_from_save_action.triggered.connect(self._import_from_save)
        profile_menu.addAction(self.import_from_save_action)

        self._plugin_menu = menubar.addMenu(tr("game_plugins"))
        self._plugin_menu_actions: Dict[str, QAction] = {}

        self._tools_menu = menubar.addMenu(tr("menu_tools"))
        self._feature_plugin_menu_actions: Dict[str, QAction] = {}

        settings_action = QAction(tr("settings"), self)
        settings_action.triggered.connect(self._show_settings_dialog)
        menubar.addAction(settings_action)

        help_menu = menubar.addMenu(tr("menu_help"))
        search_tags_action = QAction(tr("search_tags_title"), self)
        search_tags_action.triggered.connect(self._show_search_tags)
        help_menu.addAction(search_tags_action)
        help_menu.addSeparator()
        about_action = QAction(tr("about"), self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

        self._refresh_plugin_menu()
        self._refresh_feature_plugins_menu()

    def _create_game_menu(self, menubar):
        loader = get_plugin_loader()
        available_games = loader.get_available_plugins()

        current_game_id = ""
        current_game_name = ""
        if self.game_adapter:
            current_game_id = self.game_adapter.game_id
            game_info = self.game_adapter.get_game_info()
            default_name = game_info.default_name if game_info else current_game_id
            if self.config_manager:
                current_game_name = self.config_manager.get_game_display_name(current_game_id, default_name)
            else:
                current_game_name = default_name

        if len(available_games) <= 1:
            self._game_action = menubar.addAction(current_game_name if current_game_name else tr("switch_game"))
            self._game_action.setEnabled(False)
            return

        self._game_menu = menubar.addMenu(current_game_name if current_game_name else tr("switch_game"))
        self._game_action_group = None
        self._refresh_game_menu()

    def _refresh_game_menu(self):
        loader = get_plugin_loader()
        available_games = loader.get_available_plugins()

        current_game_id = ""
        current_game_name = ""
        if self.game_adapter:
            current_game_id = self.game_adapter.game_id
            game_info = self.game_adapter.get_game_info()
            default_name = game_info.default_name if game_info else current_game_id
            if self.config_manager:
                current_game_name = self.config_manager.get_game_display_name(current_game_id, default_name)
            else:
                current_game_name = default_name

        if len(available_games) <= 1:
            if self._game_action:
                self._game_action.setText(current_game_name if current_game_name else tr("switch_game"))
            return

        self._game_menu.setTitle(current_game_name if current_game_name else tr("switch_game"))
        self._game_menu.clear()

        if not available_games:
            no_games_action = self._game_menu.addAction(tr("no_available_tags"))
            no_games_action.setEnabled(False)
            return

        self._game_action_group = QActionGroup(self)
        self._game_action_group.setExclusive(True)

        for game_id in available_games:
            adapter = loader.get_adapter(game_id)
            if adapter:
                game_info = adapter.get_game_info()
                default_name = game_info.default_name if game_info else game_id
                if self.config_manager:
                    display_name = self.config_manager.get_game_display_name(game_id, default_name)
                else:
                    display_name = default_name
                game_action = self._game_menu.addAction(display_name)
                game_action.setCheckable(True)
                game_action.setChecked(game_id == current_game_id)
                game_action.setActionGroup(self._game_action_group)
                game_action.triggered.connect(lambda checked, gid=game_id: self._switch_game(gid))

    def _refresh_plugin_menu(self):
        self._plugin_menu.clear()
        self._plugin_menu_actions.clear()

        if not self.game_adapter:
            no_plugin_action = self._plugin_menu.addAction(tr("no_plugin_loaded"))
            no_plugin_action.setEnabled(False)
            return

        try:
            menu_items = self.game_adapter.get_menu_items()
        except Exception as e:
            logger.error(f"Failed to get plugin menu items: {e}")
            menu_items = []

        if not menu_items:
            no_menu_action = self._plugin_menu.addAction(tr("no_plugin_menu"))
            no_menu_action.setEnabled(False)
            return

        for item in menu_items:
            self._add_plugin_menu_item(self._plugin_menu, item)

    def _add_plugin_menu_item(self, parent_menu: QMenu, item):
        if item.separator_before:
            parent_menu.addSeparator()

        if item.submenu_items:
            submenu = parent_menu.addMenu(item.label)
            for sub_item in item.submenu_items:
                self._add_plugin_menu_item(submenu, sub_item)
        else:
            action = QAction(item.label, self)
            action.setEnabled(item.enabled)
            if item.shortcut:
                action.setShortcut(item.shortcut)

            action_id = item.action_id or item.id
            action.triggered.connect(lambda checked, aid=action_id: self._on_plugin_menu_action(aid))

            parent_menu.addAction(action)
            self._plugin_menu_actions[action_id] = action

    def _on_plugin_menu_action(self, action_id: str):
        if not self.game_adapter:
            return

        manager_collection = get_manager_collection()

        try:
            result = self.game_adapter.on_menu_action(action_id, manager_collection)
        except Exception as e:
            logger.error(f"Plugin menu action failed: {e}")
            ToastManager.show(f"插件操作失败: {e}")
            return

        if result:

            if result.data.get("refresh_mods"):
                self._scan_mods()
            if result.data.get("refresh_profiles"):
                self._refresh_profile_combo()
            if result.message:
                ToastManager.show(result.message)

    def _refresh_feature_plugins_menu(self):
        self._tools_menu.clear()
        self._feature_plugin_menu_actions.clear()

        loader = get_plugin_loader()
        feature_plugins = loader.get_available_feature_plugins()

        if not feature_plugins:
            no_plugins_action = self._tools_menu.addAction(tr("no_feature_plugins"))
            no_plugins_action.setEnabled(False)
            return

        for plugin_id, feature_plugin in feature_plugins.items():
            if not feature_plugin.is_initialized():
                continue

            menu_items = feature_plugin.get_menu_items()
            for item in menu_items:
                self._add_feature_plugin_menu_item(self._tools_menu, item, plugin_id)

    def _add_feature_plugin_menu_item(self, parent_menu: QMenu, item, plugin_id: str):
        if item.separator_before:
            parent_menu.addSeparator()

        if item.submenu_items:
            submenu = parent_menu.addMenu(item.label)
            for sub_item in item.submenu_items:
                self._add_feature_plugin_menu_item(submenu, sub_item, plugin_id)
        else:
            action = QAction(item.label, self)
            action.setEnabled(item.enabled)
            if item.shortcut:
                action.setShortcut(item.shortcut)

            action_id = item.action_id or item.id
            action.triggered.connect(
                lambda checked, aid=action_id, pid=plugin_id: self._on_feature_plugin_menu_action(pid, aid))

            parent_menu.addAction(action)
            self._feature_plugin_menu_actions[action_id] = action

    def _on_feature_plugin_menu_action(self, plugin_id: str, action_id: str):
        loader = get_plugin_loader()
        feature_plugin = loader.get_available_feature_plugins().get(plugin_id)

        if not feature_plugin:
            return

        manager_collection = get_manager_collection()

        try:
            result = feature_plugin.on_menu_action(action_id, manager_collection)
        except Exception as e:
            logger.error(f"Feature plugin menu action failed: {e}")
            ToastManager.show(f"功能插件操作失败: {e}")
            return

        if result:
            if result.data.get("message"):
                ToastManager.show(result.data.get("message"))
            if result.success and result.data.get("refresh_ui"):
                self._refresh_feature_plugins_menu()

    def _show_search_tags(self):
        from ui.dialogs.search_tags_dialog import SearchTagsDialog
        dialog = SearchTagsDialog(self, self.base_font_size)
        dialog.show()

    def _show_about(self):
        from ui.dialogs.about_dialog import AboutDialog
        dialog = AboutDialog(self, self.base_font_size)
        dialog.changelog_requested.connect(self._show_changelog)
        dialog.exec()

    def _show_changelog(self):
        from ui.dialogs.update_dialog import ChangelogDialog
        dialog = ChangelogDialog(self, self.base_font_size)
        dialog.exec()
