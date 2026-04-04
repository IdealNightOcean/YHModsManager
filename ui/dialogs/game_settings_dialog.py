import os
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QFileDialog, QMessageBox, QWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QAbstractItemView
)

from plugin_system import GamePaths, get_plugin_loader
from yh_mods_manager_sdk import PlatformUtils, StatusType
from utils.steam_detector import SteamDetector
from ..i18n import tr
from ..styles import refresh_widget_style


class GameSettingsDialog(QDialog):
    def __init__(self, current_paths: GamePaths, parent=None, game_adapter=None, config_manager=None):
        super().__init__(parent)
        self.game_dir_paths = current_paths
        self.result_paths: Optional[GamePaths] = None
        self._game_adapter = game_adapter or get_plugin_loader().get_current_adapter()
        self._config_manager = config_manager

        self.setWindowTitle(tr("game_settings"))
        self.setMinimumWidth(750)
        self.setMinimumHeight(850)

        self._init_ui()
        self._load_current_paths()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        layout.addWidget(self._create_game_name_section())

        layout.addWidget(self._create_auto_detect_section())

        layout.addWidget(self._create_game_dir_path_section())

        layout.addWidget(self._create_local_mods_section())

        layout.addWidget(self._create_workshop_dir_path_section())

        layout.addWidget(self._create_game_config_dir_path_section())

        layout.addWidget(self._create_default_save_dir_path_section())

        layout.addWidget(self._create_custom_paths_section(), 1)

        layout.addLayout(self._create_button_layout())

    def _create_game_name_section(self) -> QWidget:
        group = QGroupBox(tr("game_name"))
        layout = QHBoxLayout(group)

        layout.addWidget(QLabel(tr("game_name")))

        self.game_name_edit = QLineEdit()
        self.game_name_edit.setPlaceholderText(tr("game_name_placeholder"))

        default_name = ""
        if self._game_adapter:
            game_info = self._game_adapter.get_game_info()
            if game_info:
                default_name = game_info.default_name
        self.game_name_edit.setText(default_name)
        layout.addWidget(self.game_name_edit, 1)

        reset_btn = QPushButton(tr("reset"))
        reset_btn.clicked.connect(self._reset_game_name)
        layout.addWidget(reset_btn)

        return group

    def _reset_game_name(self):
        if self._game_adapter:
            game_info = self._game_adapter.get_game_info()
            if game_info:
                self.game_name_edit.setText(game_info.default_name)
                return
        self.game_name_edit.clear()

    def _create_auto_detect_section(self) -> QWidget:
        group = QGroupBox(tr("auto_detect"))
        layout = QHBoxLayout(group)

        self.auto_detect_btn = QPushButton(tr("auto_detect_steam"))
        self.auto_detect_btn.clicked.connect(self._auto_detect_paths)
        layout.addWidget(self.auto_detect_btn)

        self.detect_status = QLabel("")
        layout.addWidget(self.detect_status)
        layout.addStretch()

        return group

    def _create_game_dir_path_section(self) -> QWidget:
        group = QGroupBox(tr("game_dir_path_title"))
        layout = QHBoxLayout(group)

        layout.addWidget(QLabel(tr("path")))

        self.game_dir_path_edit = QLineEdit()
        self.game_dir_path_edit.setPlaceholderText(tr("game_dir_path"))
        layout.addWidget(self.game_dir_path_edit, 1)

        open_btn = QPushButton(tr("open_menu"))
        open_btn.clicked.connect(self._open_game_dir_path)
        layout.addWidget(open_btn)

        browse_btn = QPushButton(tr("browse") + "...")
        browse_btn.clicked.connect(self._browse_game_dir_path)
        layout.addWidget(browse_btn)

        validate_btn = QPushButton(tr("validate"))
        validate_btn.clicked.connect(self._validate_game_dir_path)
        layout.addWidget(validate_btn)

        self.game_dir_path_status = QLabel("")
        layout.addWidget(self.game_dir_path_status)

        return group

    def _create_workshop_dir_path_section(self) -> QWidget:
        group = QGroupBox(tr("workshop_dir_path_title"))
        layout = QHBoxLayout(group)

        layout.addWidget(QLabel(tr("path")))

        self.workshop_dir_path_edit = QLineEdit()
        self.workshop_dir_path_edit.setPlaceholderText(tr("workshop_dir_path_placeholder"))
        layout.addWidget(self.workshop_dir_path_edit, 1)

        open_btn = QPushButton(tr("open_menu"))
        open_btn.clicked.connect(self._open_workshop_dir_path)
        layout.addWidget(open_btn)

        browse_btn = QPushButton(tr("browse") + "...")
        browse_btn.clicked.connect(self._browse_workshop_dir_path)
        layout.addWidget(browse_btn)

        self.workshop_dir_path_status = QLabel("")
        layout.addWidget(self.workshop_dir_path_status)

        return group

    def _create_game_config_dir_path_section(self) -> QWidget:
        group = QGroupBox(tr("game_config_dir_path_title"))
        layout = QHBoxLayout(group)

        layout.addWidget(QLabel(tr("path")))

        self.game_config_dir_path_edit = QLineEdit()
        self.game_config_dir_path_edit.setPlaceholderText(tr("game_config_dir_path_placeholder"))
        layout.addWidget(self.game_config_dir_path_edit, 1)

        open_btn = QPushButton(tr("open_menu"))
        open_btn.clicked.connect(self._open_game_config_dir_path)
        layout.addWidget(open_btn)

        browse_btn = QPushButton(tr("browse") + "...")
        browse_btn.clicked.connect(self._browse_game_config_dir_path)
        layout.addWidget(browse_btn)

        self.game_config_dir_path_status = QLabel("")
        layout.addWidget(self.game_config_dir_path_status)

        return group

    def _create_default_save_dir_path_section(self) -> QWidget:
        group = QGroupBox(tr("default_save_dir_path"))
        layout = QHBoxLayout(group)

        layout.addWidget(QLabel(tr("path")))

        self.default_save_dir_path_edit = QLineEdit()
        self.default_save_dir_path_edit.setPlaceholderText(tr("default_save_dir_path_placeholder"))
        layout.addWidget(self.default_save_dir_path_edit, 1)

        open_btn = QPushButton(tr("open_menu"))
        open_btn.clicked.connect(self._open_default_save_dir_path)
        layout.addWidget(open_btn)
        browse_btn = QPushButton(tr("browse") + "...")
        browse_btn.clicked.connect(self._browse_default_save_dir_path)
        layout.addWidget(browse_btn)
        self.default_save_dir_path_status = QLabel("")
        layout.addWidget(self.default_save_dir_path_status)
        return group

    def _create_local_mods_section(self) -> QWidget:
        group = QGroupBox(tr("local_mod_dir_path_title"))
        layout = QHBoxLayout(group)

        layout.addWidget(QLabel(tr("path")))

        self.local_mod_dir_path_edit = QLineEdit()
        self.local_mod_dir_path_edit.setPlaceholderText(tr("local_mod_dir_path_placeholder"))
        layout.addWidget(self.local_mod_dir_path_edit, 1)

        open_btn = QPushButton(tr("open_menu"))
        open_btn.clicked.connect(self._open_local_mod_dir_path)
        layout.addWidget(open_btn)

        browse_btn = QPushButton(tr("browse") + "...")
        browse_btn.clicked.connect(self._browse_local_mod_dir_path)
        layout.addWidget(browse_btn)

        self.local_mod_dir_path_status = QLabel("")
        layout.addWidget(self.local_mod_dir_path_status)

        return group

    def _create_custom_paths_section(self) -> QWidget:
        group = QGroupBox(tr("custom_paths_title"))
        layout = QVBoxLayout(group)

        self.custom_paths_table = QTableWidget()
        self.custom_paths_table.setColumnCount(2)
        self.custom_paths_table.setHorizontalHeaderLabels([tr("custom_path_key"), tr("custom_path_value")])
        self.custom_paths_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.custom_paths_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.custom_paths_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.custom_paths_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.custom_paths_table.verticalHeader().setVisible(False)
        layout.addWidget(self.custom_paths_table)

        btn_layout = QHBoxLayout()

        add_btn = QPushButton(tr("add_custom_path"))
        add_btn.clicked.connect(self._add_custom_path)
        btn_layout.addWidget(add_btn)

        open_btn = QPushButton(tr("open_selected"))
        open_btn.clicked.connect(self._open_custom_path)
        btn_layout.addWidget(open_btn)

        edit_btn = QPushButton(tr("edit"))
        edit_btn.clicked.connect(self._edit_custom_path)
        btn_layout.addWidget(edit_btn)

        remove_btn = QPushButton(tr("remove_selected"))
        remove_btn.clicked.connect(self._remove_custom_path)
        btn_layout.addWidget(remove_btn)

        btn_layout.addStretch()

        layout.addLayout(btn_layout)

        return group

    def _create_button_layout(self) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.addStretch()

        ok_btn = QPushButton(tr("ok"))
        ok_btn.clicked.connect(self._accept_settings)
        layout.addWidget(ok_btn)

        cancel_btn = QPushButton(tr("cancel"))
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        return layout

    def _load_current_paths(self):
        if self._config_manager:
            custom_name = self._config_manager.get_custom_game_name()
            if custom_name:
                self.game_name_edit.setText(custom_name)

        if self.game_dir_paths.game_dir_path:
            self.game_dir_path_edit.setText(self.game_dir_paths.game_dir_path)

        if self.game_dir_paths.local_mod_dir_path:
            self.local_mod_dir_path_edit.setText(self.game_dir_paths.local_mod_dir_path)

        if self.game_dir_paths.workshop_dir_path:
            self.workshop_dir_path_edit.setText(self.game_dir_paths.workshop_dir_path)

        if self.game_dir_paths.game_config_dir_path:
            self.game_config_dir_path_edit.setText(self.game_dir_paths.game_config_dir_path)

        if self.game_dir_paths.default_save_dir_path:
            self.default_save_dir_path_edit.setText(self.game_dir_paths.default_save_dir_path)

        self._load_custom_paths_to_table()

    def _load_custom_paths_to_table(self):
        self.custom_paths_table.setRowCount(0)
        for key, path in self.game_dir_paths.custom_paths.items():
            row = self.custom_paths_table.rowCount()
            self.custom_paths_table.insertRow(row)
            self.custom_paths_table.setItem(row, 0, QTableWidgetItem(key))
            self.custom_paths_table.setItem(row, 1, QTableWidgetItem(path))

    def _add_custom_path(self):
        dialog = CustomPathDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            key, path = dialog.get_values()
            if key and path:
                self.game_dir_paths.custom_paths[key] = path
                self._load_custom_paths_to_table()

    def _edit_custom_path(self):
        current_row = self.custom_paths_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, tr("info"), tr("select_row_first"))
            return

        key_item = self.custom_paths_table.item(current_row, 0)
        path_item = self.custom_paths_table.item(current_row, 1)
        if not key_item or not path_item:
            return

        old_key = key_item.text()
        old_path = path_item.text()

        dialog = CustomPathDialog(self, old_key, old_path)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_key, new_path = dialog.get_values()
            if new_key and new_path:
                if old_key != new_key and old_key in self.game_dir_paths.custom_paths:
                    del self.game_dir_paths.custom_paths[old_key]
                self.game_dir_paths.custom_paths[new_key] = new_path
                self._load_custom_paths_to_table()

    def _remove_custom_path(self):
        current_row = self.custom_paths_table.currentRow()
        if current_row < 0:
            return

        key_item = self.custom_paths_table.item(current_row, 0)
        if key_item:
            key = key_item.text()
            if key in self.game_dir_paths.custom_paths:
                del self.game_dir_paths.custom_paths[key]
                self._load_custom_paths_to_table()

    def _open_path_with_check(self, path: str) -> bool:
        """检查路径并打开，返回是否成功"""
        if not path:
            QMessageBox.warning(self, tr("error_title"), tr("path_empty"))
            return False
        if not os.path.exists(path):
            QMessageBox.warning(self, tr("error_title"), tr("path_not_exist"))
            return False
        PlatformUtils.open_path(path)
        return True

    def _open_game_dir_path(self):
        self._open_path_with_check(self.game_dir_path_edit.text().strip())

    def _open_workshop_dir_path(self):
        self._open_path_with_check(self.workshop_dir_path_edit.text().strip())

    def _open_game_config_dir_path(self):
        self._open_path_with_check(self.game_config_dir_path_edit.text().strip())

    def _open_local_mod_dir_path(self):
        self._open_path_with_check(self.local_mod_dir_path_edit.text().strip())

    def _open_default_save_dir_path(self):
        self._open_path_with_check(self.default_save_dir_path_edit.text().strip())

    def _open_custom_path(self):
        current_row = self.custom_paths_table.currentRow()
        if current_row < 0:
            return

        path_item = self.custom_paths_table.item(current_row, 1)
        if not path_item:
            return
        path = path_item.text()
        if not path:
            QMessageBox.warning(self, tr("error_title"), tr("path_empty"))
            return
        if not os.path.exists(path):
            QMessageBox.warning(self, tr("error_title"), tr("path_not_exist"))
            return
        PlatformUtils.open_path(path)

    def _auto_detect_paths(self):
        from plugin_system import GamePaths

        if self._game_adapter:
            detector = self._game_adapter.create_detector()
            detected = detector.detect_game_dir_paths()
        else:
            detected = GamePaths()

        if detected.game_dir_path:
            self.game_dir_path_edit.setText(detected.game_dir_path)
            self.game_dir_path_status.setText("✓ " + tr("detected"))
            self.game_dir_path_status.setProperty("statusType", StatusType.SUCCESS.value)
        else:
            self.game_dir_path_status.setText("✗ " + tr("not_detected"))
            self.game_dir_path_status.setProperty("statusType", StatusType.ERROR.value)
        refresh_widget_style(self.game_dir_path_status)

        if detected.local_mod_dir_path:
            self.local_mod_dir_path_edit.setText(detected.local_mod_dir_path)
            self.local_mod_dir_path_status.setText("✓ " + tr("detected"))
            self.local_mod_dir_path_status.setProperty("statusType", StatusType.SUCCESS.value)
        else:
            self.local_mod_dir_path_status.setText("— " + tr("not_detected"))
            self.local_mod_dir_path_status.setProperty("statusType", StatusType.DISABLED.value)
        refresh_widget_style(self.local_mod_dir_path_status)

        if detected.workshop_dir_path:
            self.workshop_dir_path_edit.setText(detected.workshop_dir_path)
            self.workshop_dir_path_status.setText("✓ " + tr("detected"))
            self.workshop_dir_path_status.setProperty("statusType", StatusType.SUCCESS.value)
        else:
            self.workshop_dir_path_status.setText("— " + tr("not_detected"))
            self.workshop_dir_path_status.setProperty("statusType", StatusType.DISABLED.value)
        refresh_widget_style(self.workshop_dir_path_status)

        if detected.game_config_dir_path:
            self.game_config_dir_path_edit.setText(detected.game_config_dir_path)
            self.game_config_dir_path_status.setText("✓ " + tr("detected"))
            self.game_config_dir_path_status.setProperty("statusType", StatusType.SUCCESS.value)
        else:
            self.game_config_dir_path_status.setText("— " + tr("not_detected"))
            self.game_config_dir_path_status.setProperty("statusType", StatusType.DISABLED.value)
        refresh_widget_style(self.game_config_dir_path_status)

        if detected.default_save_dir_path:
            self.default_save_dir_path_edit.setText(detected.default_save_dir_path)
            self.default_save_dir_path_status.setText("✓ " + tr("detected"))
            self.default_save_dir_path_status.setProperty("statusType", StatusType.SUCCESS.value)
        else:
            self.default_save_dir_path_status.setText("— " + tr("not_detected"))
            self.default_save_dir_path_status.setProperty("statusType", StatusType.DISABLED.value)
        refresh_widget_style(self.default_save_dir_path_status)

        libraries_info = SteamDetector.get_steam_libraries_info()
        if libraries_info:
            self.detect_status.setText(tr("steam_libraries_detected").format(len(libraries_info)))
        else:
            self.detect_status.setText(tr("steam_not_detected"))

    def _browse_game_dir_path(self):
        folder = QFileDialog.getExistingDirectory(self, tr("game_dir_path"))
        if folder:
            self.game_dir_path_edit.setText(folder)
            self._validate_game_dir_path()

    def _browse_workshop_dir_path(self):
        folder = QFileDialog.getExistingDirectory(self, tr("workshop_dir_path"))
        if folder:
            self.workshop_dir_path_edit.setText(folder)

    def _browse_game_config_dir_path(self):
        folder = QFileDialog.getExistingDirectory(self, tr("game_config_dir_path_title"))
        if folder:
            self.game_config_dir_path_edit.setText(folder)
            self._validate_game_config_dir_path()

    def _browse_default_save_dir_path(self):
        folder = QFileDialog.getExistingDirectory(self, tr("default_save_dir_path_title"))
        if folder:
            self.default_save_dir_path_edit.setText(folder)
            self._validate_default_save_dir_path()

    def _validate_game_config_dir_path(self):
        path = self.game_config_dir_path_edit.text().strip()
        if not path:
            self.game_config_dir_path_status.setText("— " + tr("optional"))
            self.game_config_dir_path_status.setProperty("statusType", StatusType.DISABLED.value)
            refresh_widget_style(self.game_config_dir_path_status)
            return True

        if os.path.isdir(path):
            self.game_config_dir_path_status.setText("✓ " + tr("valid"))
            self.game_config_dir_path_status.setProperty("statusType", StatusType.SUCCESS.value)
            refresh_widget_style(self.game_config_dir_path_status)
            return True
        else:
            self.game_config_dir_path_status.setText("✗ " + tr("invalid"))
            self.game_config_dir_path_status.setProperty("statusType", StatusType.ERROR.value)
            refresh_widget_style(self.game_config_dir_path_status)
            return False

    def _validate_default_save_dir_path(self):
        path = self.default_save_dir_path_edit.text().strip()
        if not path:
            self.default_save_dir_path_edit.setText("— " + tr("optional"))
            self.default_save_dir_path_edit.setProperty("statusType", StatusType.DISABLED.value)
            refresh_widget_style(self.default_save_dir_path_edit)
            return True

        if os.path.isdir(path):
            self.default_save_dir_path_edit.setText("✓ " + tr("valid"))
            self.default_save_dir_path_edit.setProperty("statusType", StatusType.SUCCESS.value)
            refresh_widget_style(self.default_save_dir_path_edit)
            return True
        else:
            self.default_save_dir_path_edit.setText("✗ " + tr("invalid"))
            self.default_save_dir_path_edit.setProperty("statusType", StatusType.ERROR.value)
            refresh_widget_style(self.default_save_dir_path_edit)
            return False

    def _validate_game_dir_path(self):
        path = self.game_dir_path_edit.text().strip()
        if not path:
            self.game_dir_path_status.setText(tr("please_set_game_dir_path"))
            self.game_dir_path_status.setProperty("statusType", StatusType.WARNING.value)
            refresh_widget_style(self.game_dir_path_status)
            return False

        if self._game_adapter:
            is_valid = self._game_adapter.validate_game_dir_path(path)
        else:
            is_valid = os.path.isdir(path) and os.path.exists(os.path.join(path, "Modules"))

        if is_valid:
            self.game_dir_path_status.setText("✓ " + tr("valid"))
            self.game_dir_path_status.setProperty("statusType", StatusType.SUCCESS.value)
            refresh_widget_style(self.game_dir_path_status)
            return True
        else:
            self.game_dir_path_status.setText("✗ " + tr("invalid_modules"))
            self.game_dir_path_status.setProperty("statusType", StatusType.ERROR.value)
            refresh_widget_style(self.game_dir_path_status)
            return False

    def _browse_local_mod_dir_path(self):
        folder = QFileDialog.getExistingDirectory(self, tr("local_mod_dir_path_title"))
        if folder:
            self.local_mod_dir_path_edit.setText(folder)

    def _validate_mod_paths(self) -> bool:
        """验证Mod路径（本地mod路径和创意工坊路径至少需要一个）"""
        local_path = self.local_mod_dir_path_edit.text().strip()
        workshop_dir_path = self.workshop_dir_path_edit.text().strip()

        if not local_path and not workshop_dir_path:
            QMessageBox.warning(
                self,
                tr("error_title"),
                tr("mod_path_required")
            )
            return False
        return True

    def _accept_settings(self):
        game_dir_path = self.game_dir_path_edit.text().strip()

        if not game_dir_path:
            QMessageBox.warning(self, tr("error_title"), tr("please_set_game_dir_path"))
            return

        if self._game_adapter:
            is_valid = self._game_adapter.validate_game_dir_path(game_dir_path)
        else:
            is_valid = os.path.isdir(game_dir_path) and os.path.exists(os.path.join(game_dir_path, "Modules"))

        if not is_valid:
            reply = QMessageBox.question(
                self, tr("confirm_delete"),
                tr("confirm_save_invalid"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        if not self._validate_mod_paths():
            return

        custom_name = self.game_name_edit.text().strip()
        if self._config_manager:
            self._config_manager.set_custom_game_name(custom_name)

        self.result_paths = GamePaths(
            game_dir_path=self.game_dir_path_edit.text().strip(),
            workshop_dir_path=self.workshop_dir_path_edit.text().strip(),
            game_config_dir_path=self.game_config_dir_path_edit.text().strip(),
            local_mod_dir_path=self.local_mod_dir_path_edit.text().strip(),
            default_save_dir_path=self.default_save_dir_path_edit.text().strip(),
            custom_paths=self.game_dir_paths.custom_paths
        )

        self.accept()

    def get_paths(self) -> Optional[GamePaths]:
        return self.result_paths


class CustomPathDialog(QDialog):
    def __init__(self, parent=None, key: str = "", path: str = ""):
        super().__init__(parent)
        self._key = key
        self._path = path

        self.setWindowTitle(tr("custom_path_dialog_title"))
        self.setMinimumWidth(500)

        self._init_ui()

        if key:
            self.key_edit.setText(key)
        if path:
            self.path_edit.setText(path)

    def _init_ui(self):
        layout = QVBoxLayout(self)

        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel(tr("custom_path_key") + ":"))
        self.key_edit = QLineEdit()
        self.key_edit.setPlaceholderText(tr("custom_path_key_placeholder"))
        layout.addLayout(key_layout)
        layout.addWidget(self.key_edit)

        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel(tr("custom_path_value") + ":"))
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText(tr("custom_path_value_placeholder"))
        path_layout.addWidget(self.path_edit, 1)

        browse_btn = QPushButton(tr("browse") + "...")
        browse_btn.clicked.connect(self._browse_path)
        path_layout.addWidget(browse_btn)

        layout.addLayout(path_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        ok_btn = QPushButton(tr("ok"))
        ok_btn.clicked.connect(self._accept)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton(tr("cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

    def _browse_path(self):
        folder = QFileDialog.getExistingDirectory(self, tr("custom_path_value"))
        if folder:
            self.path_edit.setText(folder)

    def _accept(self):
        key = self.key_edit.text().strip()
        path = self.path_edit.text().strip()

        if not key:
            QMessageBox.warning(self, tr("error_title"), tr("custom_path_key_empty"))
            return

        if not path:
            QMessageBox.warning(self, tr("error_title"), tr("custom_path_value_empty"))
            return

        self.accept()

    def get_values(self) -> tuple:
        return self.key_edit.text().strip(), self.path_edit.text().strip()
