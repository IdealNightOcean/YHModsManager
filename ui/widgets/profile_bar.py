from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QComboBox, QPushButton

from ..i18n import tr
from ..styles import refresh_widgets_style


class ProfileBar(QWidget):
    profile_changed = pyqtSignal(str)
    new_profile_clicked = pyqtSignal()
    save_profile_clicked = pyqtSignal()
    delete_profile_clicked = pyqtSignal()
    rename_profile_clicked = pyqtSignal()

    def __init__(self, base_font_size: int = 14, parent=None):
        super().__init__(parent)
        self.base_font_size = base_font_size
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 5)

        layout.addWidget(QLabel(tr("profile_scheme")))

        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(200)
        self.profile_combo.currentTextChanged.connect(self._on_profile_changed)
        layout.addWidget(self.profile_combo)

        self.new_btn = QPushButton(tr("new_profile"))
        self.new_btn.clicked.connect(self.new_profile_clicked.emit)
        self.new_btn.setProperty("buttonType", "standard")
        layout.addWidget(self.new_btn)

        self.save_btn = QPushButton(tr("save"))
        self.save_btn.clicked.connect(self.save_profile_clicked.emit)
        self.save_btn.setProperty("buttonType", "standard")
        layout.addWidget(self.save_btn)

        self.rename_btn = QPushButton(tr("rename"))
        self.rename_btn.clicked.connect(self.rename_profile_clicked.emit)
        self.rename_btn.setProperty("buttonType", "standard")
        layout.addWidget(self.rename_btn)

        self.delete_btn = QPushButton(tr("delete"))
        self.delete_btn.clicked.connect(self.delete_profile_clicked.emit)
        self.delete_btn.setProperty("buttonType", "standard")
        layout.addWidget(self.delete_btn)
        layout.addStretch()

    def _on_profile_changed(self, profile_name: str):
        if profile_name:
            self.profile_changed.emit(profile_name)

    def set_profiles(self, profile_names: list, current_name: str = None):
        self.profile_combo.blockSignals(True)
        self.profile_combo.clear()
        for name in profile_names:
            self.profile_combo.addItem(name)
        if current_name:
            index = self.profile_combo.findText(current_name)
            if index >= 0:
                self.profile_combo.setCurrentIndex(index)
        self.profile_combo.blockSignals(False)

    def get_current_profile_name(self) -> str:
        return self.profile_combo.currentText()

    def set_current_profile(self, profile_name: str):
        self.profile_combo.blockSignals(True)
        index = self.profile_combo.findText(profile_name)
        if index >= 0:
            self.profile_combo.setCurrentIndex(index)
        self.profile_combo.blockSignals(False)

    def refresh_styles(self):
        refresh_widgets_style(self.new_btn, self.save_btn, self.rename_btn, self.delete_btn)
