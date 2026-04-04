from typing import List, Dict, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QScrollArea, QApplication
)

from ..i18n import tr
from ..styles import get_calculated_font_size, FontSize


class MissingModsDialog(QDialog):
    def __init__(self, missing_mods: List[Dict[str, Optional[str]]], profile_name: str = "", base_font_size: int = 14,
                 parent=None):
        super().__init__(parent)
        self._missing_mods = missing_mods
        self._profile_name = profile_name
        self._base_font_size = base_font_size
        self._confirmed = False
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle(tr("missing_mods_title"))
        self.setMinimumWidth(550)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        self._apply_dialog_style()

        count = len(self._missing_mods)
        if self._profile_name:
            info_text = tr("missing_mods_info_with_profile").format(self._profile_name, count)
        else:
            info_text = tr("missing_mods_info").format(count)

        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        info_label.setProperty("labelType", "validation_info")
        font = info_label.font()
        font.setBold(True)
        font.setPointSize(get_calculated_font_size(self._base_font_size, FontSize.BASE))
        info_label.setFont(font)
        layout.addWidget(info_label)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setProperty("scrollAreaType", "validation")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(8, 8, 8, 8)
        scroll_layout.setSpacing(4)

        for mod_info in self._missing_mods:
            mod_id = mod_info.get('id', '')
            name = mod_info.get('name', mod_id or 'Unknown')
            workshop_id = mod_info.get('workshop_id')

            detail_parts = [f"ID: {mod_id}"]
            if workshop_id:
                detail_parts.append(f"Workshop: {workshop_id}")
            detail_text = " | ".join(detail_parts)

            mod_widget = QWidget()
            mod_layout = QVBoxLayout(mod_widget)
            mod_layout.setContentsMargins(0, 0, 0, 0)
            mod_layout.setSpacing(2)

            name_layout = QHBoxLayout()
            name_layout.setContentsMargins(12, 0, 0, 0)
            name_layout.setSpacing(4)

            bullet_label = QLabel("•")
            bullet_label.setProperty("labelType", "missing_mod_bullet")
            name_layout.addWidget(bullet_label)

            name_label = QLabel(name)
            name_label.setProperty("labelType", "missing_mod_name")
            name_layout.addWidget(name_label, 1)

            mod_layout.addLayout(name_layout)

            detail_label = QLabel(detail_text)
            detail_label.setProperty("labelType", "missing_mod_detail")
            detail_label.setContentsMargins(24, 0, 0, 0)
            mod_layout.addWidget(detail_label)

            mod_widget.setProperty("widgetType", "missing_mod_item")
            scroll_layout.addWidget(mod_widget)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        copy_layout = QHBoxLayout()
        copy_layout.addStretch()

        self.copy_btn = QPushButton(tr("copy_missing_mods"))
        self.copy_btn.setProperty("buttonType", "standard")
        self.copy_btn.clicked.connect(self._copy_missing_mods)
        copy_layout.addWidget(self.copy_btn)

        layout.addLayout(copy_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton(tr("cancel"))
        self.cancel_btn.setProperty("buttonType", "standard")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.confirm_btn = QPushButton(tr("continue_import"))
        self.confirm_btn.setProperty("buttonType", "accent")
        self.confirm_btn.clicked.connect(self._on_confirm)
        btn_layout.addWidget(self.confirm_btn)

        layout.addLayout(btn_layout)

    def _apply_dialog_style(self):
        self.setProperty("dialogType", "validation")

    def _copy_missing_mods(self):
        lines = [tr("missing_mods_copy_header")]
        for mod_info in self._missing_mods:
            display_name = mod_info.get('display_name', mod_info.get('id', 'Unknown'))
            mod_id = mod_info.get('id', '')
            workshop_id = mod_info.get('workshop_id')

            if workshop_id:
                lines.append(f"• {display_name} | ID: {mod_id} | Workshop: {workshop_id}")
            else:
                lines.append(f"• {display_name} | ID: {mod_id}")

        text = "\n".join(lines)
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

        self.copy_btn.setText(tr("copied"))
        self.copy_btn.setProperty("buttonType", "copied")
        self.copy_btn.style().unpolish(self.copy_btn)
        self.copy_btn.style().polish(self.copy_btn)

        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1500, self._reset_copy_button)

    def _reset_copy_button(self):
        self.copy_btn.setText(tr("copy_missing_mods"))
        self.copy_btn.setProperty("buttonType", "standard")
        self.copy_btn.style().unpolish(self.copy_btn)
        self.copy_btn.style().polish(self.copy_btn)

    def _on_confirm(self):
        self._confirmed = True
        self.accept()

    def is_confirmed(self) -> bool:
        return self._confirmed

    @staticmethod
    def check_and_show(missing_mods: List[Dict[str, Optional[str]]], profile_name: str = "", base_font_size: int = 14,
                       parent=None) -> bool:
        if not missing_mods:
            return True

        dialog = MissingModsDialog(missing_mods, profile_name, base_font_size, parent)
        result = dialog.exec()
        return result == QDialog.DialogCode.Accepted
