"""
样式模块 - 从QSS文件加载样式
支持主题相关的样式变量替换

优化说明：
- 添加缓存刷新机制，支持配置热更新
- 统一样式刷新方法，减少重复代码
"""

import logging
import os
from enum import Enum
from typing import Dict, Optional

from PyQt6.QtCore import Qt, QRect, QSize, QPoint
from PyQt6.QtWidgets import QLayout

from utils.file_utils import get_resource_path
from .theme_manager import get_theme_manager

logger = logging.getLogger(__name__)


class FontSize(Enum):
    VERY_TINY = "very_tiny"
    TINY = "tiny"
    SMALL = "small"
    BASE = "base"
    MEDIUM = "medium"
    LARGE = "large"
    TITLE = "title"
    DISPLAY = "display"


STYLE_DIR = get_resource_path(os.path.join("config", "styles"))
_constants_cache: Optional[Dict] = None
_font_size_offsets_cache: Optional[Dict[FontSize, int]] = None

_DEFAULT_FONT_OFFSETS = {
    FontSize.VERY_TINY: -8, FontSize.TINY: -4, FontSize.SMALL: -2, FontSize.BASE: 0,
    FontSize.MEDIUM: 1, FontSize.LARGE: 2, FontSize.TITLE: 4, FontSize.DISPLAY: 8
}


def _load_font_size_offsets() -> Dict[FontSize, int]:
    global _font_size_offsets_cache
    if _font_size_offsets_cache is not None:
        return _font_size_offsets_cache

    font_sizes_config = _load_ui_constants().get("font_sizes", {})
    if font_sizes_config:
        _font_size_offsets_cache = {}
        for key, value in font_sizes_config.items():
            try:
                _font_size_offsets_cache[FontSize(key)] = value
            except ValueError:
                logger.debug(f"Unknown font size key: {key}")
    else:
        _font_size_offsets_cache = _DEFAULT_FONT_OFFSETS.copy()
    return _font_size_offsets_cache


def _load_ui_constants() -> Dict:
    global _constants_cache
    if _constants_cache is not None:
        return _constants_cache

    from core.json_serializer import get_json_manager
    config_dir = get_resource_path("config")
    json_manager = get_json_manager(config_dir)
    constants_path = os.path.join(config_dir, "ui_constants.json")
    _constants_cache = json_manager.load_from_file(constants_path, default={})
    return _constants_cache


def get_ui_constant(category: str, key: str, default=None):
    constants = _load_ui_constants()
    return constants.get(category, {}).get(key, default)


def get_ui_constant_dict(category: str, default=None) -> Optional[Dict]:
    constants = _load_ui_constants()
    return constants.get(category, default)


def clear_ui_constants_cache():
    """清除UI常量缓存，用于配置热更新"""
    global _constants_cache, _font_size_offsets_cache
    _constants_cache = None
    _font_size_offsets_cache = None


def _load_qss_file(filename: str) -> str:
    filepath = os.path.join(STYLE_DIR, filename)
    if not os.path.exists(filepath):
        return ""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()


def _replace_variables(qss_content: str, font_size: int = 14) -> str:
    tm = get_theme_manager()
    colors = tm.get_all_colors()
    border_radius = tm.get_all_border_radius()
    font_offsets = _load_font_size_offsets()

    result = qss_content

    for key, value in colors.items():
        result = result.replace(f"${{colors.{key}}}", value)

    for key, value in border_radius.items():
        result = result.replace(f"${{border_radius.{key}}}", str(value))

    result = result.replace("${font_size}", str(font_size))
    result = result.replace("${font_size_base}", str(font_size))

    for key, offset in font_offsets.items():
        actual_size = max(8, font_size + offset)
        result = result.replace(f"${{font_size_{key.value}}}", str(actual_size))

    return result


def get_modern_theme(font_size: int = 14) -> str:
    if not os.path.exists(STYLE_DIR):
        return ""

    qss_files = sorted([
        f for f in os.listdir(STYLE_DIR)
        if f.endswith('.qss')
    ])

    combined_qss = []
    for filename in qss_files:
        content = _load_qss_file(filename)
        if content:
            combined_qss.append(content)

    full_qss = "\n\n".join(combined_qss)
    return _replace_variables(full_qss, font_size)


def apply_theme(app, font_size: int = 14):
    theme = get_modern_theme(font_size)
    app.setStyleSheet(theme)


def get_calculated_font_size(base_font_size: int, size_key: FontSize = FontSize.BASE) -> int:
    offsets = _load_font_size_offsets()
    offset = offsets.get(size_key, 0)
    return max(8, base_font_size + offset)


