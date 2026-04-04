from typing import Optional

from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QFrame, QComboBox, QToolButton
)

from yh_mods_manager_sdk import ListType, ModType
from utils.icons import get_mod_type_icon, get_icon
from .mod_list_item import ModListDelegate
from ..draggable_list import DraggableListWidget
from ..i18n import tr
from ..styles import refresh_widget_style, refresh_widgets_style, get_calculated_font_size, get_ui_constant, FontSize
from ..theme_manager import get_color


def _get_list_panel_config():
    return {
        'type_filter_min_width': get_ui_constant('list_panel', 'type_filter_min_width', 80),
        'filter_mode_btn_size': get_ui_constant('list_panel', 'filter_mode_btn_size', 28),
        'margin': get_ui_constant('list_panel', 'margin', 8),
        'icon_size_medium': get_ui_constant('icon_sizes', 'medium', 16),
        'icon_size_large': get_ui_constant('icon_sizes', 'large', 20),
    }


class ListPanel(QWidget):
    enable_selected_clicked = pyqtSignal()
    enable_all_clicked = pyqtSignal()
    disable_selected_clicked = pyqtSignal()
    disable_all_clicked = pyqtSignal()
    move_up_clicked = pyqtSignal()
    move_down_clicked = pyqtSignal()
    search_changed = pyqtSignal(str)
    type_filter_changed = pyqtSignal(int)
    filter_mode_changed = pyqtSignal(bool)

    def __init__(self, list_type: ListType, base_font_size: int = 14, parent=None):
        super().__init__(parent)
        self.list_type = list_type
        self.base_font_size = base_font_size
        self._filter_only_mode = True
        self._config = _get_list_panel_config()
        self._init_ui()

    def _init_ui(self):
        self.setProperty("widgetType", "list_panel")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(self._config['margin'], self._config['margin'], self._config['margin'],
                                  self._config['margin'])

        header_layout = QHBoxLayout()
        header_text = tr("disabled_mods") if self.list_type == ListType.DISABLED else tr("drag_to_reorder")
        self.header_label = QLabel(header_text)
        self.header_label.setProperty("labelType", "list_header")
        font = self.header_label.font()
        font.setBold(True)
        font.setPointSize(get_calculated_font_size(self.base_font_size, FontSize.SMALL))
        self.header_label.setFont(font)
        header_layout.addWidget(self.header_label)
        header_layout.addStretch()

        self.count_label = QLabel("")
        self.count_label.setProperty("labelType",
                                     "count_disabled" if self.list_type == ListType.DISABLED else "count_normal")
        font = self.count_label.font()
        font.setPointSize(get_calculated_font_size(self.base_font_size, FontSize.SMALL))
        self.count_label.setFont(font)
        header_layout.addWidget(self.count_label)
        layout.addLayout(header_layout)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        placeholder = "🔍 " + (
            tr("search_disabled") if self.list_type == ListType.DISABLED else tr("tip_search") + "...")
        self.search_input.setPlaceholderText(placeholder)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self.search_changed.emit)
        search_layout.addWidget(self.search_input)

        self.filter_mode_btn = QToolButton()
        btn_size = self._config['filter_mode_btn_size']
        self.filter_mode_btn.setFixedSize(btn_size, btn_size)
        self.filter_mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.filter_mode_btn.setToolTip(tr("toggle_filter_mode"))
        self.filter_mode_btn.clicked.connect(self._toggle_filter_mode)
        self._update_filter_mode_icon()
        search_layout.addWidget(self.filter_mode_btn)

        self.type_filter = QComboBox()
        self.type_filter.setToolTip(tr("filter_by_type"))
        self.type_filter.addItem(tr("all_types"), None)
        self._populate_type_filter()
        self.type_filter.currentIndexChanged.connect(self.type_filter_changed.emit)
        self.type_filter.setMinimumWidth(self._config['type_filter_min_width'])
        self.type_filter.setProperty("comboBoxType", "tag")
        search_layout.addWidget(self.type_filter)
        layout.addLayout(search_layout)

        list_container = QFrame()
        self.list_container = list_container
        self.list_container.setProperty("frameType", "list_container")
        self._update_list_container_style()
        list_container_layout = QVBoxLayout(list_container)
        list_container_layout.setContentsMargins(0, 0, 0, 0)

        self.list_widget = DraggableListWidget(self.list_type)
        self.list_widget.setItemDelegate(ModListDelegate(self.list_widget, self.base_font_size))
        self.list_widget.setProperty("listWidgetType", "mod_list")
        list_container_layout.addWidget(self.list_widget)
        layout.addWidget(list_container)

        btn_layout = QHBoxLayout()

        if self.list_type == ListType.DISABLED:
            self.enable_btn = QPushButton(tr("enable_selected"))
            self.enable_btn.clicked.connect(self.enable_selected_clicked.emit)
            self.enable_btn.setProperty("buttonType", "standard")
            btn_layout.addWidget(self.enable_btn)

            self.enable_all_btn = QPushButton(tr("enable_all") + " →")
            self.enable_all_btn.clicked.connect(self.enable_all_clicked.emit)
            self.enable_all_btn.setProperty("buttonType", "enable_all")
            btn_layout.addWidget(self.enable_all_btn)
        else:
            self.move_up_btn = QPushButton("↑ " + tr("move_up"))
            self.move_up_btn.clicked.connect(self.move_up_clicked.emit)
            self.move_up_btn.setProperty("buttonType", "standard")
            btn_layout.addWidget(self.move_up_btn)

            self.move_down_btn = QPushButton("↓ " + tr("move_down"))
            self.move_down_btn.clicked.connect(self.move_down_clicked.emit)
            self.move_down_btn.setProperty("buttonType", "standard")
            btn_layout.addWidget(self.move_down_btn)

            self.disable_btn = QPushButton(tr("disable_selected"))
            self.disable_btn.clicked.connect(self.disable_selected_clicked.emit)
            self.disable_btn.setProperty("buttonType", "standard")
            btn_layout.addWidget(self.disable_btn)

            self.disable_all_btn = QPushButton("← " + tr("disable_all"))
            self.disable_all_btn.clicked.connect(self.disable_all_clicked.emit)
            self.disable_all_btn.setProperty("buttonType", "disable_all")
            btn_layout.addWidget(self.disable_all_btn)

        layout.addLayout(btn_layout)

    def _populate_type_filter(self):
        type_items = [
            (ModType.WORKSHOP, tr("mod_type_workshop")),
            (ModType.LOCAL, tr("mod_type_local")),
            (ModType.DLC, tr("mod_type_dlc")),
            (ModType.CORE, tr("mod_type_core")),
        ]
        for mod_type, display_name in type_items:
            icon = get_mod_type_icon(mod_type, self._config['icon_size_medium'])
            self.type_filter.addItem(icon, display_name, mod_type)

    def _toggle_filter_mode(self):
        self._filter_only_mode = not self._filter_only_mode
        self._update_filter_mode_icon()
        self.filter_mode_changed.emit(self._filter_only_mode)

    def _update_filter_mode_icon(self):
        if self._filter_only_mode:
            icon = get_icon('eye_slash', get_color('text'), self._config['icon_size_large'])
            self.filter_mode_btn.setToolTip(tr("show_all_with_mask"))
        else:
            icon = get_icon('eye_light', get_color('text'), self._config['icon_size_large'])
            self.filter_mode_btn.setToolTip(tr("show_filtered_only"))
        self.filter_mode_btn.setIcon(icon)

    def is_filter_only_mode(self) -> bool:
        return self._filter_only_mode

    def set_filter_only_mode(self, filter_only: bool):
        if self._filter_only_mode != filter_only:
            self._filter_only_mode = filter_only
            self._update_filter_mode_icon()

    def get_list_widget(self) -> DraggableListWidget:
        return self.list_widget

    def get_type_filter_value(self) -> Optional[ModType]:
        data = self.type_filter.currentData()
        return data if isinstance(data, ModType) else None

    def _update_list_container_style(self):
        refresh_widget_style(self.list_container)

    def set_count(self, count: int, issue_count: int = 0):
        if issue_count > 0:
            self.count_label.setText(f"({count} | ⚠️ {issue_count})")
            self.count_label.setProperty("labelType", "count_warning")
        else:
            self.count_label.setText(f"({count})")
            self.count_label.setProperty("labelType",
                                         "count_disabled" if self.list_type == ListType.DISABLED else "count_normal")
        font = self.count_label.font()
        font.setPointSize(get_calculated_font_size(self.base_font_size, FontSize.SMALL))
        self.count_label.setFont(font)
        refresh_widget_style(self.count_label)

    def refresh_styles(self):
        self.header_label.setProperty("labelType", "list_header")
        font = self.header_label.font()
        font.setBold(True)
        font.setPointSize(get_calculated_font_size(self.base_font_size, FontSize.SMALL))
        self.header_label.setFont(font)
        self._update_list_container_style()
        refresh_widget_style(self.type_filter)

        if self.list_type == ListType.DISABLED:
            refresh_widgets_style(self.enable_btn, self.enable_all_btn)
        else:
            refresh_widgets_style(
                self.move_up_btn, self.move_down_btn,
                self.disable_btn, self.disable_all_btn
            )
