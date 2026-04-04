"""
关于对话框模块
展示软件信息、GitHub链接、协议、作者、版本、更新日志按钮
"""

import logging

from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QFrame
)

from services.update_service import get_update_service
from ui.i18n import tr
from ui.styles import refresh_widget_style

logger = logging.getLogger(__name__)


class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class AboutDialog(QDialog):
    changelog_requested = pyqtSignal()

    def __init__(self, parent=None, base_font_size: int = 12):
        super().__init__(parent)
        self._base_font_size = base_font_size
        self._update_service = get_update_service()
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle(tr("about"))
        self.setMinimumSize(450, 400)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        title_label = QLabel(tr("app_name"))
        title_label.setProperty("labelType", "about_title")
        refresh_widget_style(title_label)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        version = self._update_service.get_current_version()
        version_label = QLabel(f"v{version}")
        version_label.setProperty("labelType", "about_version")
        refresh_widget_style(version_label)
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setProperty("frameType", "separator")
        refresh_widget_style(line)
        layout.addWidget(line)

        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setSpacing(12)

        author = self._update_service.get_author()
        author_row = self._create_info_row(tr("info_author"), author)
        info_layout.addLayout(author_row)

        license_name = self._update_service.get_license()
        license_row = self._create_info_row(tr("about_license"), license_name)
        info_layout.addLayout(license_row)

        github_repo = self._update_service.get_github_repo()
        if github_repo:
            github_url = f"https://github.com/{github_repo}"
            github_row = self._create_link_row(tr("about_github"), github_url)
            info_layout.addLayout(github_row)

        layout.addWidget(info_widget)

        desc_label = QLabel(tr("about_description"))
        desc_label.setProperty("labelType", "about_description")
        refresh_widget_style(desc_label)
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_label)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        changelog_btn = QPushButton(tr("about_changelog"))
        changelog_btn.setProperty("buttonType", "standard")
        changelog_btn.clicked.connect(self._on_changelog_clicked)
        btn_layout.addWidget(changelog_btn)

        check_update_btn = QPushButton(tr("about_check_update"))
        check_update_btn.setProperty("buttonType", "accent")
        check_update_btn.clicked.connect(self._on_check_update_clicked)
        btn_layout.addWidget(check_update_btn)

        layout.addLayout(btn_layout)

        close_btn = QPushButton(tr("close"))
        close_btn.setProperty("buttonType", "standard")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    @staticmethod
    def _create_info_row(label: str, value: str) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.addStretch()

        label_widget = QLabel(f"{label}:")
        label_widget.setProperty("labelType", "about_info_label")
        refresh_widget_style(label_widget)
        layout.addWidget(label_widget)

        value_widget = QLabel(value)
        value_widget.setProperty("labelType", "about_info_value")
        refresh_widget_style(value_widget)
        layout.addWidget(value_widget)

        layout.addStretch()
        return layout

    def _create_link_row(self, label: str, url: str) -> QHBoxLayout:
        layout = QHBoxLayout()
        layout.addStretch()

        label_widget = QLabel(f"{label}:")
        label_widget.setProperty("labelType", "about_info_label")
        refresh_widget_style(label_widget)
        layout.addWidget(label_widget)

        link_widget = ClickableLabel(url)
        link_widget.setProperty("labelType", "about_link")
        refresh_widget_style(link_widget)
        link_widget.clicked.connect(lambda: self._open_url(url))
        layout.addWidget(link_widget)

        layout.addStretch()
        return layout

    @staticmethod
    def _open_url(url: str):
        try:
            QDesktopServices.openUrl(QUrl(url))
        except Exception as e:
            logger.error(f"Failed to open URL {url}: {e}")

    def _on_changelog_clicked(self):
        self.changelog_requested.emit()

    def _on_check_update_clicked(self):
        from ui.dialogs.update_dialog import UpdateCheckDialog
        dialog = UpdateCheckDialog(self, self._base_font_size)
        dialog.exec()
