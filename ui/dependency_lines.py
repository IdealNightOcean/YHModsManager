from dataclasses import dataclass
from typing import Dict, List, Optional

from PyQt6.QtCore import QTimer
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPen, QPainterPath, QPolygon, QFont, QBrush
from PyQt6.QtWidgets import (
    QListWidget, QWidget, QSizePolicy
)

from yh_mods_manager_sdk import ListType
from utils.debouncer import Debouncer
from .i18n import tr
from .styles import get_ui_constant, get_calculated_font_size, FontSize
from .theme_manager import get_color, get_dependency_colors, get_border_radius

_dependency_lines_config_cache: Optional[Dict] = None
_legend_config_cache: Optional[Dict] = None


def _get_dependency_lines_config():
    """获取依赖线配置（带缓存）"""
    global _dependency_lines_config_cache
    if _dependency_lines_config_cache is not None:
        return _dependency_lines_config_cache

    _dependency_lines_config_cache = {
        'item_height': get_ui_constant('dependency_lines', 'item_height', 40),
        'line_width': get_ui_constant('dependency_lines', 'line_width', 0.8),
        'highlight_line_width': get_ui_constant('dependency_lines', 'highlight_line_width', 1.6),
        'default_alpha': get_ui_constant('dependency_lines', 'default_alpha', 200),
        'highlight_alpha': get_ui_constant('dependency_lines', 'highlight_alpha', 255),
        'line_offset_step': get_ui_constant('dependency_lines', 'line_offset_step', 6),
        'info_box_margin': get_ui_constant('dependency_lines', 'info_box_margin', 50),
        'max_line_area_width': get_ui_constant('dependency_lines', 'max_line_area_width', 56),
        'scrollbar_width': get_ui_constant('dependency_lines', 'scrollbar_width', 10),
        'scrollbar_margin': get_ui_constant('dependency_lines', 'scrollbar_margin', 4),
        'max_lines_in_area': get_ui_constant('dependency_lines', 'max_lines_in_area', 5),
        'step_x': get_ui_constant('dependency_lines', 'step_x', 10),
    }
    return _dependency_lines_config_cache


def _get_legend_config():
    """获取图例配置（带缓存）"""
    global _legend_config_cache
    if _legend_config_cache is not None:
        return _legend_config_cache

    _legend_config_cache = {
        'item_height': get_ui_constant('legend_widget', 'item_height', 22),
        'min_width': get_ui_constant('legend_widget', 'min_width', 140),
        'collapsed_min_width': get_ui_constant('legend_widget', 'collapsed_min_width', 40),
    }
    return _legend_config_cache


@dataclass
class DependencyLine:
    source_id: str
    target_id: str
    source_row: int
    target_row: int
    color: QColor
    offset_index: int = 0
    source_offset: int = 0
    target_offset: int = 0
    is_wrong_order: bool = False


class DependencyColorManager:
    def __init__(self):
        self._color_map: Dict[str, QColor] = {}
        self._color_index = 0

    @staticmethod
    def get_dependency_colors() -> List[str]:
        return get_dependency_colors()

    def get_color_for_mod(self, mod_id: str) -> QColor:
        if mod_id not in self._color_map:
            colors = self.get_dependency_colors()
            color_hex = colors[self._color_index % len(colors)]
            self._color_map[mod_id] = QColor(color_hex)
            self._color_index += 1
        return self._color_map[mod_id]

    def get_all_colors(self) -> Dict[str, QColor]:
        return self._color_map.copy()

    def clear(self):
        self._color_map.clear()
        self._color_index = 0

    def rebuild(self, source_mod_ids: List[str]):
        self.clear()
        for mod_id in source_mod_ids:
            self.get_color_for_mod(mod_id)


