import os
from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QTimer
from PyQt6.QtGui import QCursor, QPixmap
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox,
    QFormLayout, QScrollArea, QComboBox, QLineEdit, QTextEdit, QGridLayout,
    QSizePolicy, QApplication, QSpacerItem
)

from yh_mods_manager_sdk import Mod, ModType, ModIssueStatus
from yh_mods_manager_sdk.enum_extension import EnumExtension
from yh_mods_manager_sdk.enum_types import ActionTypes
from utils.icons import get_action_icon, get_mod_type_icon
from utils.mod_ui_utils import ModUIUtils
from .buttons import ColorButton, ClearColorButton, AddColorButton, TagButton, IssueBadgeButton
from .elided_label import ElidedLabel
from ..i18n import tr
from ..styles import FlowLayout, refresh_widget_style, refresh_widgets_style, get_calculated_font_size, get_ui_constant, \
    FontSize
from ..theme_manager import get_color
from ..toast_widget import ToastManager

if TYPE_CHECKING:
    from core.mod_manager import ModManager
    from core import UserConfigManager
    from core.config_manager import ConfigManager


def _get_info_panel_config():
    return {
        'min_width': get_ui_constant('info_panel', 'min_width', 280),
        'max_width': get_ui_constant('info_panel', 'max_width', 450),
        'preview_image_max_height': get_ui_constant('info_panel', 'preview_image_max_height', 200),
        'tag_button_height': get_ui_constant('info_panel', 'tag_button_height', 24),
        'tag_combo_min_width': get_ui_constant('info_panel', 'tag_combo_min_width', 150),
        'custom_name_label_min_width': get_ui_constant('info_panel', 'custom_name_label_min_width', 60),
        'note_edit_max_height': get_ui_constant('info_panel', 'note_edit_max_height', 80),
        'form_spacing': get_ui_constant('info_panel', 'form_spacing', 6),
        'main_spacing': get_ui_constant('info_panel', 'main_spacing', 10),
        'margin': get_ui_constant('info_panel', 'margin', 8),
    }


