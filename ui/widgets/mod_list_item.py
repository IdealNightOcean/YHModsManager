from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFontMetrics, QFont
from PyQt6.QtWidgets import QListWidgetItem, QStyledItemDelegate, QStyle, QStyleOptionViewItem

from yh_mods_manager_sdk import ListType, StatusType, Mod, ListItemState
from yh_mods_manager_sdk.enum_extension import EnumExtension
from utils.icons import IconManager, get_mod_type_icon, get_status_icon, get_tooltip_with_icon
from ..i18n import tr
from ..styles import FontSize, get_calculated_font_size, get_ui_constant
from ..theme_manager import get_color


def get_status_colors():
    return {
        StatusType.NORMAL: get_color('status_normal'),
        StatusType.WARNING: get_color('status_warning'),
        StatusType.ERROR: get_color('status_error'),
    }


class ModListItem(QListWidgetItem):

    def __init__(self, mod: Mod, show_order: bool = False, order: int = 0, is_masked: bool = False, parent=None):
        super().__init__(parent)
        self.mod = mod
        self.show_order = show_order
        self.order = order
        self.is_masked = is_masked
        self.update_display()

    def update_display(self):
        mod = self.mod
        self.setText(mod.display_name)

        tooltip_parts = []
        if mod.custom_name:
            tooltip_parts.append(f"{tr('custom_name')}: {mod.custom_name}")
            tooltip_parts.append(f"{tr('original_name')}: {mod.name}")
        else:
            tooltip_parts.append(f"{tr('info_name')}: {mod.name}")
        tooltip_parts.append(f"ID: {mod.original_id}")
        if mod.note:
            tooltip_parts.append(f"{tr('note')}: {mod.note}")

        for issue_status in EnumExtension.PREDEFINE_MOD_ISSUES_STATUS:
            if not mod.has_visible_issue(issue_status):
                continue

            details = mod.get_issue_details(issue_status)
            if not details:
                continue

            icon_name, color_key = "", "text"
            if issue_status in IconManager.STATUS_ICON_MAP:
                icon_name, color_key = IconManager.STATUS_ICON_MAP[issue_status]

            tooltip_parts.append("")
            tooltip_parts.append(get_tooltip_with_icon(tr(EnumExtension.get_issue_label_key(issue_status)), icon_name,
                                                       get_color(color_key), 14) + (":" if details else ""))

            if details:
                for detail in details:
                    tooltip_parts.append(f"  - {detail}")

        self.setToolTip("<br>".join(tooltip_parts))


