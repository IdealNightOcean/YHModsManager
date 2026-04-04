"""
设置对话框模块
包含标签管理、颜色管理、语言设置等UI
"""

import logging
import os
import random
from typing import Dict

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QFontMetrics
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QColorDialog, QLineEdit,
    QWidget, QFormLayout, QComboBox, QMessageBox, QSpinBox, QStackedWidget, QScrollArea
)

from core import TagConfig, ColorOption, get_user_config
from plugin_system.plugin_loader import get_plugin_loader, PluginType
from utils.icons import get_icon
from ..i18n import Language, tr, get_i18n
from ..styles import get_calculated_font_size, refresh_widget_style, FontSize, get_ui_constant
from ..theme_manager import get_color, get_theme_manager, get_dependency_colors

logger = logging.getLogger(__name__)


def generate_random_color() -> str:
    colors = get_dependency_colors()
    return random.choice(colors)


class EnableToggleWidget(QWidget):
    """启用/禁用切换控件，使用SVG图标"""

    toggled = pyqtSignal(bool)

    def __init__(self, parent=None, enabled: bool = True, icon_size: int = 16):
        super().__init__(parent)
        self._enabled = enabled
        self._icon_size = icon_size
        self._hover = False
        self._setup_ui()

    def _setup_ui(self):
        self.setFixedSize(90, 32)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setProperty("widgetType", "enable_toggle")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(8)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(self._icon_size, self._icon_size)
        layout.addWidget(self.icon_label)

        self.text_label = QLabel()
        self.text_label.setProperty("labelType", "toggle_text")
        layout.addWidget(self.text_label)
        layout.addStretch()

        self._update_display()
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _update_display(self):
        icon = get_icon('check_circle' if self._enabled else 'remove_circle',
                        get_color('success') if self._enabled else get_color('error'),
                        self._icon_size)
        self.icon_label.setPixmap(icon.pixmap(self._icon_size, self._icon_size))

        self.text_label.setText(tr("enabled") if self._enabled else tr("disabled"))
        self.text_label.setProperty("toggleState", "enabled" if self._enabled else "disabled")
        refresh_widget_style(self.text_label)

        self._update_style()

    def _update_style(self):
        self.setProperty("toggleState", "enabled" if self._enabled else "disabled")
        self.setProperty("hoverState", "true" if self._hover else "false")
        refresh_widget_style(self)

    def isChecked(self) -> bool:
        return self._enabled

    def setChecked(self, enabled: bool):
        if self._enabled != enabled:
            self._enabled = enabled
            self._update_display()
            self.toggled.emit(enabled)

    def enterEvent(self, event):
        self._hover = True
        self._update_style()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self._update_style()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._enabled)
        super().mousePressEvent(event)


class ColorPickerMixin:
    current_color: str = None
    color_preview: QPushButton = None
    color_edit: QLineEdit = None

    @staticmethod
    def _get_default_color() -> str:
        return get_dependency_colors()[0]

    def _setup_color_picker(self, initial_color: str = None):
        if initial_color is None:
            initial_color = self._get_default_color()
        self.current_color = initial_color
        color_layout = QHBoxLayout()

        self.color_preview = QPushButton()
        self.color_preview.setFixedSize(40, 30)
        self.color_preview.setProperty("buttonType", "color_preview")
        self._update_color_preview()
        self.color_preview.clicked.connect(self._choose_color)
        color_layout.addWidget(self.color_preview)

        self.color_edit = QLineEdit(self.current_color)
        self.color_edit.textChanged.connect(self._on_color_text_changed)
        color_layout.addWidget(self.color_edit)

        return color_layout

    def _update_color_preview(self):
        from PyQt6.QtGui import QPalette
        palette = self.color_preview.palette()
        palette.setColor(QPalette.ColorRole.Button, QColor(self.current_color))
        self.color_preview.setPalette(palette)
        self.color_preview.setAutoFillBackground(True)

    def _choose_color(self):
        color = QColorDialog.getColor(QColor(self.current_color), self)
        if color.isValid():
            self.current_color = color.name()
            self.color_edit.setText(self.current_color)
            self._update_color_preview()

    def _on_color_text_changed(self, text):
        if len(text) == 7 and text.startswith("#"):
            try:
                int(text[1:], 16)
                self.current_color = text
                self._update_color_preview()
            except ValueError:
                logger.debug(f"Invalid color format: {text}")