class InfoPanel(QWidget):
    color_changed = pyqtSignal(str, object)
    tags_changed = pyqtSignal()
    custom_name_changed = pyqtSignal()
    note_changed = pyqtSignal()
    locate_mod_requested = pyqtSignal(str)
    mod_list_refresh_requested = pyqtSignal()
    issues_ignored_changed = pyqtSignal()

    def __init__(self, mod_manager: 'ModManager', user_config: 'UserConfigManager',
                 base_font_size: int = 14, config_manager: 'ConfigManager' = None, parent=None):
        super().__init__(parent)
        self.mod_manager = mod_manager
        self.user_config = user_config
        self.base_font_size = base_font_size
        self._config_manager = config_manager
        self._current_mod: Optional[Mod] = None
        self._updating_note_fields = False
        self._config = _get_info_panel_config()

        self._init_ui()

    def _init_ui(self):
        self.setMinimumWidth(self._config['min_width'])
        self.setMaximumWidth(self._config['max_width'])

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(self._config['margin'], self._config['margin'], self._config['margin'],
                                       self._config['margin'])
        main_layout.setSpacing(self._config['main_spacing'])

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(self.scroll_area.Shape.NoFrame)

        self.scroll_content = QWidget()
        self.scroll_content.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        scroll_layout = QVBoxLayout(self.scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(self._config['main_spacing'])

        self._create_basic_info_group(scroll_layout)
        self._create_file_info_group(scroll_layout)
        self._create_load_req_group(scroll_layout)
        self._create_official_tags_group(scroll_layout)
        self._create_tags_group(scroll_layout)
        self._create_color_group(scroll_layout)
        self._create_note_group(scroll_layout)
        self._create_ignore_issues_group(scroll_layout)
        self._create_description_group(scroll_layout)

        scroll_layout.addStretch()
        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area)

        self._refresh_styles()

    def _create_basic_info_group(self, scroll_layout):
        self.basic_group = QGroupBox(tr("group_basic_info"))
        self.basic_group.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
        basic_layout = QVBoxLayout(self.basic_group)
        basic_layout.setSpacing(self._config['form_spacing'])

        self.preview_image_label = QLabel()
        self.preview_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image_label.setScaledContents(False)
        self.preview_image_label.setMaximumHeight(self._config['preview_image_max_height'])
        self.preview_image_label.hide()
        basic_layout.addWidget(self.preview_image_label)

        form_layout = QFormLayout()
        form_layout.setSpacing(self._config['form_spacing'])
        form_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        label_min_width = self._config.get('form_label_min_width', 70)

        self.name_title_label = QLabel(tr("info_name") + ":")
        self.name_title_label.setMinimumWidth(label_min_width)
        self.name_label = ElidedLabel("--", copyable=True)
        self.name_label.setProperty("labelType", "info_name")
        self.name_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        form_layout.addRow(self.name_title_label, self.name_label)

        self.id_title_label = QLabel("ID:")
        self.id_title_label.setMinimumWidth(label_min_width)
        self.id_label = ElidedLabel("--", copyable=True)
        self.id_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        form_layout.addRow(self.id_title_label, self.id_label)

        self.type_container = QWidget()
        self.type_container.setProperty("widgetType", "transparent_container")
        self.type_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        type_layout = QHBoxLayout(self.type_container)
        type_layout.setContentsMargins(0, 0, 0, 0)
        type_layout.setSpacing(4)
        self.type_icon_label = QLabel()
        self.type_icon_label.setFixedSize(16, 16)
        self.type_icon_label.hide()
        type_layout.addWidget(self.type_icon_label)
        self.type_badge = ElidedLabel("--", copyable=True)
        self.type_badge.setProperty("badgeType", "type_local")
        type_layout.addWidget(self.type_badge)
        type_layout.addStretch()
        self.type_title_label = QLabel(tr("info_type") + ":")
        self.type_title_label.setMinimumWidth(label_min_width)
        form_layout.addRow(self.type_title_label, self.type_container)

        self.version_title_label = QLabel(tr("info_version") + ":")
        self.version_title_label.setMinimumWidth(label_min_width)
        self.version_badge = ElidedLabel("--", copyable=True)
        self.version_badge.setProperty("badgeType", "version")
        form_layout.addRow(self.version_title_label, self.version_badge)

        self.game_versions_container = QWidget()
        self.game_versions_container.setProperty("widgetType", "transparent_container")
        self.game_versions_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.game_versions_layout = FlowLayout(self.game_versions_container)
        self.game_versions_layout.setSpacing(4)
        self.game_version_title_label = QLabel(tr("info_game_version") + ":")
        self.game_version_title_label.setMinimumWidth(label_min_width)
        form_layout.addRow(self.game_version_title_label, self.game_versions_container)

        self.authors_container = QWidget()
        self.authors_container.setProperty("widgetType", "transparent_container")
        self.authors_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.authors_layout = FlowLayout(self.authors_container)
        self.authors_layout.setSpacing(4)
        self.author_title_label = QLabel(tr("info_author") + ":")
        self.author_title_label.setMinimumWidth(label_min_width)
        form_layout.addRow(self.author_title_label, self.authors_container)

        basic_layout.addLayout(form_layout)
        scroll_layout.addWidget(self.basic_group)

    def _create_file_info_group(self, scroll_layout):
        self.file_group = QGroupBox(tr("group_file_info"))
        self.file_group.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
        file_layout = QFormLayout(self.file_group)
        file_layout.setSpacing(6)
        file_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.path_label = ElidedLabel("----", copyable=True)
        self.path_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        file_layout.addRow(tr("info_path") + ":", self.path_label)
        font = self.path_label.font()
        font.setPointSize(get_calculated_font_size(self.base_font_size, FontSize.TINY))
        self.path_label.setFont(font)

        file_layout.addItem(QSpacerItem(0, 2))

        self.workshop_id_label = ElidedLabel("----", copyable=True)
        self.workshop_id_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        file_layout.addRow(tr("info_workshop_id") + ":", self.workshop_id_label)
        font = self.workshop_id_label.font()
        font.setPointSize(get_calculated_font_size(self.base_font_size, FontSize.TINY))
        self.workshop_id_label.setFont(font)

        btn_layout = QHBoxLayout()
        self._open_folder_btn = QPushButton(tr("open_folder"))
        self._open_folder_btn.setIcon(get_action_icon(ActionTypes.FOLDER, 14))
        self._open_folder_btn.clicked.connect(self._open_mod_folder)
        btn_layout.addWidget(self._open_folder_btn)
        self._open_workshop_btn = QPushButton(tr("open_workshop"))
        self._open_workshop_btn.setIcon(get_action_icon(ActionTypes.STEAM, 14))
        self._open_workshop_btn.clicked.connect(self._open_workshop_page)
        btn_layout.addWidget(self._open_workshop_btn)
        btn_layout.addStretch()
        file_layout.addRow(btn_layout)
        scroll_layout.addWidget(self.file_group)
        self.file_group.hide()

    def _open_mod_folder(self):
        ModUIUtils.open_mod_folder(self._current_mod)

    def _open_workshop_page(self):
        ModUIUtils.open_workshop_page(self._current_mod)

    @staticmethod
    def _create_dep_container():
        container = QWidget()
        container.setProperty("widgetType", "transparent_container")
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 0, 0, 0)
        layout.setSpacing(2)
        return container, layout

    def _create_load_req_group(self, scroll_layout):
        self.load_req_group = QGroupBox(tr("group_load_requirements"))
        self.load_req_group.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
        load_req_layout = QVBoxLayout(self.load_req_group)
        load_req_layout.setSpacing(4)

        self.depends_on_label = QLabel(tr("depends_on"))
        load_req_layout.addWidget(self.depends_on_label)
        self.depends_on_container, self.depends_on_layout = InfoPanel._create_dep_container()
        load_req_layout.addWidget(self.depends_on_container)

        self.load_before_label = QLabel(tr("load_before"))
        load_req_layout.addWidget(self.load_before_label)
        self.load_before_container, self.load_before_layout = InfoPanel._create_dep_container()
        load_req_layout.addWidget(self.load_before_container)

        self.load_after_label = QLabel(tr("load_after"))
        load_req_layout.addWidget(self.load_after_label)
        self.load_after_container, self.load_after_layout = InfoPanel._create_dep_container()
        load_req_layout.addWidget(self.load_after_container)

        self.incompatible_label = QLabel(tr("incompatible_with"))
        load_req_layout.addWidget(self.incompatible_label)
        self.incompatible_container, self.incompatible_layout = InfoPanel._create_dep_container()
        load_req_layout.addWidget(self.incompatible_container)
        scroll_layout.addWidget(self.load_req_group)
        self.load_req_group.hide()

    def _create_official_tags_group(self, scroll_layout):
        self.official_tags_group = QGroupBox(tr("info_official_tags"))
        self.official_tags_group.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
        official_tags_layout = QVBoxLayout(self.official_tags_group)
        official_tags_layout.setSpacing(self._config['form_spacing'])

        self.official_tags_container = QWidget()
        self.official_tags_container.setProperty("widgetType", "transparent_container")
        self.official_tags_flow_layout = FlowLayout(self.official_tags_container)
        self.official_tags_flow_layout.setSpacing(4)
        official_tags_layout.addWidget(self.official_tags_container)

        scroll_layout.addWidget(self.official_tags_group)
        self.official_tags_group.hide()

    def _create_tags_group(self, scroll_layout):
        self.tags_group = QGroupBox(tr("tag_management"))
        self.tags_group.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
        tags_layout = QVBoxLayout(self.tags_group)
        tags_layout.setSpacing(self._config['form_spacing'])

        self.tags_container = QWidget()
        self.tags_container.setMinimumHeight(30)
        self.tags_container.setObjectName("info_tags_container")
        self.tags_container.setProperty("widgetType", "info_tags_container")
        self.tags_flow_layout = FlowLayout(self.tags_container)
        self.tags_flow_layout.setSpacing(4)
        tags_layout.addWidget(self.tags_container)

        add_tag_layout = QHBoxLayout()
        self.tag_combo = QComboBox()
        self.tag_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.tag_combo.setMinimumWidth(self._config['tag_combo_min_width'])
        self.tag_combo.setProperty("comboBoxType", "tag")
        self.tag_combo.installEventFilter(self)
        self._refresh_tag_combo()
        self.tag_combo.currentIndexChanged.connect(self._on_tag_combo_changed)
        add_tag_layout.addWidget(self.tag_combo)

        self.custom_tag_input = QLineEdit()
        self.custom_tag_input.setPlaceholderText(tr("enter_tag_name"))
        self.custom_tag_input.setProperty("inputType", "custom_tag")
        self.custom_tag_input.returnPressed.connect(self._add_custom_tag_from_input)
        add_tag_layout.addWidget(self.custom_tag_input)
        tags_layout.addLayout(add_tag_layout)
        scroll_layout.addWidget(self.tags_group)
        self.tags_group.hide()

    def _create_color_group(self, scroll_layout):
        self.color_group = QGroupBox(tr("color_settings"))
        self.color_group.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
        self.color_grid = QGridLayout()
        self.color_grid.setSpacing(self._config['margin'])
        self.color_grid.setContentsMargins(self._config['margin'], 16, self._config['margin'], self._config['margin'])
        self._refresh_color_buttons()
        self.color_group.setLayout(self.color_grid)
        scroll_layout.addWidget(self.color_group)
        self.color_group.hide()

    def _create_note_group(self, scroll_layout):
        self.note_group = QGroupBox(tr("note_settings"))
        self.note_group.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
        note_layout = QVBoxLayout(self.note_group)
        note_layout.setSpacing(self._config['margin'])

        custom_name_layout = QHBoxLayout()
        self.custom_name_label = QLabel(tr("custom_name") + ":")
        self.custom_name_label.setMinimumWidth(self._config['custom_name_label_min_width'])
        self.custom_name_edit = QLineEdit()
        self.custom_name_edit.setPlaceholderText(tr("custom_name_placeholder"))
        self.custom_name_edit.textChanged.connect(self._on_custom_name_changed)
        custom_name_layout.addWidget(self.custom_name_label)
        custom_name_layout.addWidget(self.custom_name_edit)
        note_layout.addLayout(custom_name_layout)

        self.original_name_label = QLabel("")
        note_layout.addWidget(self.original_name_label)

        note_input_layout = QVBoxLayout()
        note_input_layout.setSpacing(2)
        self.note_label = QLabel(tr("note") + ":")
        self.note_edit = QTextEdit()
        self.note_edit.setPlaceholderText(tr("note_placeholder"))
        self.note_edit.setMaximumHeight(self._config['note_edit_max_height'])
        self.note_edit.textChanged.connect(self._on_note_changed)
        note_input_layout.addWidget(self.note_label)
        note_input_layout.addWidget(self.note_edit)
        note_layout.addLayout(note_input_layout)
        scroll_layout.addWidget(self.note_group)
        self.note_group.hide()

    def _create_ignore_issues_group(self, scroll_layout):
        self.ignore_issues_group = QGroupBox(tr("ignore_issues"))
        self.ignore_issues_group.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
        ignore_layout = QVBoxLayout(self.ignore_issues_group)
        ignore_layout.setSpacing(self._config['form_spacing'])

        self.issues_container = QWidget()
        self.issues_container.setMinimumHeight(30)
        self.issues_container.setProperty("widgetType", "info_tags_container")
        self.issues_flow_layout = FlowLayout(self.issues_container)
        self.issues_flow_layout.setSpacing(4)
        ignore_layout.addWidget(self.issues_container)

        scroll_layout.addWidget(self.ignore_issues_group)
        self.ignore_issues_group.hide()

    def _create_description_group(self, scroll_layout):
        self.description_group = QGroupBox(tr("description"))
        self.description_group.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Minimum)
        desc_layout = QVBoxLayout(self.description_group)
        desc_layout.setSpacing(4)

        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        desc_layout.addWidget(self.description_label)
        scroll_layout.addWidget(self.description_group)
        self.description_group.hide()

    def _set_font_size(self, widget, font_size: FontSize, bold: bool = False):
        font = widget.font()
        font.setPointSize(get_calculated_font_size(self.base_font_size, font_size))
        if bold:
            font.setBold(True)
        widget.setFont(font)

    def _refresh_styles(self):
        self.setProperty("widgetType", "info_panel")
        self.scroll_area.setProperty("scrollAreaType", "info_panel")

        self._set_font_size(self.scroll_content, FontSize.BASE)

        refresh_widgets_style(
            self.basic_group, self.file_group, self.load_req_group,
            self.official_tags_group, self.tags_group, self.color_group, self.note_group,
            self.description_group, self.ignore_issues_group,
            self.tags_container, self.issues_container, self.official_tags_container
        )

        for label in [self.name_title_label, self.id_title_label, self.type_title_label,
                      self.version_title_label, self.game_version_title_label, self.author_title_label]:
            self._set_font_size(label, FontSize.TINY)

        self.name_label.setProperty("labelType", "info_name")
        self._set_font_size(self.name_label, FontSize.LARGE, bold=True)
        refresh_widget_style(self.name_label)

        if self._current_mod:
            match self._current_mod.mod_type:
                case ModType.CORE:
                    self.type_badge.setProperty("badgeType", "type_core")
                case ModType.DLC:
                    self.type_badge.setProperty("badgeType", "type_dlc")
                case ModType.WORKSHOP:
                    self.type_badge.setProperty("badgeType", "type_workshop")
                case _:
                    self.type_badge.setProperty("badgeType", "type_local")
        refresh_widget_style(self.type_badge)

        self.version_badge.setProperty("badgeType", "version")
        refresh_widgets_style(self.version_badge, self._open_folder_btn, self._open_workshop_btn)

        for btn in [self._open_folder_btn, self._open_workshop_btn]:
            self._set_font_size(btn, FontSize.TINY)

        for label in [self.depends_on_label, self.load_before_label, self.load_after_label, self.incompatible_label]:
            label.setProperty("labelType", "dep_label")
            self._set_font_size(label, FontSize.TINY)

        refresh_widget_style(self.custom_name_edit)

        for label in [self.custom_name_label, self.note_label]:
            self._set_font_size(label, FontSize.TINY)

        self.original_name_label.setProperty("labelType", "original_name")
        self._set_font_size(self.original_name_label, FontSize.SMALL)

        self.note_edit.setProperty("textEditType", "note_edit")

        InfoPanel._refresh_dep_item_styles(self.depends_on_layout)
        InfoPanel._refresh_dep_item_styles(self.load_before_layout)
        InfoPanel._refresh_dep_item_styles(self.load_after_layout)
        InfoPanel._refresh_dep_item_styles(self.incompatible_layout)
        refresh_widgets_style(self.tag_combo, self.custom_tag_input)

    @staticmethod
    def _refresh_dep_item_styles(layout):
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if item and item.widget():
                dep_row = item.widget()
                name_label = dep_row.findChild(QLabel)
                is_missing = "❌" in name_label.text() if name_label else False
                dep_row.setProperty("widgetType", "dep_row")
                dep_row.setProperty("isMissing", "true" if is_missing else "false")
                refresh_widget_style(dep_row)
                if name_label:
                    name_label.setProperty("labelType", "dep_missing" if is_missing else "dep_normal")
                    refresh_widget_style(name_label)

    def _on_tag_combo_changed(self, index: int):
        if not self._current_mod or index <= 0:
            return
        tag = self.tag_combo.itemData(index)
        if tag and tag not in self._current_mod.tags:
            self.tag_combo.blockSignals(True)
            self.tag_combo.setCurrentIndex(0)
            self.tag_combo.blockSignals(False)
            self.mod_manager.add_tag_to_mod(self._current_mod.id, tag)
            self._refresh_tags_display()
            self.tags_changed.emit()
        else:
            self.tag_combo.setCurrentIndex(0)

    def eventFilter(self, obj, event):
        if obj == self.tag_combo and event.type() == QEvent.Type.Wheel:
            return True
        return super().eventFilter(obj, event)

    def _add_custom_tag_from_input(self):
        if not self._current_mod:
            return
        tag = self.custom_tag_input.text().strip()
        if not tag:
            return
        if tag in self._current_mod.tags:
            self.custom_tag_input.clear()
            return
        self.mod_manager.add_tag_to_mod(self._current_mod.id, tag)
        self.custom_tag_input.clear()
        self._refresh_tags_display()
        self.tags_changed.emit()

    def _create_tag_button(self, tag: str) -> QPushButton:
        tag_color = self.user_config.get_tag_color(tag) or get_color('tag_default')
        display_tag = tr(tag) if tag.startswith("tag_") else tag
        btn = TagButton(display_tag, tag_color, self.base_font_size)
        btn.setToolTip(tr("click_to_remove_tag"))
        btn.clicked.connect(lambda checked, t=tag: self._remove_tag_from_mod(t))
        return btn

    def _refresh_official_tags_display(self, mod: Mod):
        self.official_tags_flow_layout.clear()

        if not self._is_section_visible("official_tags"):
            self.official_tags_group.hide()
            return

        if not mod.official_tags:
            self.official_tags_group.hide()
            return

        self.official_tags_group.show()

        for tag in mod.official_tags:
            badge = ElidedLabel(str(tag), copyable=True)
            badge.setProperty("badgeType", "official_tag")
            refresh_widget_style(badge)
            badge.adjustSize()
            self.official_tags_flow_layout.addWidget(badge)

        QTimer.singleShot(0, self._delayed_official_tags_layout_update)

    def _delayed_official_tags_layout_update(self):
        self.official_tags_flow_layout.invalidate()
        self.official_tags_container.updateGeometry()
        if self.official_tags_group:
            self.official_tags_group.updateGeometry()
        self.scroll_content.updateGeometry()
        self.scroll_area.updateGeometry()

    def _refresh_tags_display(self):
        self.tags_flow_layout.clear()

        if not self._is_section_visible("tags"):
            self.tags_group.hide()
            return

        if not self._current_mod:
            self.tags_group.hide()
            return

        self.tags_group.show()

        if self._current_mod.tags:
            for tag in sorted(self._current_mod.tags):
                btn = self._create_tag_button(tag)
                self.tags_flow_layout.addWidget(btn)
        else:
            no_tags_label = QLabel(tr("no_tags"))
            no_tags_label.setProperty("labelType", "no_tags")
            font = no_tags_label.font()
            font.setPointSize(get_calculated_font_size(self.base_font_size, FontSize.TINY))
            no_tags_label.setFont(font)
            self.tags_flow_layout.addWidget(no_tags_label)
        QTimer.singleShot(0, self._delayed_layout_update)

    def _refresh_issues_display(self):
        self.issues_flow_layout.clear()

        if not self._is_section_visible("ignore_issues"):
            self.ignore_issues_group.hide()
            return

        if not self._current_mod:
            self.ignore_issues_group.hide()
            return

        for issue_status in EnumExtension.PREDEFINE_MOD_ISSUES_STATUS:
            display_name = tr(EnumExtension.get_issue_label_key(issue_status))
            is_ignored = self._current_mod.custom_meta.is_issue_ignored(issue_status)
            has_issue = self._current_mod.has_issue(issue_status)
            btn = IssueBadgeButton(
                issue_status=issue_status,
                display_name=display_name,
                is_ignored=is_ignored,
                base_font_size=self.base_font_size,
                has_issue=has_issue
            )
            btn.clicked.connect(lambda checked, s=issue_status: self._toggle_issue_ignore(s))
            self.issues_flow_layout.addWidget(btn)

        self.ignore_issues_group.show()
        QTimer.singleShot(0, self._delayed_issues_layout_update)

    def _delayed_issues_layout_update(self):
        self.issues_flow_layout.invalidate()
        self.issues_container.updateGeometry()
        if self.ignore_issues_group:
            self.ignore_issues_group.updateGeometry()
        self.scroll_content.updateGeometry()
        self.scroll_area.updateGeometry()

    def _toggle_issue_ignore(self, issue_status: ModIssueStatus):
        if not self._current_mod:
            return

        is_currently_ignored = self._current_mod.custom_meta.is_issue_ignored(issue_status)
        self.mod_manager.set_mod_ignored_issue(
            self._current_mod.id,
            issue_status,
            not is_currently_ignored
        )
        QTimer.singleShot(10, self._refresh_issues_display)
        QTimer.singleShot(20, lambda: self.issues_ignored_changed.emit())

    def _delayed_layout_update(self):
        self.tags_flow_layout.invalidate()
        self.tags_container.updateGeometry()
        if self.tags_group:
            self.tags_group.updateGeometry()
        self.scroll_content.updateGeometry()
        self.scroll_area.updateGeometry()

    def _remove_tag_from_mod(self, tag: str):
        if not self._current_mod:
            return
        if tag in self._current_mod.tags:
            self.mod_manager.remove_tag_from_mod(self._current_mod.id, tag)
            self._refresh_tags_display()
            self.tags_changed.emit()

    def set_mod_color(self, color: Optional[str], mod_id: Optional[str] = None):
        target_id = mod_id or (self._current_mod.id if self._current_mod else None)
        if not target_id:
            return
        if self.mod_manager.set_mod_color(target_id, color):
            self.color_changed.emit(target_id, color)
            if self._current_mod and self._current_mod.id == target_id:
                self.set_current_mod(self._current_mod)

    def _on_custom_name_changed(self, text: str):
        if self._updating_note_fields or not self._current_mod:
            return
        self.mod_manager.set_mod_custom_name(self._current_mod.id, text.strip() if text.strip() else None)
        self.custom_name_changed.emit()

    def _on_note_changed(self):
        if self._updating_note_fields or not self._current_mod:
            return
        text = self.note_edit.toPlainText()
        self.mod_manager.set_mod_note(self._current_mod.id, text.strip() if text.strip() else None)
        self.note_changed.emit()

    def _add_custom_color(self):
        from PyQt6.QtWidgets import QColorDialog
        color = QColorDialog.getColor()
        if color.isValid():
            color_hex = color.name()
            self.user_config.add_color(f"custom_{color_hex}", color_hex)
            self._refresh_color_buttons()
            if self._current_mod:
                self.set_current_mod(self._current_mod)

    def _refresh_color_buttons(self):
        while self.color_grid.count():
            item = self.color_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        col, row, max_cols = 0, 0, 6
        default_colors = {c.color.lower() for c in self.user_config.DEFAULT_COLORS}

        for color_option in self.user_config.get_enabled_colors():
            btn = ColorButton(color_option.color)
            btn.setToolTip(tr(color_option.name_key))
            btn.clicked.connect(lambda checked, c=color_option.color: self.set_mod_color(c))
            self.color_grid.addWidget(btn, row, col)

            if color_option.color.lower() not in default_colors:
                delete_btn = QPushButton("×")
                delete_btn.setFixedSize(12, 12)
                delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
                delete_btn.setProperty("buttonType", "delete_color")
                delete_btn.clicked.connect(lambda checked, c=color_option.color: self._delete_custom_color(c))
                self.color_grid.addWidget(delete_btn, row, col, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

            col += 1
            if col >= max_cols:
                col, row = 0, row + 1

        add_color_btn = AddColorButton(self.base_font_size)
        add_color_btn.setToolTip(tr("add_custom_color"))
        add_color_btn.clicked.connect(self._add_custom_color)
        self.color_grid.addWidget(add_color_btn, row, col)
        col += 1
        if col >= max_cols:
            col, row = 0, row + 1

        clear_color_btn = ClearColorButton(self.base_font_size)
        clear_color_btn.setToolTip(tr("clear"))
        clear_color_btn.clicked.connect(lambda: self.set_mod_color(None))
        self.color_grid.addWidget(clear_color_btn, row, col)

    def _delete_custom_color(self, color: str):
        self.user_config.remove_color(color)
        self._refresh_color_buttons()

    def copy_mod_name(self, mod_id: str, button: QPushButton = None):
        if not mod_id:
            return
        mod = self.mod_manager.get_mod_by_id(mod_id)
        text = mod.display_name if mod else mod_id
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        if button:
            global_pos = button.mapToGlobal(button.rect().center())
            ToastManager.show_at_click(tr("copied_to_clipboard").format(text), global_pos, duration=2000)
        else:
            ToastManager.show(tr("copied_to_clipboard").format(text), duration=2000)

    def _locate_mod(self, mod_id: str):
        self.locate_mod_requested.emit(mod_id)

    def _create_dep_row(self, dep_id, is_missing=False):
        actual_mod_id = dep_id
        if self.mod_manager.id_comparer and self.mod_manager.id_comparer.has_original_id(dep_id):
            resolved = self.mod_manager.id_comparer.resolve_original_id(dep_id)
            if resolved:
                actual_mod_id = resolved
        dep_mod = self.mod_manager.get_mod_by_id(actual_mod_id)
        is_missing = is_missing or (dep_mod is None)
        dep_row = QWidget()
        dep_row.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        dep_row.setProperty("widgetType", "dep_row")
        dep_row.setProperty("isMissing", "true" if is_missing else "false")
        dep_row_layout = QHBoxLayout(dep_row)
        dep_row_layout.setContentsMargins(4, 2, 4, 2)
        dep_row_layout.setSpacing(2)

        name_label = QLabel()
        name_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        name_label.setTextFormat(Qt.TextFormat.PlainText)
        name_font = name_label.font()
        name_font.setPointSize(get_calculated_font_size(self.base_font_size, FontSize.TINY))
        name_label.setFont(name_font)
        if dep_mod:
            display_text = f"📦 {dep_mod.display_name}"
            name_label.setProperty("labelType", "dep_normal")
        else:
            display_text = f"❌ {dep_id}"
            name_label.setProperty("labelType", "dep_missing")
        name_label.setText(display_text)
        name_label.setToolTip(display_text)
        dep_row_layout.addWidget(name_label, 1)

        copy_icon = get_action_icon(ActionTypes.COPY, 14)
        copy_btn = QPushButton()
        copy_btn.setIcon(copy_icon)
        copy_btn.setFixedSize(20, 20)
        copy_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        copy_btn.setProperty("buttonType", "icon_btn")
        copy_btn.clicked.connect(lambda checked, d=actual_mod_id, btn=copy_btn: self.copy_mod_name(d, btn))
        dep_row_layout.addWidget(copy_btn)

        locate_icon = get_action_icon(ActionTypes.LOCATE, 14)
        locate_btn = QPushButton()
        locate_btn.setIcon(locate_icon)
        locate_btn.setFixedSize(20, 20)
        locate_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        locate_btn.setProperty("buttonType", "icon_btn")
        if dep_mod:
            locate_btn.clicked.connect(lambda checked, d=actual_mod_id: self._locate_mod(d))
        else:
            locate_btn.setEnabled(False)
            locate_btn.setProperty("isMissing", "true")
        dep_row_layout.addWidget(locate_btn)

        refresh_widget_style(dep_row)
        return dep_row

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    @staticmethod
    def _clear_flow_layout(layout: FlowLayout):
        layout.clear()

    def _update_geometry_after_mod_set(self):
        self.game_versions_container.updateGeometry()
        self.authors_container.updateGeometry()
        self.basic_group.updateGeometry()
        self.scroll_content.updateGeometry()

        QTimer.singleShot(0, self._force_layout_update)

    def _force_layout_update(self):
        self.authors_layout.update()
        self.game_versions_layout.update()
        self.authors_container.update()
        self.game_versions_container.update()

    def _is_section_visible(self, section_key: str) -> bool:
        if self._config_manager:
            return self._config_manager.is_info_panel_section_visible(section_key)
        return True

    def set_current_mod(self, mod: Optional[Mod]):
        self._current_mod = mod

        if mod is None:
            self.name_label.setText("--")
            self.id_label.setText("--")
            self.type_badge.setText("--")
            self.type_icon_label.hide()
            self.version_badge.setText("--")
            InfoPanel._clear_flow_layout(self.game_versions_layout)
            InfoPanel._clear_flow_layout(self.authors_layout)
            self.path_label.setText("----")
            self.workshop_id_label.setText("----")
            self._open_workshop_btn.setVisible(False)
            self.preview_image_label.hide()
            self.preview_image_label.clear()
            self.file_group.hide()
            self.load_req_group.hide()
            self.depends_on_label.hide()
            self.depends_on_container.hide()
            self.load_before_label.hide()
            self.load_before_container.hide()
            self.load_after_label.hide()
            self.load_after_container.hide()
            self.incompatible_label.hide()
            self.incompatible_container.hide()
            self.official_tags_group.hide()
            self.tags_group.hide()
            while self.tags_flow_layout.count():
                item = self.tags_flow_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.color_group.hide()
            self.note_group.hide()
            while self.issues_flow_layout.count():
                item = self.issues_flow_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            self.ignore_issues_group.hide()
            self._updating_note_fields = True
            self.custom_name_edit.setText("")
            self.note_edit.setPlainText("")
            self.original_name_label.setText("")
            self._updating_note_fields = False
            self.description_group.hide()
            self.description_label.clear()
            return

        self.name_label.setText(mod.display_name)
        self.id_label.setText(mod.original_id)

        if mod.preview_image and os.path.exists(mod.preview_image):
            pixmap = QPixmap(mod.preview_image)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaledToHeight(200, Qt.TransformationMode.SmoothTransformation)
                self.preview_image_label.setPixmap(scaled_pixmap)
                self.preview_image_label.show()
            else:
                self.preview_image_label.hide()
        else:
            self.preview_image_label.hide()

        type_icon = get_mod_type_icon(mod.mod_type, 16)
        self.type_icon_label.setPixmap(type_icon.pixmap(16, 16))
        self.type_icon_label.show()
        if mod.mod_type == ModType.CORE:
            self.type_badge.setText(tr("mod_type_core"))
            self.type_badge.setProperty("badgeType", "type_core")
        elif mod.mod_type == ModType.DLC:
            self.type_badge.setText(tr("mod_type_dlc"))
            self.type_badge.setProperty("badgeType", "type_dlc")
        elif mod.mod_type == ModType.WORKSHOP:
            self.type_badge.setText(tr("mod_type_workshop"))
            self.type_badge.setProperty("badgeType", "type_workshop")
        else:
            self.type_badge.setText(tr("mod_type_local"))
            self.type_badge.setProperty("badgeType", "type_local")

        self.version_badge.setText(mod.version or tr("unknown"))
        self.version_badge.setProperty("badgeType", "version")

        InfoPanel._clear_flow_layout(self.game_versions_layout)
        versions_to_show = mod.supported_versions if mod.supported_versions else [tr("unknown")]
        for ver in versions_to_show:
            badge = ElidedLabel(str(ver), copyable=True)
            badge.setProperty("badgeType", "version")
            refresh_widget_style(badge)
            badge.adjustSize()
            self.game_versions_layout.addWidget(badge)

        InfoPanel._clear_flow_layout(self.authors_layout)
        authors_to_show = mod.authors if mod.authors else [tr("unknown")]
        for author in authors_to_show:
            badge = ElidedLabel(str(author), copyable=True)
            badge.setProperty("badgeType", "author")
            refresh_widget_style(badge)
            badge.adjustSize()
            self.authors_layout.addWidget(badge)

        self._refresh_official_tags_display(mod)

        self.path_label.setText(mod.path)
        if mod.mod_type == ModType.WORKSHOP and mod.workshop_id is not None:
            self.workshop_id_label.setText(mod.workshop_id)
            self._open_workshop_btn.setVisible(True)
        else:
            self._open_workshop_btn.setVisible(False)

        if self._is_section_visible("file_info"):
            self.file_group.show()
        else:
            self.file_group.hide()

        if self._is_section_visible("load_requirements"):
            self.load_req_group.show()
        else:
            self.load_req_group.hide()

        InfoPanel._clear_layout(self.depends_on_layout)
        InfoPanel._clear_layout(self.load_before_layout)
        InfoPanel._clear_layout(self.load_after_layout)
        InfoPanel._clear_layout(self.incompatible_layout)

        if mod.depended_modules:
            for dep_id in mod.depended_modules:
                self.depends_on_layout.addWidget(self._create_dep_row(dep_id))
            self.depends_on_label.show()
            self.depends_on_container.show()
        else:
            self.depends_on_label.hide()
            self.depends_on_container.hide()

        if mod.load_before:
            for dep_id in mod.load_before:
                self.load_before_layout.addWidget(self._create_dep_row(dep_id))
            self.load_before_label.show()
            self.load_before_container.show()
        else:
            self.load_before_label.hide()
            self.load_before_container.hide()

        if mod.load_after:
            for dep_id in mod.load_after:
                self.load_after_layout.addWidget(self._create_dep_row(dep_id))
            self.load_after_label.show()
            self.load_after_container.show()
        else:
            self.load_after_label.hide()
            self.load_after_container.hide()

        if mod.incompatible_modules:
            for dep_id in mod.incompatible_modules:
                self.incompatible_layout.addWidget(self._create_dep_row(dep_id))
            self.incompatible_label.show()
            self.incompatible_container.show()
        else:
            self.incompatible_label.hide()
            self.incompatible_container.hide()

        self._refresh_tags_display()
        self._refresh_issues_display()

        if self._is_section_visible("color"):
            self.color_group.show()
        else:
            self.color_group.hide()

        if self._is_section_visible("note"):
            self.note_group.show()
        else:
            self.note_group.hide()

        self._updating_note_fields = True
        self.custom_name_edit.setText(mod.custom_name or "")
        self.note_edit.setPlainText(mod.note or "")
        self.original_name_label.setText(f"({tr('original_name')}: {mod.name})" if mod.custom_name else "")
        self._updating_note_fields = False

        if self._is_section_visible("description") and mod.description:
            self.description_label.setText(mod.description)
            self.description_label.setProperty("labelType", "description")
            font = self.description_label.font()
            font.setPointSize(get_calculated_font_size(self.base_font_size, FontSize.BASE))
            self.description_label.setFont(font)
            self.description_group.show()
        else:
            self.description_group.hide()

        self._refresh_styles()
        self._update_geometry_after_mod_set()

    def get_current_mod_id(self) -> Optional[str]:
        return self._current_mod.id if self._current_mod else None

    def _refresh_tag_combo(self):
        self.tag_combo.blockSignals(True)
        self.tag_combo.clear()
        self.tag_combo.addItem(tr("common_tags"), None)
        first_item = self.tag_combo.model().item(0)
        if first_item:
            first_item.setFlags(first_item.flags() & ~Qt.ItemFlag.ItemIsSelectable & ~Qt.ItemFlag.ItemIsEnabled)
        for tag_config in self.user_config.get_enabled_tags():
            display_name = tr(tag_config.name) if tag_config.name.startswith("tag_") else tag_config.name
            self.tag_combo.addItem(display_name, tag_config.name)
        self.tag_combo.setCurrentIndex(0)
        self.tag_combo.blockSignals(False)

    def refresh_theme(self):
        self._refresh_styles()
        self._refresh_tags_display()
        self._refresh_issues_display()
        self._refresh_color_buttons()
        self._refresh_tag_combo()
        if self._current_mod:
            self.set_current_mod(self._current_mod)