class ModListDelegate(QStyledItemDelegate):
    def __init__(self, parent=None, base_font_size=11):
        super().__init__(parent)
        self._base_font_size = base_font_size
        self._default_tag_color = get_color('tag_default')

        self._status_bar_width = get_ui_constant('mod_list_item', 'status_bar_width', 4)
        self._order_box_width = get_ui_constant('mod_list_item', 'order_box_width', 28)
        self._order_box_height = get_ui_constant('mod_list_item', 'order_box_height', 20)
        self._info_box_padding = get_ui_constant('mod_list_item', 'info_box_padding', 8)
        self._box_spacing = get_ui_constant('mod_list_item', 'box_spacing', 6)
        self._border_radius = get_ui_constant('mod_list_item', 'border_radius', 6)
        self._order_font_size = get_ui_constant('mod_list_item', 'order_font_size', 9)
        self._item_height = get_ui_constant('mod_list_item', 'item_height', 32)
        self._box_height = get_ui_constant('mod_list_item', 'box_height', 26)

    @staticmethod
    def _get_status_color(mod: Mod) -> str:
        status_colors = get_status_colors()
        if mod.has_visible_static_issue():
            return status_colors[StatusType.ERROR]
        elif mod.has_visible_warning_issue():
            return status_colors[StatusType.WARNING]
        else:
            return status_colors[StatusType.NORMAL]

    @staticmethod
    def _get_text_color(mod: Mod) -> QColor:
        if mod.custom_color:
            return QColor(mod.custom_color)
        elif mod.has_visible_error_issue():
            return QColor(get_color('error'))
        elif mod.has_visible_warning_issue():
            return QColor(get_color('warning'))
        else:
            return QColor(get_color('text'))

    @staticmethod
    def _draw_rounded_box(painter: QPainter, rect: QRect, bg_color: QColor, border_color: QColor = None,
                          radius: int = 6):
        painter.setBrush(QBrush(bg_color))
        if border_color:
            painter.setPen(QPen(border_color, 1))
        else:
            painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, radius, radius)

    @staticmethod
    def _elide_text(text: str, fm: QFontMetrics, max_width: int) -> str:
        if fm.horizontalAdvance(text) <= max_width:
            return text
        return fm.elidedText(text, Qt.TextElideMode.ElideRight, max_width)

    def paint(self, painter, option, index):
        from PyQt6.QtCore import QRect

        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        parent = self.parent()
        item = parent.itemFromIndex(index) if parent else None

        if not item:
            if option.state & QStyle.StateFlag.State_Selected:
                painter.fillRect(option.rect, QColor(get_color('surface_selected')))
            elif option.state & QStyle.StateFlag.State_MouseOver:
                painter.fillRect(option.rect, QColor(get_color('surface_lighter')))
            else:
                if option.features & QStyleOptionViewItem.ViewItemFeature.Alternate:
                    painter.fillRect(option.rect, QColor(get_color('surface_light')))
                else:
                    painter.fillRect(option.rect, QColor(get_color('surface')))
            painter.restore()
            super().paint(painter, option, index)
            return

        mod = item.mod
        order = item.order

        main_window = parent.window() if parent else None

        item_state = ListItemState.NONE
        primary_id = None
        is_selected_enabled = False
        if main_window:
            item_state = main_window._selection_manager.get_state(mod.id)
            primary_id = main_window._selection_manager.get_primary_selection()
            if primary_id:
                is_selected_enabled = main_window.mod_manager.is_mod_enabled(primary_id)

        is_dependency_of_selected = False
        if primary_id and is_selected_enabled and primary_id != mod.id:
            deps = main_window.mod_manager.get_mod_dependencies(primary_id)
            if mod.id in deps:
                is_dependency_of_selected = True

        is_global_selected = bool(item_state & ListItemState.GLOBAL_SELECTED)
        is_multi_selected = bool(item_state & ListItemState.MULTI_SELECTED)
        is_any_selected = bool(item_state & ListItemState.SELECTED)

        is_enabled_list = parent.list_type == ListType.ENABLED if parent else False

        if option.features & QStyleOptionViewItem.ViewItemFeature.Alternate:
            painter.fillRect(option.rect, QColor(get_color('surface_light')))
        else:
            painter.fillRect(option.rect, QColor(get_color('surface')))

        font = option.font
        font.setPointSize(get_calculated_font_size(self._base_font_size, FontSize.SMALL))
        font.setBold(True)
        fm = QFontMetrics(font)
        item_height = option.rect.height()
        item_top = option.rect.top()
        item_left = option.rect.left()
        item_width = option.rect.width()

        if parent:
            viewport_width = parent.viewport().width()
            item_width = viewport_width

        item_right = item_left + item_width

        status_color_str = ModListDelegate._get_status_color(mod)
        status_color = QColor(status_color_str)

        text_color = ModListDelegate._get_text_color(mod)

        box_height = 26
        box_y = item_top + (item_height - box_height) // 2

        left_margin = 60 if is_enabled_list else 8
        current_x = item_left + left_margin

        order_font = QFont(font)
        order_font.setPointSize(get_calculated_font_size(self._order_font_size, FontSize.BASE))
        order_fm = QFontMetrics(order_font)
        order_text = str(order)
        order_box_width = order_fm.horizontalAdvance(order_text) + 8
        order_box_width = max(order_box_width, 22)
        order_box_rect = QRect(current_x, box_y, order_box_width, box_height)

        semi_transparent_status = QColor(status_color)
        semi_transparent_status.setAlpha(180)
        ModListDelegate._draw_rounded_box(painter, order_box_rect, semi_transparent_status, QColor(get_color('border')),
                                          self._border_radius)

        order_text_rect = QRect(current_x, box_y, order_box_width, box_height)
        order_text_color = QColor(get_color('text'))
        painter.setPen(QPen(order_text_color))
        painter.setFont(order_font)
        painter.drawText(order_text_rect, Qt.AlignmentFlag.AlignCenter, order_text)

        current_x = order_box_rect.right() + 6

        info_box_left = current_x
        info_box_width = item_right - 8 - info_box_left

        if info_box_width < 5:
            info_box_width = 5

        info_box_rect = QRect(info_box_left, box_y, info_box_width, box_height)

        plugin_highlight = None
        if main_window:
            from core.manager_collection import get_manager_collection
            manager_collection = get_manager_collection()
            highlight_manager = manager_collection.get_highlight_rule_manager()
            if highlight_manager:
                plugin_highlight = highlight_manager.get_highlight(mod)

        if is_global_selected or is_multi_selected or is_any_selected:
            info_bg_color = QColor(get_color('surface_selected'))
            info_border_color = QColor(get_color('surface_selected_hover'))
        elif is_dependency_of_selected:
            info_bg_color = QColor(get_color('surface_dependency_highlight'))
            info_border_color = QColor(get_color('border_dependency'))
        elif plugin_highlight:
            info_bg_color = QColor(plugin_highlight.background_color)
            info_border_color = QColor(plugin_highlight.border_color) if plugin_highlight.border_color else QColor(
                get_color('border'))
        elif option.state & QStyle.StateFlag.State_MouseOver:
            info_bg_color = QColor(get_color('surface_lighter'))
            info_border_color = QColor(get_color('border_light'))
        else:
            info_bg_color = QColor(get_color('surface_lighter'))
            info_bg_color.setAlpha(180)
            info_border_color = QColor(get_color('border'))

        ModListDelegate._draw_rounded_box(painter, info_box_rect, info_bg_color, info_border_color, self._border_radius)

        content_left = info_box_rect.left() + 8
        content_right = info_box_rect.right() - 8

        icon_size = 16
        icon_y = box_y + (box_height - icon_size) // 2
        icon_x = content_left

        mod_type_icon = get_mod_type_icon(mod.mod_type, icon_size)
        pixmap = mod_type_icon.pixmap(icon_size, icon_size)
        painter.drawPixmap(icon_x, icon_y, pixmap)

        current_x = icon_x + icon_size + 6

        status_icon_size = 16
        status_icon_y = box_y + (box_height - status_icon_size) // 2

        for issue_status in EnumExtension.PREDEFINE_MOD_ISSUES_STATUS:
            if mod.has_visible_issue(issue_status):
                icon = get_status_icon(issue_status, status_icon_size)
                pixmap = icon.pixmap(status_icon_size, status_icon_size)
                painter.drawPixmap(current_x, status_icon_y, pixmap)
                current_x += status_icon_size + 2

        max_text_width = content_right - current_x - 6
        if max_text_width < 0:
            max_text_width = 0

        mod_name = mod.display_name
        if fm.horizontalAdvance(mod_name) > max_text_width:
            mod_name = ModListDelegate._elide_text(mod_name, fm, max_text_width)

        text_rect = QRect(current_x, info_box_rect.top(), max_text_width, info_box_rect.height())

        painter.setPen(QPen(text_color))
        painter.setFont(font)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, mod_name)

        if item.is_masked:
            mask_color = QColor(get_color('surface'))
            mask_color.setAlpha(180)
            painter.fillRect(option.rect, mask_color)

        painter.restore()

    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(self._item_height)
        return size
