from typing import List, Tuple, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QScrollArea, QApplication
)

from ..i18n import tr
from ..styles import get_calculated_font_size, FontSize


class ValidationResultDialog(QDialog):
    def __init__(self, errors: List[str], base_font_size: int = 14, parent=None,
                 enabled_order: Optional[List[str]] = None):
        super().__init__(parent)
        self._errors = errors
        self._base_font_size = base_font_size
        self._enabled_order = enabled_order or []
        self._sorted_errors: List[Tuple[int, str, str]] = []
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle(tr("validation_result"))
        self.setMinimumWidth(550)
        self.setMinimumHeight(400)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        self._apply_dialog_style()

        count = len(self._errors)
        info_label = QLabel(tr("validation_issues_count").format(count))
        info_label.setWordWrap(True)
        info_label.setProperty("labelType", "validation_info")
        font = info_label.font()
        font.setBold(True)
        font.setPointSize(get_calculated_font_size(self._base_font_size, FontSize.BASE))
        info_label.setFont(font)
        layout.addWidget(info_label)

        self._sorted_errors = self._sort_errors_by_enabled_order(self._errors)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setProperty("scrollAreaType", "validation")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(8, 8, 8, 8)
        scroll_layout.setSpacing(4)

        for order_num, mod_name, error_msg in self._sorted_errors:
            if order_num > 0:
                error_label = QLabel(f"• [{order_num}] {error_msg}")
            else:
                error_label = QLabel(f"• {error_msg}")
            error_label.setWordWrap(True)
            error_label.setProperty("labelType", "validation_error")
            scroll_layout.addWidget(error_label)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        copy_layout = QHBoxLayout()
        copy_layout.addStretch()

        self.copy_btn = QPushButton(tr("copy_validation_errors"))
        self.copy_btn.setProperty("buttonType", "standard")
        self.copy_btn.clicked.connect(self._copy_errors)
        copy_layout.addWidget(self.copy_btn)

        layout.addLayout(copy_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.ok_btn = QPushButton(tr("ok"))
        self.ok_btn.setProperty("buttonType", "accent")
        self.ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.ok_btn)

        layout.addLayout(btn_layout)

    def _apply_dialog_style(self):
        self.setProperty("dialogType", "validation")

    def _sort_errors_by_enabled_order(self, errors: List[str]) -> List[Tuple[int, str, str]]:
        parsed_errors = []
        order_map = {mod_id: idx + 1 for idx, mod_id in enumerate(self._enabled_order)}

        for error in errors:
            mod_id, mod_name, error_text = self._parse_error(error)
            order_num = order_map.get(mod_id, 0)
            display_text = f"{mod_name}: {error_text}" if mod_name else error_text
            parsed_errors.append((order_num, mod_id, display_text))

        parsed_errors.sort(key=lambda x: (x[0] if x[0] > 0 else float('inf'), x[1].lower()))

        return parsed_errors

    @staticmethod
    def _parse_error(error: str) -> Tuple[str, str, str]:
        import re
        match = re.match(r"\[([^\]]+)\]'([^']+)':\s*(.+)", error)
        if match:
            return match.group(1), match.group(2), match.group(3)

        match = re.search(r"'([^']+)'", error)
        if match:
            mod_name = match.group(1)
            return mod_name, mod_name, error

        words = error.split()
        mod_name = words[0] if words else "Unknown"
        return mod_name, mod_name, error

    def _copy_errors(self):
        lines = [tr("validation_errors_copy_header")]
        for order_num, mod_name, error_msg in self._sorted_errors:
            if order_num > 0:
                lines.append(f"• [{order_num}] {error_msg}")
            else:
                lines.append(f"• {error_msg}")

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
        self.copy_btn.setText(tr("copy_validation_errors"))
        self.copy_btn.setProperty("buttonType", "standard")
        self.copy_btn.style().unpolish(self.copy_btn)
        self.copy_btn.style().polish(self.copy_btn)

    @staticmethod
    def show_errors(errors: List[str], base_font_size: int = 14, parent=None,
                    enabled_order: Optional[List[str]] = None) -> bool:
        if not errors:
            return False

        dialog = ValidationResultDialog(errors, base_font_size, parent, enabled_order)
        dialog.exec()
        return True