class ModHighlightMixin:
    def __init__(self):
        self._highlight_mod_id: Optional[str] = None
        self._selected_mod_id: Optional[str] = None
        self._list_widget: Optional[QListWidget] = None

    def set_highlight_mod(self, mod_id: Optional[str], is_selected: bool = False):
        if is_selected:
            self._selected_mod_id = mod_id
            self._highlight_mod_id = mod_id
        else:
            if mod_id is None:
                # 掠过空白处时，只清除高亮，不清除选中状态
                self._highlight_mod_id = None
            else:
                is_selected_in_enabled = False
                if self._selected_mod_id and self._list_widget:
                    for i in range(self._list_widget.count()):
                        item = self._list_widget.item(i)
                        if item and item.mod.id == self._selected_mod_id:
                            is_selected_in_enabled = True
                            break
                if not self._selected_mod_id or not is_selected_in_enabled:
                    self._highlight_mod_id = mod_id
        self.update()

    def clear_selected_mod(self):
        self._selected_mod_id = None
        self._highlight_mod_id = None
        self.update()


class DependencyLegendWidget(QWidget, ModHighlightMixin):
    legend_clicked = pyqtSignal(str)
    toggle_lines_requested = pyqtSignal()

    def __init__(self, parent=None, base_font_size=12):
        QWidget.__init__(self, parent)
        ModHighlightMixin.__init__(self)
        self._base_font_size = base_font_size
        legend_config = _get_legend_config()
        self._item_height = legend_config['item_height']
        self._min_width = legend_config['min_width']
        self._collapsed_min_width = legend_config['collapsed_min_width']

        lines_config = _get_dependency_lines_config()
        self._scrollbar_width = lines_config['scrollbar_width']
        self._scrollbar_margin = lines_config['scrollbar_margin']

        self._color_manager: Optional[DependencyColorManager] = None
        self._hover_mod_id: Optional[str] = None
        self._collapsed = False
        self._mod_names: Dict[str, str] = {}
        self._show_lines = True
        self._toggle_btn_rect: Optional[QRect] = None
        self._scroll_offset = 0
        self._content_height = 0
        self._header_height = 40
        self._dragging_scrollbar = False
        self._scrollbar_drag_start_y = 0
        self._scrollbar_drag_start_offset = 0
        self._scrollbar_rect: Optional[QRect] = None
        self._scrollbar_hovered = False
        self._scrollbar_track_rect: Optional[QRect] = None

        self.setMinimumWidth(self._min_width)
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.WheelFocus)

    def set_show_lines(self, show: bool):
        self._show_lines = show
        self.update()

    def set_color_manager(self, manager: DependencyColorManager):
        self._color_manager = manager
        self._scroll_offset = 0
        self.update()

    def set_mod_names(self, names: Dict[str, str]):
        self._mod_names = names
        self._scroll_offset = 0
        self.update()

    def set_collapsed(self, collapsed: bool):
        self._collapsed = collapsed
        if collapsed:
            self.setMinimumWidth(self._collapsed_min_width)
        else:
            self.setMinimumWidth(self._min_width)
        self.update()

    def toggle_collapsed(self):
        self.set_collapsed(not self._collapsed)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        br = get_border_radius('card')
        bg_rect = self.rect().adjusted(4, 4, -4, -4)
        painter.setBrush(QBrush(QColor(get_color('surface_light'))))
        painter.setPen(QColor(get_color('border')))
        painter.drawRoundedRect(bg_rect, br, br)

        if self._collapsed:
            painter.setPen(QColor(get_color('accent')))
            font = QFont()
            font.setPointSize(get_calculated_font_size(self._base_font_size, FontSize.TINY))
            painter.setFont(font)
            painter.drawText(10, 25, tr("legend_collapsed_1"))
            painter.drawText(10, 45, tr("legend_collapsed_2"))
            painter.end()
            return

        painter.setPen(QColor(get_color('accent')))
        font = QFont()
        font.setBold(True)
        font.setPointSize(get_calculated_font_size(self._base_font_size, FontSize.SMALL))
        painter.setFont(font)
        painter.drawText(14, 24, tr("dependency_legend"))

        btn_text = "🔗" if self._show_lines else "⛓️‍💥"
        btn_rect = QRect(self.width() - 34, 8, 24, 24)
        self._toggle_btn_rect = btn_rect

        btn_color = QColor(get_color('border')) if self._show_lines else QColor(get_color('surface_light'))
        painter.setBrush(QBrush(btn_color))
        painter.setPen(QColor(get_color('border_light')))
        painter.drawRoundedRect(btn_rect, 4, 4)

        painter.setPen(QColor(get_color('drop_indicator')))
        font.setPointSize(get_calculated_font_size(self._base_font_size, FontSize.SMALL))
        painter.setFont(font)
        painter.drawText(btn_rect, Qt.AlignmentFlag.AlignCenter, btn_text)

        if not self._color_manager:
            painter.end()
            return

        colors = self._color_manager.get_all_colors()
        if not colors:
            painter.end()
            return

        num_items = len(colors)
        self._content_height = num_items * self._item_height

        list_area_top = self._header_height
        list_area_height = self.height() - self._header_height - 8
        list_area_rect = QRect(4, list_area_top, self.width() - 8, list_area_height)

        painter.setClipRect(list_area_rect)

        font.setBold(False)
        font.setPointSize(get_calculated_font_size(self._base_font_size, FontSize.TINY))
        painter.setFont(font)

        y_offset = self._header_height + 12 - self._scroll_offset
        for mod_id, color in colors.items():
            if y_offset + self._item_height < list_area_top:
                y_offset += self._item_height
                continue
            if y_offset > self.height() - 8:
                break

            is_highlighted = self._highlight_mod_id == mod_id

            display_name = self._mod_names.get(mod_id, mod_id)
            if len(display_name) > 12:
                display_name = display_name[:10] + "..."

            item_rect = QRect(8, y_offset - 12, self.width() - 16, self._item_height)
            if is_highlighted:
                painter.fillRect(item_rect, QColor(get_color('legend_item_hover')))
                painter.setPen(QColor(get_color('border_focus')))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(item_rect, 4, 4)
            else:
                painter.fillRect(item_rect, QColor(get_color('legend_item_background')))
                painter.setPen(QColor(get_color('border')))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRoundedRect(item_rect, 4, 4)

            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(18, y_offset - 5, 10, 10)

            text_color = QColor(color)
            if not is_highlighted and self._highlight_mod_id:
                text_color.setAlpha(100)
            else:
                text_color.setAlpha(255)

            painter.setPen(text_color)
            painter.drawText(33, y_offset + 3, display_name)

            y_offset += self._item_height

        painter.setClipping(False)

        max_scroll = self._get_max_scroll_offset()
        if max_scroll > 0:
            scrollbar_track_width = self._scrollbar_width + 4
            scrollbar_area_height = list_area_height - 8
            scrollbar_height = max(30, int(scrollbar_area_height * list_area_height / self._content_height))
            scrollbar_y = list_area_top + 4 + int(
                (scrollbar_area_height - scrollbar_height) * self._scroll_offset / max_scroll)

            self._scrollbar_track_rect = QRect(
                self.width() - scrollbar_track_width - self._scrollbar_margin - 4,
                list_area_top + 4,
                scrollbar_track_width,
                list_area_height - 8
            )

            track_color = QColor(get_color('surface_light'))
            track_color.setAlpha(180)
            painter.setBrush(QBrush(track_color))
            painter.setPen(QColor(get_color('border_light')))
            painter.drawRoundedRect(self._scrollbar_track_rect, 4, 4)

            self._scrollbar_rect = QRect(
                self.width() - self._scrollbar_width - self._scrollbar_margin - 6,
                scrollbar_y,
                self._scrollbar_width,
                scrollbar_height
            )

            if self._dragging_scrollbar:
                scrollbar_color = QColor(get_color('accent'))
            elif self._scrollbar_hovered:
                scrollbar_color = QColor(get_color('accent'))
                scrollbar_color.setAlpha(200)
            else:
                scrollbar_color = QColor(get_color('border'))
                scrollbar_color.setAlpha(180)

            painter.setBrush(QBrush(scrollbar_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(self._scrollbar_rect, 5, 5)
        else:
            self._scrollbar_rect = None
            self._scrollbar_track_rect = None

        painter.end()

    def _get_max_scroll_offset(self) -> int:
        if not self._color_manager:
            return 0
        colors = self._color_manager.get_all_colors()
        num_items = len(colors)
        content_height = num_items * self._item_height
        visible_height = self.height() - self._header_height - 8
        max_scroll = content_height - visible_height
        return max(0, max_scroll)

    def wheelEvent(self, event):
        if self._collapsed:
            return

        delta = event.angleDelta().y()
        scroll_step = self._item_height

        if delta > 0:
            self._scroll_offset = max(0, self._scroll_offset - scroll_step)
        else:
            max_scroll = self._get_max_scroll_offset()
            self._scroll_offset = min(max_scroll, self._scroll_offset + scroll_step)

        self.update()

    def mousePressEvent(self, event):
        if self._collapsed:
            self.toggle_collapsed()
            return

        if self._toggle_btn_rect and self._toggle_btn_rect.contains(event.position().toPoint()):
            self.toggle_lines_requested.emit()
            return

        if self._scrollbar_rect and self._scrollbar_rect.contains(event.position().toPoint()):
            self._dragging_scrollbar = True
            self._scrollbar_drag_start_y = event.position().y()
            self._scrollbar_drag_start_offset = self._scroll_offset
            self.update()
            return

        if self._scrollbar_track_rect and self._scrollbar_track_rect.contains(event.position().toPoint()):
            max_scroll = self._get_max_scroll_offset()
            if max_scroll > 0:
                list_area_height = self.height() - self._header_height - 8
                scrollbar_area_height = list_area_height - 8

                click_y = event.position().y() - (self._header_height + 4)
                scroll_ratio = click_y / scrollbar_area_height
                self._scroll_offset = max(0, min(max_scroll, int(scroll_ratio * max_scroll)))
                self.update()
            return

        if not self._color_manager:
            return

        colors = self._color_manager.get_all_colors()
        y_offset = self._header_height + 12 - self._scroll_offset

        for mod_id in colors.keys():
            if y_offset - 12 <= event.position().y() <= y_offset + self._item_height - 12:
                if event.position().y() >= self._header_height:
                    self.legend_clicked.emit(mod_id)
                return
            y_offset += self._item_height

    def mouseReleaseEvent(self, event):
        if self._dragging_scrollbar:
            self._dragging_scrollbar = False
            self.update()

    def mouseMoveEvent(self, event):
        if self._collapsed:
            self.update()
            return

        if self._dragging_scrollbar:
            max_scroll = self._get_max_scroll_offset()
            if max_scroll > 0:
                list_area_height = self.height() - self._header_height - 8
                scrollbar_area_height = list_area_height - 8
                scrollbar_height = max(30, int(scrollbar_area_height * list_area_height / self._content_height))

                delta_y = event.position().y() - self._scrollbar_drag_start_y
                scroll_ratio = delta_y / (
                        scrollbar_area_height - scrollbar_height) if scrollbar_area_height > scrollbar_height else 0
                new_offset = self._scrollbar_drag_start_offset + int(scroll_ratio * max_scroll)
                self._scroll_offset = max(0, min(max_scroll, new_offset))
            self.update()
            return

        was_hovered = self._scrollbar_hovered
        self._scrollbar_hovered = self._scrollbar_rect and self._scrollbar_rect.contains(event.position().toPoint())

        if self._selected_mod_id:
            if was_hovered != self._scrollbar_hovered:
                self.update()
            return

        if not self._color_manager:
            if was_hovered != self._scrollbar_hovered:
                self.update()
            return

        colors = self._color_manager.get_all_colors()
        y_offset = self._header_height + 12 - self._scroll_offset
        found = False

        for mod_id in colors.keys():
            if y_offset - 12 <= event.position().y() <= y_offset + self._item_height - 12:
                if event.position().y() >= self._header_height:
                    self._highlight_mod_id = mod_id
                    self._hover_mod_id = mod_id
                    found = True
                break
            y_offset += self._item_height

        if not found:
            self._highlight_mod_id = None
            self._hover_mod_id = None

        self.update()

    def leaveEvent(self, event):
        self._scrollbar_hovered = False
        self._hover_mod_id = None
        self.update()


class DependencyLinesWidget(QWidget, ModHighlightMixin):
    colors_updated = pyqtSignal()

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        ModHighlightMixin.__init__(self)
        self._lines: List[DependencyLine] = []
        self._color_manager = DependencyColorManager()

        config = _get_dependency_lines_config()
        self._item_height = config['item_height']
        self._line_width = config['line_width']
        self._highlight_line_width = config['highlight_line_width']
        self._default_alpha = config['default_alpha']
        self._highlight_alpha = config['highlight_alpha']
        self._line_offset_step = config['line_offset_step']
        self._info_box_margin = config['info_box_margin']
        self._max_line_area_width = config['max_line_area_width']
        self._max_lines_in_area = config['max_lines_in_area']
        self._step_x = config['step_x']
        self._show_lines = True

        self._dependency_map: Dict[str, List[str]] = {}
        self._update_pending = False
        self._debouncer = Debouncer(
            self._do_update_dependencies,
            config_key="dependency_lines_delay"
        )

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

    def set_list_widget(self, list_widget: QListWidget):
        self._list_widget = list_widget

    def set_item_height(self, height: int):
        self._item_height = height

    def set_show_lines(self, show: bool):
        self._show_lines = show
        self.update()

    def toggle_lines(self):
        self._show_lines = not self._show_lines
        self.update()

    def is_showing_lines(self) -> bool:
        return self._show_lines

    def get_color_manager(self) -> DependencyColorManager:
        return self._color_manager

    def update_dependencies(
            self,
            dependency_map: Dict[str, List[str]]
    ):
        self._dependency_map = dependency_map or {}
        self._debouncer.trigger()

    def _do_update_dependencies(self):
        self._lines.clear()

        if not self._list_widget or not self._dependency_map:
            self._color_manager.clear()
            self.update()
            self.colors_updated.emit()
            return

        mod_list = []
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            if item and item.mod:
                mod_list.append(item.mod.id)

        if not mod_list:
            self._color_manager.clear()
            self.update()
            self.colors_updated.emit()
            return

        mod_row_map = {mod_id: row for row, mod_id in enumerate(mod_list)}

        target_mod_ids = []
        wrong_order_pairs = []

        for source_id in self._dependency_map.keys():
            if source_id not in mod_row_map:
                continue
            source_row = mod_row_map[source_id]
            for target_id in self._dependency_map[source_id]:
                if target_id not in mod_row_map:
                    continue
                target_row = mod_row_map[target_id]
                if target_row < source_row:
                    if target_id not in target_mod_ids:
                        target_mod_ids.append(target_id)
                else:
                    wrong_order_pairs.append((source_id, target_id))
                    if target_id not in target_mod_ids:
                        target_mod_ids.append(target_id)

        self._color_manager.rebuild(target_mod_ids)

        dependency_colors = self._color_manager.get_dependency_colors()
        target_index_map = {}
        color_index = 0
        for target_id in target_mod_ids:
            while dependency_colors[color_index % len(dependency_colors)] == dependency_colors[0]:
                color_index += 1
            target_index_map[target_id] = color_index
            color_index += 1

        for source_id in self._dependency_map.keys():
            if source_id not in mod_row_map:
                continue
            source_row = mod_row_map[source_id]
            target_mods = self._dependency_map[source_id]

            valid_targets = []
            for target_id in target_mods:
                if target_id in mod_row_map:
                    target_row = mod_row_map[target_id]
                    if target_row < source_row:
                        valid_targets.append((target_id, target_row))

            for target_id, target_row in valid_targets:
                color = self._color_manager.get_color_for_mod(target_id)
                target_offset_index = target_index_map.get(target_id, 0)

                line = DependencyLine(
                    source_id=source_id,
                    target_id=target_id,
                    source_row=source_row,
                    target_row=target_row,
                    color=color,
                    offset_index=target_offset_index,
                    source_offset=0,
                    target_offset=0,
                    is_wrong_order=False
                )
                self._lines.append(line)

        wrong_order_color = QColor(get_color('wrong_order'))
        for i, (source_id, target_id) in enumerate(wrong_order_pairs):
            source_row = mod_row_map[source_id]
            target_row = mod_row_map[target_id]
            line = DependencyLine(
                source_id=source_id,
                target_id=target_id,
                source_row=source_row,
                target_row=target_row,
                color=wrong_order_color,
                offset_index=i % 5,
                source_offset=0,
                target_offset=0,
                is_wrong_order=True
            )
            self._lines.append(line)

        self.update()
        self.colors_updated.emit()

    def clear_lines(self):
        self._lines.clear()
        self._color_manager.clear()
        self._dependency_map = {}
        self._debouncer.cancel()
        self.update()

    def update_scroll_positions(self):
        self.update()

    def _get_mod_rect(self, mod_id: str) -> Optional[QRect]:
        if not self._list_widget:
            return None
        for i in range(self._list_widget.count()):
            item = self._list_widget.item(i)
            if item and item.mod and item.mod.id == mod_id:
                return self._list_widget.visualItemRect(item)
        return None

    def paintEvent(self, event):
        if not self._show_lines or not self._lines:
            return

        if not self._list_widget:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        h_scroll_offset = self._get_horizontal_scroll_offset()
        painter.translate(-h_scroll_offset, 0)

        clip_rect = self.rect().translated(h_scroll_offset, 0)
        painter.setClipRect(clip_rect)

        lines_by_target: Dict[tuple[str, bool], List[DependencyLine]] = {}
        for line in self._lines:
            key = (line.target_id, line.is_wrong_order)
            if key not in lines_by_target:
                lines_by_target[key] = []
            lines_by_target[key].append(line)

        source_line_index: Dict[str, int] = {}
        for line in self._lines:
            source_id = line.source_id
            if source_id not in source_line_index:
                source_line_index[source_id] = 0
            line.source_offset = source_line_index[source_id]
            source_line_index[source_id] += 1

        source_line_count: Dict[str, int] = {}
        for source_id, count in source_line_index.items():
            source_line_count[source_id] = count
        source_line_index.clear()

        is_selected_enabled = False
        if self._selected_mod_id and self._list_widget:
            for i in range(self._list_widget.count()):
                item = self._list_widget.item(i)
                if item and item.mod.id == self._selected_mod_id:
                    is_selected_enabled = True
                    break

        for (target_id, is_wrong_order_group), target_lines in lines_by_target.items():
            if not target_lines:
                continue

            color = QColor(target_lines[0].color)

            if self._selected_mod_id and is_selected_enabled:
                highlight_mod_id = self._selected_mod_id
            else:
                highlight_mod_id = self._highlight_mod_id

            is_target_highlighted = highlight_mod_id == target_id
            has_highlighted_source = any(
                highlight_mod_id == line.source_id for line in target_lines
            )
            is_highlighted = is_target_highlighted or has_highlighted_source

            if self._selected_mod_id and is_selected_enabled:
                if is_highlighted:
                    color.setAlpha(self._highlight_alpha)
                else:
                    continue
            else:
                if is_highlighted:
                    color.setAlpha(self._highlight_alpha)
                else:
                    color.setAlpha(60)

            line_width = self._highlight_line_width if is_highlighted else self._line_width

            line_index = target_lines[0].offset_index % self._max_lines_in_area
            base_x = self._max_line_area_width - 6
            main_line_x = base_x - line_index * self._step_x

            target_rect = self._get_mod_rect(target_id)
            if not target_rect:
                continue

            valid_sources = []
            for line in target_lines:
                source_rect = self._get_mod_rect(line.source_id)
                if source_rect:
                    valid_sources.append((line, source_rect))

            if not valid_sources:
                continue

            valid_sources.sort(key=lambda x: x[0].source_row)

            target_y = target_rect.top() + target_rect.height() // 2

            source_ys = [source_rect.top() + source_rect.height() // 2 for _, source_rect in valid_sources]
            min_source_y = min(source_ys)
            max_source_y = max(source_ys)

            main_start_y = target_y
            if target_y <= min_source_y:
                main_end_y = max_source_y
            elif target_y >= max_source_y:
                main_end_y = min_source_y
            else:
                main_start_y = min(target_y, min_source_y)
                main_end_y = max(target_y, max_source_y)

            line_top = min(main_start_y, main_end_y)
            line_bottom = max(main_start_y, main_end_y)
            if line_bottom < 0 or line_top > self.height():
                continue

            pen = QPen(color)
            pen.setWidthF(line_width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)

            painter.drawLine(main_line_x, main_start_y, main_line_x, main_end_y)

            branch_end_x = self._max_line_area_width - 2
            painter.setPen(pen)
            painter.drawLine(main_line_x, target_y, branch_end_x, target_y)

            dot_radius = 4 if is_highlighted else 3
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(QPoint(branch_end_x, target_y), dot_radius, dot_radius)

            for i, (line, source_rect) in enumerate(valid_sources):
                source_id = line.source_id
                total_for_source = source_line_count.get(source_id, 1)
                position_in_source = line.source_offset

                item_height = source_rect.height()
                margin = max(6, item_height * 0.25)
                usable_height = item_height - 2 * margin

                if total_for_source == 1:
                    source_y = source_rect.top() + item_height // 2
                else:
                    step = usable_height / (total_for_source - 1)
                    source_y = int(source_rect.top() + margin + position_in_source * step)

                branch_end_x = self._max_line_area_width - 2
                center_y = source_rect.top() + item_height // 2

                painter.setPen(pen)
                if source_y == center_y:
                    painter.drawLine(main_line_x, center_y, branch_end_x, center_y)
                else:
                    offset_diff = abs(source_y - center_y)
                    base_bend = min(offset_diff, 16)
                    path = QPainterPath()
                    path.moveTo(main_line_x, center_y)
                    ctrl1_x = main_line_x + base_bend * 0.5
                    ctrl2_x = main_line_x + base_bend
                    path.cubicTo(ctrl1_x, center_y, ctrl2_x, source_y, branch_end_x, source_y)
                    painter.drawPath(path)

                arrow_size = 7 if is_highlighted else 5
                painter.setBrush(QBrush(color))
                painter.setPen(Qt.PenStyle.NoPen)

                arrow_points = [
                    QPoint(branch_end_x + arrow_size, source_y),
                    QPoint(branch_end_x - arrow_size // 2, source_y - arrow_size // 2),
                    QPoint(branch_end_x - arrow_size // 2, source_y + arrow_size // 2)
                ]
                painter.drawPolygon(QPolygon(arrow_points))

        painter.end()

    def _get_scroll_offset(self) -> int:
        if self._list_widget:
            return self._list_widget.verticalScrollBar().value()
        return 0

    def _get_horizontal_scroll_offset(self) -> int:
        if self._list_widget:
            return self._list_widget.horizontalScrollBar().value()
        return 0


class DependencyListWidget(QListWidget):
    def __init__(self, list_type: ListType = ListType.ENABLED, parent=None):
        super().__init__(parent)
        self.list_type = list_type
        self._dependency_widget: Optional[DependencyLinesWidget] = None
        self._mod_dependencies: Dict[str, List[str]] = {}
        self._show_dependency_lines = True

    def set_dependency_widget(self, widget: DependencyLinesWidget):
        self._dependency_widget = widget

    def set_mod_dependencies(self, dependencies: Dict[str, List[str]]):
        self._mod_dependencies = dependencies
        self._update_dependency_lines()

    def set_show_dependency_lines(self, show: bool):
        self._show_dependency_lines = show
        if self._dependency_widget:
            self._dependency_widget.set_show_lines(show)

    def toggle_dependency_lines(self):
        self._show_dependency_lines = not self._show_dependency_lines
        if self._dependency_widget:
            if self._show_dependency_lines:
                self._dependency_widget.set_show_lines(True)
                QTimer.singleShot(0, self._update_dependency_lines)
            else:
                self._dependency_widget.set_show_lines(False)

    def update_dependency_lines(self):
        self._update_dependency_lines()

    def _update_dependency_lines(self):
        if not self._dependency_widget or not self._show_dependency_lines:
            return

        self._dependency_widget.set_item_height(self.sizeHintForRow(0) or 25)
        self._dependency_widget.update_dependencies(self._mod_dependencies)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._dependency_widget:
            self._dependency_widget.setGeometry(self.rect())

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        if self._dependency_widget:
            self._dependency_widget.update()

    def rowsInserted(self, parent, start, end):
        super().rowsInserted(parent, start, end)
        QTimer.singleShot(0, self._update_dependency_lines)

    def rowsAboutToBeRemoved(self, parent, start, end):
        super().rowsAboutToBeRemoved(parent, start, end)
        QTimer.singleShot(0, self._update_dependency_lines)
