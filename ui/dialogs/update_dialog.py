"""
更新相关对话框模块
包含更新日志展示、更新检查、更新进度等对话框
"""

import logging
import os
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal, QThread, QFileSystemWatcher
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QFrame, QScrollArea, QProgressBar, QMessageBox,
    QCheckBox
)

from services.update_service import get_update_service, UpdateInfo
from ui.i18n import tr
from ui.styles import refresh_widget_style
from ui.theme_manager import get_color
from utils.icons import get_icon

logger = logging.getLogger(__name__)


class ChangelogDialog(QDialog):
    def __init__(self, parent=None, base_font_size: int = 12, limit: int = 5):
        super().__init__(parent)
        self._base_font_size = base_font_size
        self._limit = limit
        self._update_service = get_update_service()
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle(tr("about_changelog"))
        self.setMinimumSize(500, 450)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title_label = QLabel(tr("about_changelog"))
        title_label.setProperty("labelType", "dialog_title")
        refresh_widget_style(title_label)
        layout.addWidget(title_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setProperty("scrollAreaType", "changelog")

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(16)

        entries = self._update_service.get_changelog_entries(self._limit)

        for i, entry in enumerate(entries):
            entry_widget = self._create_changelog_entry(entry)
            content_layout.addWidget(entry_widget)

            if i < len(entries) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setProperty("frameType", "separator")
                refresh_widget_style(line)
                content_layout.addWidget(line)

        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        close_btn = QPushButton(tr("close"))
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    @staticmethod
    def _create_changelog_entry(entry) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()

        version_label = QLabel(f"v{entry.version}")
        version_label.setProperty("labelType", "changelog_version")
        refresh_widget_style(version_label)
        header_layout.addWidget(version_label)

        date_label = QLabel(entry.date)
        date_label.setProperty("labelType", "changelog_date")
        refresh_widget_style(date_label)
        header_layout.addWidget(date_label)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        for change in entry.changes:
            change_label = QLabel(f"• {change}")
            change_label.setProperty("labelType", "changelog_item")
            change_label.setWordWrap(True)
            refresh_widget_style(change_label)
            layout.addWidget(change_label)

        return widget


class UpdateCheckWorker(QThread):
    finished = pyqtSignal(bool, object)
    error = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._update_service = get_update_service()

    def run(self):
        try:
            has_update, update_info = self._update_service.check_for_updates()
            self.finished.emit(has_update, update_info)
        except Exception as e:
            logger.error(f"Error checking for updates: {e}", exc_info=True)
            self.error.emit(str(e))


class UpdateDownloadWorker(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, update_info: UpdateInfo, parent=None):
        super().__init__(parent)
        self._update_service = get_update_service()
        self._update_info = update_info

    def run(self):
        try:
            download_path = self._update_service.download_update(
                self._update_info,
                lambda current, total: self.progress.emit(current, total)
            )
            if download_path:
                self.finished.emit(download_path)
            else:
                self.error.emit(tr("update_download_failed"))
        except Exception as e:
            logger.error(f"Error downloading update: {e}", exc_info=True)
            self.error.emit(str(e))


class UpdateCheckDialog(QDialog):
    def __init__(self, parent=None, base_font_size: int = 12):
        super().__init__(parent)
        self._base_font_size = base_font_size
        self._update_service = get_update_service()
        self._update_info: Optional[UpdateInfo] = None
        self._download_path: Optional[str] = None
        self._check_worker: Optional[UpdateCheckWorker] = None
        self._download_worker: Optional[UpdateDownloadWorker] = None
        self._file_watcher: Optional[QFileSystemWatcher] = None
        self._updating: bool = False
        self._setup_ui()
        self._start_check()

    def _setup_ui(self):
        self.setWindowTitle(tr("about_check_update"))
        self.setMinimumSize(400, 300)
        self.setModal(True)

        self._layout = QVBoxLayout(self)
        self._layout.setSpacing(16)

        self._status_label = QLabel(tr("update_checking"))
        self._status_label.setProperty("labelType", "dialog_status")
        self._status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        refresh_widget_style(self._status_label)
        self._layout.addWidget(self._status_label)

        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        self._layout.addWidget(self._progress_bar)

        self._info_widget = QWidget()
        self._info_layout = QVBoxLayout(self._info_widget)
        self._info_layout.setSpacing(8)
        self._info_widget.setVisible(False)
        self._layout.addWidget(self._info_widget)

        self._button_layout = QHBoxLayout()
        self._button_layout.addStretch()

        self._action_btn = QPushButton(tr("ok"))
        self._action_btn.clicked.connect(self.accept)
        self._button_layout.addWidget(self._action_btn)

        self._cancel_btn = QPushButton(tr("cancel"))
        self._cancel_btn.clicked.connect(self._on_cancel)
        self._cancel_btn.setVisible(False)
        self._button_layout.addWidget(self._cancel_btn)

        self._layout.addLayout(self._button_layout)

    def _start_check(self):
        self._status_label.setText(tr("update_checking"))
        self._check_worker = UpdateCheckWorker(self)
        self._check_worker.finished.connect(self._on_check_finished)
        self._check_worker.error.connect(self._on_check_error)
        self._check_worker.start()

    def _on_check_finished(self, has_update: bool, update_info: Optional[UpdateInfo]):
        if has_update and update_info:
            self._update_info = update_info
            self._show_update_available(update_info)
        else:
            self._status_label.setText(tr("update_no_update"))

    def _on_check_error(self, error: str):
        self._status_label.setText(f"{tr('update_check_failed')}: {error}")

    def _show_update_available(self, update_info: UpdateInfo):
        self._status_label.setText(tr("update_available").format(version=update_info.version))
        self._status_label.setProperty("labelType", "dialog_status_success")
        refresh_widget_style(self._status_label)

        self._info_widget.setVisible(True)

        for i in reversed(range(self._info_layout.count())):
            self._info_layout.itemAt(i).widget().deleteLater()

        version_label = QLabel(f"{tr('update_new_version')}: v{update_info.version}")
        version_label.setProperty("labelType", "update_info")
        refresh_widget_style(version_label)
        self._info_layout.addWidget(version_label)

        size_mb = update_info.file_size / (1024 * 1024)
        size_label = QLabel(f"{tr('update_file_size')}: {size_mb:.2f} MB")
        size_label.setProperty("labelType", "update_info")
        refresh_widget_style(size_label)
        self._info_layout.addWidget(size_label)

        self._action_btn.setText(tr("update_download"))
        self._action_btn.clicked.disconnect()
        self._action_btn.clicked.connect(self._start_download)

        self._cancel_btn.setVisible(True)

    def _start_download(self):
        if not self._update_info:
            return

        self._status_label.setText(tr("update_downloading"))
        self._progress_bar.setVisible(True)
        self._progress_bar.setRange(0, 100)
        self._action_btn.setEnabled(False)
        self._cancel_btn.setEnabled(False)

        self._download_worker = UpdateDownloadWorker(self._update_info, self)
        self._download_worker.progress.connect(self._on_download_progress)
        self._download_worker.finished.connect(self._on_download_finished)
        self._download_worker.error.connect(self._on_download_error)
        self._download_worker.start()

    def _on_download_progress(self, current: int, total: int):
        if total > 0:
            percent = int(current * 100 / total)
            self._progress_bar.setValue(percent)

    def _on_download_finished(self, download_path: str):
        self._download_path = download_path
        self._status_label.setText(tr("update_download_complete"))
        self._progress_bar.setVisible(False)
        self._action_btn.setEnabled(True)
        self._action_btn.setText(tr("update_install"))
        self._action_btn.clicked.disconnect()
        self._action_btn.clicked.connect(self._install_update)
        self._cancel_btn.setEnabled(True)
        self._cancel_btn.setText(tr("cancel"))

    def _on_download_error(self, error: str):
        self._status_label.setText(f"{tr('update_download_failed')}: {error}")
        self._progress_bar.setVisible(False)
        self._action_btn.setEnabled(True)
        self._cancel_btn.setEnabled(True)

    def _install_update(self):
        if not self._download_path:
            return

        reply = QMessageBox.question(
            self,
            tr("update_install"),
            tr("update_install_confirm"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self._updating = True
        self._status_label.setText(tr("update_installing"))
        self._action_btn.setEnabled(False)
        self._cancel_btn.setEnabled(False)

        success, message = self._update_service.install_update(self._download_path)

        if success:
            self._start_update_complete_watcher()
            self._update_service.execute_update_restart()
            self._status_label.setText(tr("update_waiting_complete"))
        else:
            self._updating = False
            QMessageBox.critical(
                self,
                tr("update_install"),
                f"{tr('update_install_failed')}: {message}"
            )
            self._action_btn.setEnabled(True)
            self._cancel_btn.setEnabled(True)

    def _start_update_complete_watcher(self):
        marker_path = self._update_service.get_update_complete_marker_path()
        marker_dir = os.path.dirname(marker_path)
        
        self._file_watcher = QFileSystemWatcher(self)
        self._file_watcher.addPath(marker_dir)
        self._file_watcher.directoryChanged.connect(self._check_update_complete)
        self._file_watcher.fileChanged.connect(self._check_update_complete)

    def _check_update_complete(self):
        if self._update_service.check_update_complete_marker():
            if self._file_watcher:
                self._file_watcher.deleteLater()
                self._file_watcher = None
            
            QMessageBox.information(
                self,
                tr("update_install"),
                tr("update_complete_restart")
            )
            self.accept()
            if self.parent():
                from PyQt6.QtWidgets import QWidget
                parent = self.parent()
                while parent.parent():
                    parent = parent.parent()
                if isinstance(parent, QWidget):
                    parent.close()

    def closeEvent(self, event):
        if self._updating:
            event.ignore()
        else:
            if self._check_worker and self._check_worker.isRunning():
                self._check_worker.terminate()
            if self._download_worker and self._download_worker.isRunning():
                self._download_worker.terminate()
            super().closeEvent(event)

    def _on_cancel(self):
        if self._check_worker and self._check_worker.isRunning():
            self._check_worker.terminate()
        if self._download_worker and self._download_worker.isRunning():
            self._download_worker.terminate()
        self.reject()


class UpdateNotificationDialog(QDialog):
    update_now = pyqtSignal()
    disable_check = pyqtSignal()

    def __init__(self, update_info: UpdateInfo, parent=None, base_font_size: int = 12):
        super().__init__(parent)
        self._base_font_size = base_font_size
        self._update_info = update_info
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle(tr("update_available_title"))
        self.setMinimumSize(400, 300)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        header_layout = QHBoxLayout()
        icon_label = QLabel()
        icon = get_icon('cloud', get_color('primary'), 32)
        icon_label.setPixmap(icon.pixmap(32, 32))
        header_layout.addWidget(icon_label)

        title_label = QLabel(tr("update_available_title"))
        title_label.setProperty("labelType", "dialog_title")
        refresh_widget_style(title_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        version_label = QLabel(tr("update_new_version_available").format(
            current=self._update_info.version
        ))
        version_label.setProperty("labelType", "update_info")
        refresh_widget_style(version_label)
        layout.addWidget(version_label)

        size_mb = self._update_info.file_size / (1024 * 1024)
        size_label = QLabel(f"{tr('update_file_size')}: {size_mb:.2f} MB")
        size_label.setProperty("labelType", "update_info")
        refresh_widget_style(size_label)
        layout.addWidget(size_label)

        self._disable_checkbox = QCheckBox(tr("update_disable_check"))
        layout.addWidget(self._disable_checkbox)

        layout.addStretch()

        btn_layout = QHBoxLayout()

        skip_btn = QPushButton(tr("update_skip"))
        skip_btn.setProperty("buttonType", "standard")
        skip_btn.clicked.connect(self.reject)
        btn_layout.addWidget(skip_btn)

        btn_layout.addStretch()

        update_btn = QPushButton(tr("update_now"))
        update_btn.setProperty("buttonType", "primary")
        update_btn.clicked.connect(self._on_update_now)
        btn_layout.addWidget(update_btn)

        layout.addLayout(btn_layout)

    def _on_update_now(self):
        if self._disable_checkbox.isChecked():
            self.disable_check.emit()
        self.update_now.emit()
        self.accept()

    def is_disable_checked(self) -> bool:
        return self._disable_checkbox.isChecked()