def refresh_widget_style(widget):
    """刷新单个控件的样式
    
    统一的样式刷新方法，避免重复代码
    """
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def setup_checkbox_icon(checkbox, icon_name: str = 'done', size: int = 14):
    """为CheckBox设置选中状态的图标
    
    Args:
        checkbox: QCheckBox控件
        icon_name: 图标名称，默认为'done'
        size: 图标大小，默认为14
    """
    from utils.icons import get_icon
    from ui.theme_manager import get_color

    icon = get_icon(icon_name, get_color('white'), size)
    checkbox.setIcon(icon)
    checkbox.setIconSize(QSize(size, size))


def refresh_widgets_style(*widgets):
    """批量刷新多个控件的样式
    
    Args:
        *widgets: 要刷新样式的控件列表
    """
    for widget in widgets:
        if widget is not None:
            refresh_widget_style(widget)


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        if parent is not None:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self._items = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self._items.append(item)
        widget = item.widget()
        if widget:
            widget.ensurePolished()
            widget.adjustSize()
        self.invalidate()
        if self.parentWidget():
            self.parentWidget().updateGeometry()

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            item = self._items.pop(index)
            self.invalidate()
            return item
        return None

    def clear(self):
        while self._items:
            item = self.takeAt(0)
            if item:
                widget = item.widget()
                if widget:
                    widget.hide()
                    widget.setParent(None)
                elif item.layout():
                    self._remove_item_recursive(item.layout())
        self.invalidate()
        if self.parentWidget():
            self.parentWidget().update()
            self.parentWidget().updateGeometry()

    def _remove_item_recursive(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
            elif item.layout():
                self._remove_item_recursive(item.layout())

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._calculate_height(width)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def _calculate_height(self, width: int) -> int:
        if not self._items:
            return 0

        margin = self.contentsMargins()
        space_x = self.spacing()
        space_y = self.spacing()

        x = margin.left()
        y = margin.top()
        line_height = 0
        right_edge = width - margin.right()

        for item in self._items:
            widget = item.widget()
            if widget and not widget.isVisible():
                continue

            if widget:
                item_size = widget.sizeHint()
                if item_size.width() <= 0 or item_size.height() <= 0:
                    item_size = widget.minimumSizeHint()
                if item_size.width() <= 0 or item_size.height() <= 0:
                    item_size = widget.minimumSize()
            else:
                item_size = item.sizeHint()

            if item_size.width() <= 0 or item_size.height() <= 0:
                item_size = QSize(60, 22)

            if x + item_size.width() > right_edge and line_height > 0:
                y = y + line_height + space_y
                x = margin.left()
                line_height = 0

            x = x + item_size.width() + space_x
            line_height = max(line_height, item_size.height())

        return y + line_height + margin.bottom()

    def minimumSize(self):
        if not self._items:
            return QSize(0, 0)

        margin = self.contentsMargins()
        parent = self.parentWidget()
        if parent:
            available_width = parent.width()
            if available_width > margin.left() + margin.right():
                height = self._calculate_height(available_width)
                return QSize(available_width, height)

        height = self._calculate_height(10000)
        return QSize(0, height)

    def update(self):
        self.invalidate()
        if self.parentWidget():
            parent = self.parentWidget()
            parent.updateGeometry()
            parent.update()

    def _do_layout(self, rect, test_only):
        if rect.width() <= 0 and self.parentWidget():
            rect = QRect(0, 0, self.parentWidget().width(), self.parentWidget().height())

        margin = self.contentsMargins()
        space_x = self.spacing()
        space_y = self.spacing()

        x = margin.left()
        y = margin.top()
        line_height = 0
        right_edge = rect.width() - margin.right()

        for item in self._items:
            widget = item.widget()
            if widget and not widget.isVisible():
                continue

            if widget:
                item_size = widget.sizeHint()
                if item_size.width() <= 0 or item_size.height() <= 0:
                    item_size = widget.minimumSizeHint()
                if item_size.width() <= 0 or item_size.height() <= 0:
                    item_size = widget.minimumSize()
            else:
                item_size = item.sizeHint()

            if item_size.width() <= 0 or item_size.height() <= 0:
                item_size = QSize(60, 22)

            next_x = x + item_size.width()
            if next_x > right_edge and line_height > 0:
                x = margin.left()
                y = y + line_height + space_y
                next_x = x + item_size.width()
                line_height = 0

            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), item_size))

            x = next_x + space_x
            line_height = max(line_height, item_size.height())

        return y + line_height + margin.bottom() - rect.top()