class TagEditDialog(QDialog, ColorPickerMixin):
    """标签编辑对话框"""

    def __init__(self, parent=None, tag: TagConfig = None):
        super().__init__(parent)
        self.tag = tag
        self.result_tag = None
        self._setup_ui()

    def _setup_ui(self):
        if self.tag:
            self.setWindowTitle(tr("edit"))
        else:
            self.setWindowTitle(tr("add"))

        self.setMinimumWidth(300)

        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        if self.tag:
            self.name_edit.setText(self.tag.name)
            self.name_edit.setEnabled(False)
        name_label = QLabel(tr("tag_name") + ":")
        name_label.setProperty("labelType", "settings_form_label")
        refresh_widget_style(name_label)
        layout.addRow(name_label, self.name_edit)

        initial_color = self.tag.color if self.tag else generate_random_color()
        color_layout = self._setup_color_picker(initial_color)
        color_label = QLabel(tr("color_settings") + ":")
        color_label.setProperty("labelType", "settings_form_label")
        refresh_widget_style(color_label)
        layout.addRow(color_label, color_layout)

        self.enabled_toggle = EnableToggleWidget(enabled=True if not self.tag else self.tag.enabled)
        layout.addRow("", self.enabled_toggle)

        btn_layout = QHBoxLayout()

        save_btn = QPushButton(tr("save"))
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton(tr("cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addRow("", btn_layout)

    def _on_save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, tr("error_title"), tr("tag_name_empty"))
            return

        # Check for duplicate tag name (only when adding new tag)
        if not self.tag:
            user_config = get_user_config()
            if user_config.get_tag(name):
                QMessageBox.warning(self, tr("error_title"), tr("tag_exists"))
                return

        self.result_tag = TagConfig(
            name=name,
            color=self.current_color,
            enabled=self.enabled_toggle.isChecked()
        )
        self.accept()

    def get_result(self) -> TagConfig:
        return self.result_tag


class ColorEditDialog(QDialog, ColorPickerMixin):
    """颜色编辑对话框"""

    def __init__(self, parent=None, color_option: ColorOption = None):
        super().__init__(parent)
        self.color_option = color_option
        self.result_color = None
        self._setup_ui()

    def _setup_ui(self):
        if self.color_option:
            self.setWindowTitle(tr("edit"))
        else:
            self.setWindowTitle(tr("add"))

        self.setMinimumWidth(300)

        layout = QFormLayout(self)

        self.name_edit = QLineEdit()
        if self.color_option and self.color_option.custom_name:
            self.name_edit.setText(self.color_option.custom_name)
        name_label = QLabel(tr("color_name") + ":")
        name_label.setProperty("labelType", "settings_form_label")
        refresh_widget_style(name_label)
        layout.addRow(name_label, self.name_edit)

        initial_color = self.color_option.color if self.color_option else self._get_default_color()
        color_layout = self._setup_color_picker(initial_color)
        color_label = QLabel(tr("color_settings") + ":")
        color_label.setProperty("labelType", "settings_form_label")
        refresh_widget_style(color_label)
        layout.addRow(color_label, color_layout)

        self.enabled_toggle = EnableToggleWidget(enabled=True if not self.color_option else self.color_option.enabled)
        layout.addRow("", self.enabled_toggle)

        btn_layout = QHBoxLayout()

        save_btn = QPushButton(tr("save"))
        save_btn.clicked.connect(self._on_save)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton(tr("cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addRow("", btn_layout)

    def _on_save(self):
        name_key = f"custom_color_{self.current_color[1:]}"
        if self.color_option:
            name_key = self.color_option.name_key

        custom_name = self.name_edit.text().strip()

        self.result_color = ColorOption(
            name_key=name_key,
            color=self.current_color,
            enabled=self.enabled_toggle.isChecked(),
            custom_name=custom_name
        )
        self.accept()

    def get_result(self) -> ColorOption:
        return self.result_color


class TagsTab(QWidget):
    """常用标签管理标签页"""

    config_changed = pyqtSignal()

    def __init__(self, parent=None, base_font_size=12, mod_metadata=None):
        super().__init__(parent)
        self.user_config = get_user_config()
        self._base_font_size = base_font_size
        self._mod_metadata = mod_metadata or {}
        self._setup_ui()
        self._refresh_list()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        info_label = QLabel(tr("tag_management"))
        info_label.setProperty("labelType", "settings_title")
        refresh_widget_style(info_label)
        layout.addWidget(info_label)

        self.tag_list = QListWidget()
        self.tag_list.setAlternatingRowColors(True)
        self.tag_list.setItemDelegate(TagListDelegate(self.tag_list, self._base_font_size))
        self.tag_list.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self.tag_list)

        btn_layout = QHBoxLayout()

        add_btn = QPushButton(tr("add"))
        add_btn.setIcon(get_icon('add', get_color('text'), 16))
        add_btn.clicked.connect(self._on_add)
        add_btn.setProperty("buttonType", "standard")
        btn_layout.addWidget(add_btn)

        edit_btn = QPushButton(tr("edit"))
        edit_btn.setIcon(get_icon('edit_calendar', get_color('text'), 16))
        edit_btn.clicked.connect(self._on_edit)
        edit_btn.setProperty("buttonType", "standard")
        btn_layout.addWidget(edit_btn)

        self.remove_btn = QPushButton(tr("delete"))
        self.remove_btn.setIcon(get_icon('auto_delete', get_color('danger'), 16))
        self.remove_btn.clicked.connect(self._on_remove)
        self.remove_btn.setProperty("buttonType", "danger")
        btn_layout.addWidget(self.remove_btn)

        reset_btn = QPushButton(tr("reset"))
        reset_btn.setIcon(get_icon('history', get_color('text'), 16))
        reset_btn.clicked.connect(self._on_reset)
        reset_btn.setProperty("buttonType", "standard")
        btn_layout.addWidget(reset_btn)

        layout.addLayout(btn_layout)

    @staticmethod
    def _get_tag_display_name(tag_name: str) -> str:
        if tag_name.startswith("tag_"):
            return tr(tag_name)
        return tag_name

    def _on_selection_changed(self, current):
        if not current:
            self.remove_btn.setEnabled(True)
            return

        self.remove_btn.setEnabled(True)
        self.remove_btn.setToolTip("")

    def _refresh_list(self):
        self.tag_list.clear()
        for tag in self.user_config.get_all_tags():
            item = QListWidgetItem()
            display_name = self._get_tag_display_name(tag.name)
            item.setText(display_name)
            item.setData(Qt.ItemDataRole.UserRole, tag)
            item.setData(Qt.ItemDataRole.UserRole + 1, tag.color)
            self.tag_list.addItem(item)

        if self.tag_list.count() > 0:
            self.tag_list.setCurrentRow(0)

    def _on_add(self):
        dialog = TagEditDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            tag = dialog.get_result()
            if tag:
                self.user_config.add_tag(tag.name, tag.color)
                self._refresh_list()
                self.config_changed.emit()

    def _on_edit(self):
        current_item = self.tag_list.currentItem()
        if not current_item:
            return

        tag = current_item.data(Qt.ItemDataRole.UserRole)
        dialog = TagEditDialog(self, tag)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_tag = dialog.get_result()
            if new_tag:
                self.user_config.update_tag_color(new_tag.name, new_tag.color)
                self.user_config.set_tag_enabled(new_tag.name, new_tag.enabled)
                self._refresh_list()
                self.config_changed.emit()

    def _on_remove(self):
        current_item = self.tag_list.currentItem()
        if not current_item:
            return

        tag = current_item.data(Qt.ItemDataRole.UserRole)
        display_name = self._get_tag_display_name(tag.name)
        message = tr("confirm_delete_tag").format(display_name)

        reply = QMessageBox.question(
            self, tr("confirm_delete"),
            message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.user_config.remove_tag(tag.name)
            self._refresh_list()
            self.config_changed.emit()

    def _on_reset(self):
        reply = QMessageBox.question(
            self, tr("confirm_delete"),
            tr("confirm_reset_tags"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.user_config.reset_tags_to_default()
            self._refresh_list()
            self.config_changed.emit()


from PyQt6.QtWidgets import QStyledItemDelegate, QStyle
from PyQt6.QtCore import QSize, Qt


class ColorCircleListDelegate(QStyledItemDelegate):
    """带颜色圆圈的列表项委托基类
    
    用于标签和颜色列表的统一渲染
    """

    def __init__(self, parent=None, base_font_size=12):
        super().__init__(parent)
        self._base_font_size = base_font_size
        self._circle_radius = 8
        self._icon_size = 14

    @staticmethod
    def _get_item_data(index):
        """获取列表项数据，子类可重写"""
        return (
            index.data(Qt.ItemDataRole.UserRole),
            index.data(Qt.ItemDataRole.UserRole + 1),
            index.data(Qt.ItemDataRole.DisplayRole)
        )

    @staticmethod
    def _is_enabled(item_data) -> bool:
        """判断项是否启用，子类可重写"""
        return getattr(item_data, 'enabled', True) if item_data else True

    def paint(self, painter, option, index):
        painter.save()

        item_data, color_hex, text = self._get_item_data(index)

        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(option.rect, QColor(get_color('surface_selected')))

        circle_x = option.rect.left() + 12
        circle_y = option.rect.center().y()

        if color_hex:
            painter.setBrush(QBrush(QColor(color_hex)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(circle_x - self._circle_radius,
                                circle_y - self._circle_radius,
                                self._circle_radius * 2,
                                self._circle_radius * 2)

        icon_x = circle_x + self._circle_radius + 8
        is_enabled = self._is_enabled(item_data)
        icon = get_icon('check_circle' if is_enabled else 'remove_circle',
                        get_color('success') if is_enabled else get_color('error'),
                        self._icon_size)
        icon.paint(painter, icon_x, circle_y - self._icon_size // 2,
                   self._icon_size, self._icon_size)

        text_x = icon_x + self._icon_size + 6
        text_rect = option.rect.adjusted(text_x - option.rect.left(), 0, 0, 0)
        painter.setPen(QColor(get_color('text')))
        font = painter.font()
        font.setPointSize(get_calculated_font_size(self._base_font_size, FontSize.SMALL))
        painter.setFont(font)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text or "")

        painter.restore()

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), max(28, get_calculated_font_size(self._base_font_size, FontSize.BASE)))


class TagListDelegate(ColorCircleListDelegate):
    """标签列表委托"""
    pass


class ColorListDelegate(ColorCircleListDelegate):
    """颜色列表委托"""
    pass


class ColorsTab(QWidget):
    """常用颜色管理标签页"""

    config_changed = pyqtSignal()

    def __init__(self, parent=None, base_font_size=12):
        super().__init__(parent)
        self.user_config = get_user_config()
        self._base_font_size = base_font_size
        self._setup_ui()
        self._refresh_list()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        info_label = QLabel(tr("common_colors"))
        info_label.setProperty("labelType", "settings_title")
        refresh_widget_style(info_label)
        layout.addWidget(info_label)

        self.color_list = QListWidget()
        self.color_list.setAlternatingRowColors(True)
        self.color_list.setItemDelegate(ColorListDelegate(self.color_list, self._base_font_size))
        self.color_list.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self.color_list)

        btn_layout = QHBoxLayout()

        add_btn = QPushButton(tr("add"))
        add_btn.setIcon(get_icon('add', get_color('text'), 16))
        add_btn.clicked.connect(self._on_add)
        add_btn.setProperty("buttonType", "standard")
        btn_layout.addWidget(add_btn)

        edit_btn = QPushButton(tr("edit"))
        edit_btn.setIcon(get_icon('edit_calendar', get_color('text'), 16))
        edit_btn.clicked.connect(self._on_edit)
        edit_btn.setProperty("buttonType", "standard")
        btn_layout.addWidget(edit_btn)

        self.remove_btn = QPushButton(tr("delete"))
        self.remove_btn.setIcon(get_icon('auto_delete', get_color('danger'), 16))
        self.remove_btn.clicked.connect(self._on_remove)
        self.remove_btn.setProperty("buttonType", "danger")
        btn_layout.addWidget(self.remove_btn)

        reset_btn = QPushButton(tr("reset"))
        reset_btn.setIcon(get_icon('history', get_color('text'), 16))
        reset_btn.clicked.connect(self._on_reset)
        reset_btn.setProperty("buttonType", "standard")
        btn_layout.addWidget(reset_btn)

        layout.addLayout(btn_layout)

    def _is_default_color(self, color_hex: str) -> bool:
        default_colors = {c.color.lower() for c in self.user_config.DEFAULT_COLORS}
        return color_hex.lower() in default_colors

    def _on_selection_changed(self, current):
        if not current:
            self.remove_btn.setEnabled(True)
            return

        color = current.data(Qt.ItemDataRole.UserRole)
        is_default = self._is_default_color(color.color)

        if is_default:
            self.remove_btn.setEnabled(False)
            self.remove_btn.setToolTip(tr("cannot_delete_default_color"))
        else:
            self.remove_btn.setEnabled(True)
            self.remove_btn.setToolTip("")

    @staticmethod
    def _get_color_display_name(color: ColorOption) -> str:
        if color.custom_name:
            return color.custom_name
        if color.name_key.startswith("color_"):
            return tr(color.name_key)
        return color.name_key

    def _refresh_list(self):
        self.color_list.clear()
        for color in self.user_config.get_all_colors():
            item = QListWidgetItem()
            display_name = self._get_color_display_name(color)
            item.setText(display_name)
            item.setData(Qt.ItemDataRole.UserRole, color)
            item.setData(Qt.ItemDataRole.UserRole + 1, color.color)
            self.color_list.addItem(item)

        if self.color_list.count() > 0:
            self.color_list.setCurrentRow(0)

    def _on_add(self):
        dialog = ColorEditDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            color = dialog.get_result()
            if color:
                if self.user_config.add_color(color.name_key, color.color, color.custom_name):
                    self._refresh_list()
                    self.config_changed.emit()
                else:
                    QMessageBox.warning(self, tr("error_title"), tr("color_exists"))

    def _on_edit(self):
        current_item = self.color_list.currentItem()
        if not current_item:
            return

        color = current_item.data(Qt.ItemDataRole.UserRole)
        dialog = ColorEditDialog(self, color)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_color = dialog.get_result()
            if new_color:
                self.user_config.update_color(color.color, new_color.color)
                self.user_config.update_color_custom_name(new_color.color, new_color.custom_name)
                self.user_config.set_color_enabled(new_color.color, new_color.enabled)
                self._refresh_list()
                self.config_changed.emit()

    def _on_remove(self):
        current_item = self.color_list.currentItem()
        if not current_item:
            return

        color = current_item.data(Qt.ItemDataRole.UserRole)

        if self._is_default_color(color.color):
            QMessageBox.information(self, tr("info"), tr("cannot_delete_default_color"))
            return

        reply = QMessageBox.question(
            self, tr("confirm_delete"),
            tr("confirm_delete_color").format(color.color),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.user_config.remove_color(color.color)
            self._refresh_list()
            self.config_changed.emit()

    def _on_reset(self):
        reply = QMessageBox.question(
            self, tr("confirm_delete"),
            tr("confirm_reset_colors"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.user_config.reset_colors_to_default()
            self._refresh_list()
            self.config_changed.emit()


class LanguageTab(QWidget):
    """语言设置标签页"""

    def __init__(self, parent=None, base_font_size=12, config_manager=None):
        super().__init__(parent)
        self.i18n = get_i18n()
        self._base_font_size = base_font_size
        self._config_manager = config_manager
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        title_label = QLabel(tr("language"))
        title_label.setProperty("labelType", "settings_title")
        refresh_widget_style(title_label)
        layout.addWidget(title_label)

        form_layout = QFormLayout()

        self.lang_combo = QComboBox()
        for lang, name in self.i18n.get_available_languages().items():
            self.lang_combo.addItem(name, lang)

        current_lang = self.i18n.get_language()
        for i in range(self.lang_combo.count()):
            if self.lang_combo.itemData(i) == current_lang:
                self.lang_combo.setCurrentIndex(i)
                break

        lang_label = QLabel(tr("language") + ":")
        lang_label.setProperty("labelType", "settings_form_label")
        refresh_widget_style(lang_label)
        form_layout.addRow(lang_label, self.lang_combo)
        layout.addLayout(form_layout)

        info_label = QLabel(tr("language_restart_required"))
        info_label.setProperty("labelType", "settings_info")
        refresh_widget_style(info_label)
        layout.addWidget(info_label)

        layout.addStretch()

    def get_selected_language(self) -> Language:
        return self.lang_combo.currentData()

    def save_language(self):
        if self._config_manager:
            new_lang = self.get_selected_language()
            self._config_manager.set_language(new_lang.value)


class ThemeTab(QWidget):
    """主题设置标签页"""

    theme_changed = pyqtSignal(str)

    def __init__(self, parent=None, base_font_size=12, config_manager=None):
        super().__init__(parent)
        self._base_font_size = base_font_size
        self._theme_manager = get_theme_manager()
        self._config_manager = config_manager
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        title_label = QLabel(tr("theme"))
        title_label.setProperty("labelType", "settings_title")
        refresh_widget_style(title_label)
        layout.addWidget(title_label)

        form_layout = QFormLayout()

        self.theme_combo = QComboBox()
        self._refresh_theme_list()
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)

        theme_label = QLabel(tr("theme") + ":")
        theme_label.setProperty("labelType", "settings_form_label")
        refresh_widget_style(theme_label)
        form_layout.addRow(theme_label, self.theme_combo)
        layout.addLayout(form_layout)

        info_label = QLabel(tr("theme_change_info"))
        info_label.setProperty("labelType", "settings_info")
        refresh_widget_style(info_label)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        btn_layout = QHBoxLayout()

        reload_btn = QPushButton(tr("reload_themes"))
        reload_btn.clicked.connect(self._reload_themes)
        btn_layout.addWidget(reload_btn)

        open_folder_btn = QPushButton(tr("open_theme_folder"))
        open_folder_btn.clicked.connect(self._open_theme_folder)
        btn_layout.addWidget(open_folder_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()

    def _refresh_theme_list(self):
        self.theme_combo.clear()
        themes = self._theme_manager.get_theme_list()
        current_theme_id = self._theme_manager.current_theme_id

        for theme_id in themes:
            theme_name = self._theme_manager.get_theme_name(theme_id)
            self.theme_combo.addItem(theme_name, theme_id)

        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == current_theme_id:
                self.theme_combo.setCurrentIndex(i)
                break

    def _on_theme_changed(self):
        theme_id = self.theme_combo.currentData()
        if theme_id:
            self.theme_changed.emit(theme_id)

    def _reload_themes(self):
        self._theme_manager.refresh_themes()
        self._refresh_theme_list()

    def _open_theme_folder(self):
        import subprocess
        themes_dir = self._theme_manager.themes_dir
        if os.path.exists(themes_dir):
            subprocess.run(['explorer', themes_dir])

    def get_selected_theme(self) -> str:
        return self.theme_combo.currentData() or ""

    def save_theme(self):
        if self._config_manager:
            theme_id = self.get_selected_theme()
            self._config_manager.set_theme(theme_id)


class FontTab(QWidget):
    """字体设置标签页"""

    def __init__(self, parent=None, base_font_size=12, config_manager=None):
        super().__init__(parent)
        self._base_font_size = base_font_size
        self._config_manager = config_manager
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        title_label = QLabel(tr("font_settings"))
        title_label.setProperty("labelType", "settings_title")
        refresh_widget_style(title_label)
        layout.addWidget(title_label)

        form_layout = QFormLayout()

        font_widget = QWidget()
        font_layout = QHBoxLayout(font_widget)
        font_layout.setContentsMargins(0, 0, 0, 0)
        font_layout.setSpacing(8)

        self.font_spin = QSpinBox()
        self.font_spin.setRange(8, 24)
        self.font_spin.setValue(self._base_font_size)
        self.font_spin.setSuffix(" px")
        font_layout.addWidget(self.font_spin)

        decrease_btn = QPushButton()
        decrease_btn.setIcon(get_icon('arrow_down', get_color('text'), 16))
        decrease_btn.setProperty("buttonType", "standard")
        decrease_btn.setFixedWidth(32)
        decrease_btn.setToolTip(tr("decrease_font_size"))
        decrease_btn.clicked.connect(self._decrease_font)
        font_layout.addWidget(decrease_btn)

        increase_btn = QPushButton()
        increase_btn.setIcon(get_icon('arrow_up', get_color('text'), 16))
        increase_btn.setProperty("buttonType", "standard")
        increase_btn.setFixedWidth(32)
        increase_btn.setToolTip(tr("increase_font_size"))
        increase_btn.clicked.connect(self._increase_font)
        font_layout.addWidget(increase_btn)

        reset_font_btn = QPushButton()
        reset_font_btn.setIcon(get_icon('reset', get_color('warning'), 16))
        reset_font_btn.setProperty("buttonType", "standard")
        reset_font_btn.setFixedWidth(32)
        reset_font_btn.setToolTip(tr("reset_font_size"))
        reset_font_btn.clicked.connect(self._reset_font)
        font_layout.addWidget(reset_font_btn)

        font_layout.addStretch()

        font_label = QLabel(tr("font_size") + ":")
        font_label.setProperty("labelType", "settings_form_label")
        refresh_widget_style(font_label)
        form_layout.addRow(font_label, font_widget)

        layout.addLayout(form_layout)

        info_label = QLabel(tr("restart_required"))
        info_label.setProperty("labelType", "settings_info")
        refresh_widget_style(info_label)
        layout.addWidget(info_label)

        layout.addStretch()

    def _increase_font(self):
        current = self.font_spin.value()
        if current < 24:
            self.font_spin.setValue(current + 1)

    def _decrease_font(self):
        current = self.font_spin.value()
        if current > 8:
            self.font_spin.setValue(current - 1)

    def _reset_font(self):
        self.font_spin.setValue(12)

    def get_font_size(self) -> int:
        return self.font_spin.value()


class NetworkSettingsTab(QWidget):
    """网络设置标签页"""

    settings_changed = pyqtSignal()

    def __init__(self, parent=None, base_font_size=12, config_manager=None):
        super().__init__(parent)
        self._base_font_size = base_font_size
        self._config_manager = config_manager
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        title_label = QLabel(tr("network_settings"))
        title_label.setProperty("labelType", "settings_title")
        refresh_widget_style(title_label)
        layout.addWidget(title_label)

        steam_group_label = QLabel(tr("steam_monitor_settings"))
        steam_group_label.setProperty("labelType", "settings_subtitle")
        refresh_widget_style(steam_group_label)
        layout.addWidget(steam_group_label)

        is_steam_disabled = False
        if self._config_manager:
            is_steam_disabled = self._config_manager.is_steam_monitor_disabled()

        self.steam_enabled_toggle = EnableToggleWidget(enabled=not is_steam_disabled)
        self.steam_enabled_toggle.toggled.connect(self._on_steam_toggled)
        layout.addWidget(self.steam_enabled_toggle)

        steam_desc_label = QLabel(tr("disable_steam_monitor_desc"))
        steam_desc_label.setProperty("labelType", "settings_info")
        refresh_widget_style(steam_desc_label)
        steam_desc_label.setWordWrap(True)
        layout.addWidget(steam_desc_label)

        layout.addSpacing(16)

        update_group_label = QLabel(tr("update_settings"))
        update_group_label.setProperty("labelType", "settings_subtitle")
        refresh_widget_style(update_group_label)
        layout.addWidget(update_group_label)

        is_update_disabled = False
        if self._config_manager:
            is_update_disabled = self._config_manager.is_update_check_disabled()

        self.update_enabled_toggle = EnableToggleWidget(enabled=not is_update_disabled)
        self.update_enabled_toggle.toggled.connect(self._on_update_toggled)
        layout.addWidget(self.update_enabled_toggle)

        update_desc_label = QLabel(tr("disable_update_check_desc"))
        update_desc_label.setProperty("labelType", "settings_info")
        refresh_widget_style(update_desc_label)
        update_desc_label.setWordWrap(True)
        layout.addWidget(update_desc_label)

        layout.addStretch()

    def _on_steam_toggled(self):
        self.settings_changed.emit()

    def _on_update_toggled(self):
        self.settings_changed.emit()

    def is_steam_monitor_disabled(self) -> bool:
        return not self.steam_enabled_toggle.isChecked()

    def is_update_check_disabled(self) -> bool:
        return not self.update_enabled_toggle.isChecked()

    def save_settings(self):
        if self._config_manager:
            steam_disabled = self.is_steam_monitor_disabled()
            self._config_manager.set_steam_monitor_disabled(steam_disabled)

            update_disabled = self.is_update_check_disabled()
            self._config_manager.set_update_check_disabled(update_disabled)

            self.settings_changed.emit()


class InfoPanelSectionsTab(QWidget):
    """Mod详情面板显示设置标签页"""

    settings_changed = pyqtSignal()

    SECTION_CONFIG = [
        ("file_info", "info_panel_section_file_info", "info_panel_section_file_info_desc"),
        ("load_requirements", "info_panel_section_load_requirements", "info_panel_section_load_requirements_desc"),
        ("official_tags", "info_panel_section_official_tags", "info_panel_section_official_tags_desc"),
        ("tags", "info_panel_section_tags", "info_panel_section_tags_desc"),
        ("color", "info_panel_section_color", "info_panel_section_color_desc"),
        ("note", "info_panel_section_note", "info_panel_section_note_desc"),
        ("ignore_issues", "info_panel_section_ignore_issues", "info_panel_section_ignore_issues_desc"),
        ("description", "info_panel_section_description", "info_panel_section_description_desc"),
    ]

    def __init__(self, parent=None, base_font_size=12, config_manager=None):
        super().__init__(parent)
        self._base_font_size = base_font_size
        self._config_manager = config_manager
        self._toggle_widgets: Dict[str, EnableToggleWidget] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        title_label = QLabel(tr("info_panel_sections_settings"))
        title_label.setProperty("labelType", "settings_title")
        refresh_widget_style(title_label)
        layout.addWidget(title_label)

        desc_label = QLabel(tr("info_panel_sections_settings_desc"))
        desc_label.setProperty("labelType", "settings_info")
        desc_label.setWordWrap(True)
        refresh_widget_style(desc_label)
        layout.addWidget(desc_label)

        sections_container = QWidget()
        sections_layout = QVBoxLayout(sections_container)
        sections_layout.setContentsMargins(8, 8, 8, 8)
        sections_layout.setSpacing(8)

        sections = self._get_sections_config()

        for section_key, name_key, desc_key in self.SECTION_CONFIG:
            section_widget = self._create_section_item(
                section_key,
                tr(name_key),
                tr(desc_key),
                sections.get(section_key, True)
            )
            sections_layout.addWidget(section_widget)

        sections_layout.addStretch()
        layout.addWidget(sections_container)
        layout.addStretch()

    def _get_sections_config(self) -> dict:
        if self._config_manager:
            return self._config_manager.get_info_panel_sections()
        return {key: True for key, _, _ in self.SECTION_CONFIG}

    def _create_section_item(self, section_key: str, name: str, desc: str, is_enabled: bool) -> QWidget:
        widget = QWidget()
        widget.setProperty("widgetType", "settings_section_item")
        item_layout = QVBoxLayout(widget)
        item_layout.setContentsMargins(0, 0, 0, 0)
        item_layout.setSpacing(4)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        name_label = QLabel(name)
        name_label.setProperty("labelType", "settings_form_label")
        refresh_widget_style(name_label)
        header_layout.addWidget(name_label)

        header_layout.addStretch()

        toggle_widget = EnableToggleWidget(enabled=is_enabled)
        toggle_widget.toggled.connect(lambda checked, key=section_key: self._on_section_toggled(key, checked))
        self._toggle_widgets[section_key] = toggle_widget
        header_layout.addWidget(toggle_widget)

        item_layout.addLayout(header_layout)

        desc_label = QLabel(desc)
        desc_label.setProperty("labelType", "settings_info")
        desc_label.setWordWrap(True)
        refresh_widget_style(desc_label)
        item_layout.addWidget(desc_label)

        return widget

    def _on_section_toggled(self, section_key: str, enabled: bool):
        if self._config_manager:
            self._config_manager.set_info_panel_section_visible(section_key, enabled)
            self.settings_changed.emit()


class PluginTab(QWidget):
    """插件管理标签页"""

    config_changed = pyqtSignal()

    def __init__(self, parent=None, base_font_size=12, config_manager=None):
        super().__init__(parent)
        self._base_font_size = base_font_size
        self._plugin_loader = get_plugin_loader()
        self._config_manager = config_manager
        self._toggle_widgets: Dict[str, EnableToggleWidget] = {}
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        title_label = QLabel(tr("plugin_management"))
        title_label.setProperty("labelType", "settings_title")
        refresh_widget_style(title_label)
        layout.addWidget(title_label)

        dir_btn_layout = QHBoxLayout()
        dir_btn_layout.setSpacing(8)

        open_game_dir_btn = QPushButton(tr("open_game_plugins_dir"))
        open_game_dir_btn.setProperty("buttonType", "standard")
        open_game_dir_btn.clicked.connect(self._open_game_plugins_dir)
        dir_btn_layout.addWidget(open_game_dir_btn)

        open_feature_dir_btn = QPushButton(tr("open_feature_plugins_dir"))
        open_feature_dir_btn.setProperty("buttonType", "standard")
        open_feature_dir_btn.clicked.connect(self._open_feature_plugins_dir)
        dir_btn_layout.addWidget(open_feature_dir_btn)

        dir_btn_layout.addStretch()
        layout.addLayout(dir_btn_layout)

        game_plugins = self._plugin_loader.get_available_game_plugins()
        feature_plugins = self._plugin_loader.get_all_feature_plugins().keys()

        if game_plugins:
            game_group_label = QLabel(tr("game_plugins"))
            game_group_label.setProperty("labelType", "settings_title")
            refresh_widget_style(game_group_label)
            layout.addWidget(game_group_label)

            game_desc_label = QLabel(tr("plugin_game_desc"))
            game_desc_label.setProperty("labelType", "settings_info")
            game_desc_label.setWordWrap(True)
            refresh_widget_style(game_desc_label)
            layout.addWidget(game_desc_label)

            game_scroll = QScrollArea()
            game_scroll.setWidgetResizable(True)
            game_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            game_scroll.setProperty("scrollAreaType", "validation")

            game_content = QWidget()
            game_scroll_layout = QVBoxLayout(game_content)
            game_scroll_layout.setContentsMargins(8, 8, 8, 8)
            game_scroll_layout.setSpacing(4)

            self._refresh_plugin_list(game_scroll_layout, PluginType.GAME)

            game_scroll_layout.addStretch()
            game_scroll.setWidget(game_content)
            layout.addWidget(game_scroll)

        if feature_plugins:
            feature_group_label = QLabel(tr("feature_plugins"))
            feature_group_label.setProperty("labelType", "settings_title")
            refresh_widget_style(feature_group_label)
            layout.addWidget(feature_group_label)

            feature_desc_label = QLabel(tr("plugin_feature_desc"))
            feature_desc_label.setProperty("labelType", "settings_info")
            feature_desc_label.setWordWrap(True)
            refresh_widget_style(feature_desc_label)
            layout.addWidget(feature_desc_label)

            feature_scroll = QScrollArea()
            feature_scroll.setWidgetResizable(True)
            feature_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            feature_scroll.setProperty("scrollAreaType", "validation")

            feature_content = QWidget()
            feature_scroll_layout = QVBoxLayout(feature_content)
            feature_scroll_layout.setContentsMargins(8, 8, 8, 8)
            feature_scroll_layout.setSpacing(4)

            self._refresh_plugin_list(feature_scroll_layout, PluginType.FEATURE)

            feature_scroll_layout.addStretch()
            feature_scroll.setWidget(feature_content)
            layout.addWidget(feature_scroll)

        if not game_plugins and not feature_plugins:
            no_plugins_label = QLabel(tr("no_plugins_found"))
            no_plugins_label.setProperty("labelType", "settings_info")
            refresh_widget_style(no_plugins_label)
            no_plugins_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(no_plugins_label)

        layout.addStretch()

    def _refresh_plugin_list(self, scroll_layout: QVBoxLayout, plugin_type: PluginType):
        current_adapter = self._plugin_loader.get_current_adapter()
        current_id = None
        if current_adapter:
            for pid, adapter in self._plugin_loader.adapters.items():
                if adapter == current_adapter:
                    current_id = pid
                    break

        plugins = (self._plugin_loader.get_available_game_plugins()
                   if plugin_type == PluginType.GAME
                   else self._plugin_loader.get_available_feature_plugin_ids())

        for plugin_id in plugins:
            info = self._plugin_loader.get_plugin_info(plugin_id)
            if info:
                is_current = plugin_id == current_id if plugin_type == PluginType.GAME else True
                if plugin_type == PluginType.GAME:
                    name = info.config.game_info.default_name if info.config and info.config.game_info else plugin_id
                    author = info.config.game_info.author if info.config and info.config.game_info else ''
                else:
                    name = info.config.name if info.config and info.config.name else plugin_id
                    author = info.config.author if info.config and info.config.author else ''
                version = info.plugin_version

                self._create_plugin_item(scroll_layout, plugin_id, name, version, author, is_current, plugin_type)

    def _create_plugin_item(self, scroll_layout: QVBoxLayout, plugin_id: str, name: str,
                            version: str, author: str, is_current: bool, plugin_type: PluginType):
        plugin_widget = QWidget()
        plugin_layout = QVBoxLayout(plugin_widget)
        plugin_layout.setContentsMargins(0, 0, 0, 0)
        plugin_layout.setSpacing(2)

        name_layout = QHBoxLayout()
        name_layout.setContentsMargins(12, 0, 0, 0)
        name_layout.setSpacing(4)

        bullet_label = QLabel("•")
        bullet_label.setProperty("labelType", "plugin_item_bullet")
        name_layout.addWidget(bullet_label)

        name_label = QLabel(name)
        name_label.setProperty("labelType", "plugin_item_name")
        name_layout.addWidget(name_label, 1)

        if plugin_type == PluginType.GAME:
            open_config_btn = QPushButton(tr("open_config"))
            open_config_btn.setProperty("buttonType", "link")
            open_config_btn.clicked.connect(lambda: self._open_plugin_config_dir(plugin_id))
            name_layout.addWidget(open_config_btn)
        else:
            is_enabled = self._is_plugin_enabled(plugin_id)
            toggle_widget = EnableToggleWidget(enabled=is_enabled)
            toggle_widget.toggled.connect(lambda checked, pid=plugin_id: self._on_plugin_toggled(pid, checked))
            self._toggle_widgets[plugin_id] = toggle_widget
            name_layout.addWidget(toggle_widget)

        plugin_layout.addLayout(name_layout)

        detail_parts = [f"v{version}"]
        if author:
            detail_parts.append(author)
        if plugin_type == PluginType.GAME:
            status_text = tr("plugin_enabled") if is_current else tr("plugin_disabled")
            detail_parts.append(status_text)
        detail_text = " | ".join(detail_parts)

        detail_label = QLabel(detail_text)
        detail_label.setProperty("labelType", "plugin_item_detail")
        detail_label.setContentsMargins(24, 0, 0, 0)
        plugin_layout.addWidget(detail_label)

        plugin_widget.setProperty("widgetType", "plugin_item")
        scroll_layout.addWidget(plugin_widget)

    def _is_plugin_enabled(self, plugin_id: str) -> bool:
        if self._config_manager:
            return not self._config_manager.is_feature_plugin_disabled(plugin_id)
        return True

    def _on_plugin_toggled(self, plugin_id: str, enabled: bool):
        if self._config_manager:
            self._config_manager.set_feature_plugin_disabled(plugin_id, not enabled)
            self.config_changed.emit()

    def _open_game_plugins_dir(self):
        import os
        path = self._plugin_loader.get_game_plugins_dir()
        if path and os.path.exists(path):
            os.startfile(path)

    def _open_feature_plugins_dir(self):
        import os
        path = self._plugin_loader.get_feature_plugins_dir()
        if path and os.path.exists(path):
            os.startfile(path)

    @staticmethod
    def _open_plugin_config_dir(plugin_id: str):
        import os
        from core.manager_collection import get_manager_collection
        config_manager = get_manager_collection().get_config_manager()
        if config_manager:
            game_data_dir = config_manager.game_data_dir
            plugin_data_dir = os.path.join(game_data_dir, plugin_id)
            if os.path.exists(plugin_data_dir):
                os.startfile(plugin_data_dir)
            else:
                os.makedirs(plugin_data_dir, exist_ok=True)
                os.startfile(plugin_data_dir)


class SettingsDialog(QDialog):
    """设置对话框"""

    config_changed = pyqtSignal()

    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent)
        self._config_manager = config_manager
        self._base_font_size = config_manager.get_font_size() if config_manager else 12
        self._mod_metadata = config_manager.load_mod_metadata() if config_manager else {}
        self._plugin_config_changed = False
        self.setWindowTitle(tr("settings"))
        min_width = get_ui_constant('settings_dialog', 'min_width', 800)
        min_height = get_ui_constant('settings_dialog', 'min_height', 500)
        self.setMinimumSize(min_width, min_height)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        main_layout = QHBoxLayout()

        self.nav_list = QListWidget()
        self.nav_list.setProperty("listType", "settings_nav")
        refresh_widget_style(self.nav_list)
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        main_layout.addWidget(self.nav_list)

        self.stack_widget = QStackedWidget()
        self.stack_widget.setProperty("widgetType", "settings_stack")
        main_layout.addWidget(self.stack_widget, 1)

        nav_items = [
            (tr("common_tags"), "tag_duotone", self._create_tags_tab),
            (tr("common_colors"), "color_lens", self._create_colors_tab),
            (tr("theme"), "themes", self._create_theme_tab),
            (tr("language"), "translate", self._create_language_tab),
            (tr("font_settings"), "font_outline", self._create_font_tab),
            (tr("info_panel_sections_settings"), "info", self._create_info_panel_sections_tab),
            (tr("plugin_management"), "plugin_fill", self._create_plugin_tab),
            (tr("network_settings"), "cloud", self._create_network_settings_tab),
        ]

        icon_size = 20
        max_width = 0
        fm = QFontMetrics(self.nav_list.font())
        for text, _, _ in nav_items:
            text_width = fm.horizontalAdvance(text) + icon_size + 40
            max_width = max(max_width, text_width)

        self.nav_list.setMinimumWidth(max_width)

        for text, icon_name, create_func in nav_items:
            item = QListWidgetItem(text)
            icon = get_icon(icon_name, get_color('text'), icon_size)
            item.setIcon(icon)
            self.nav_list.addItem(item)
            self.stack_widget.addWidget(create_func())

        self.nav_list.setCurrentRow(0)

        layout.addLayout(main_layout)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        ok_btn = QPushButton(tr("ok"))
        ok_btn.clicked.connect(self._on_ok)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton(tr("cancel"))
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)

        theme_manager = get_theme_manager()
        theme_manager.theme_changed.connect(self._on_theme_changed)

    def _create_tags_tab(self):
        self.tags_tab = TagsTab(base_font_size=self._base_font_size, mod_metadata=self._mod_metadata)
        self.tags_tab.config_changed.connect(self.config_changed.emit)
        return self.tags_tab

    def _create_colors_tab(self):
        self.colors_tab = ColorsTab(base_font_size=self._base_font_size)
        self.colors_tab.config_changed.connect(self.config_changed.emit)
        return self.colors_tab

    def _create_theme_tab(self):
        self.theme_tab = ThemeTab(base_font_size=self._base_font_size, config_manager=self._config_manager)
        self.theme_tab.theme_changed.connect(self._on_theme_selected)
        return self.theme_tab

    def _create_language_tab(self):
        self.language_tab = LanguageTab(base_font_size=self._base_font_size, config_manager=self._config_manager)
        return self.language_tab

    def _create_font_tab(self):
        self.font_tab = FontTab(base_font_size=self._base_font_size, config_manager=self._config_manager)
        return self.font_tab

    def _create_info_panel_sections_tab(self):
        self.info_panel_sections_tab = InfoPanelSectionsTab(
            base_font_size=self._base_font_size,
            config_manager=self._config_manager
        )
        self.info_panel_sections_tab.settings_changed.connect(self._on_info_panel_sections_changed)
        return self.info_panel_sections_tab

    def _create_plugin_tab(self):
        self.plugin_tab = PluginTab(base_font_size=self._base_font_size, config_manager=self._config_manager)
        self.plugin_tab.config_changed.connect(self._on_plugin_config_changed)
        return self.plugin_tab

    def _create_network_settings_tab(self):
        self.network_settings_tab = NetworkSettingsTab(base_font_size=self._base_font_size,
                                                       config_manager=self._config_manager)
        return self.network_settings_tab

    def _on_nav_changed(self, index):
        self.stack_widget.setCurrentIndex(index)

    def _on_plugin_config_changed(self):
        self._plugin_config_changed = True

    def _on_info_panel_sections_changed(self):
        self.config_changed.emit()

    @staticmethod
    def _on_theme_selected(theme_id: str):
        theme_manager = get_theme_manager()
        theme_manager.load_theme(theme_id)

    def _on_theme_changed(self):
        self.nav_list.style().unpolish(self.nav_list)
        self.nav_list.style().polish(self.nav_list)
        self.stack_widget.style().unpolish(self.stack_widget)
        self.stack_widget.style().polish(self.stack_widget)

        icon_size = 20
        for i in range(self.nav_list.count()):
            item = self.nav_list.item(i)
            nav_items = [
                ("tag_duotone",),
                ("color_lens",),
                ("themes",),
                ("translate",),
                ("font_outline",),
                ("info",),
                ("extension",),
                ("cloud",),
            ]
            if i < len(nav_items):
                icon_name = nav_items[i][0]
                icon = get_icon(icon_name, get_color('text'), icon_size)
                item.setIcon(icon)

    def _on_ok(self):
        self.language_tab.save_language()
        new_lang = self.language_tab.get_selected_language()
        i18n = get_i18n()
        if new_lang != i18n.get_language():
            i18n.set_language(new_lang)
            self.language_tab.save_language()
            QMessageBox.information(
                self, tr("msg_settings_saved"),
                tr("language_restart_required")
            )

        self.theme_tab.save_theme()

        new_font_size = self.font_tab.get_font_size()
        if new_font_size != self._base_font_size and self._config_manager:
            self._config_manager.set_font_size(new_font_size)
            QMessageBox.information(
                self, tr("msg_settings_saved"),
                tr("restart_required")
            )

        self.network_settings_tab.save_settings()

        if self._plugin_config_changed:
            QMessageBox.information(
                self, tr("msg_settings_saved"),
                tr("plugin_restart_required")
            )

        self.accept()
