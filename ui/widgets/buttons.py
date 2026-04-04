from PyQt6.QtCore import Qt, QRect, QSize
from PyQt6.QtGui import QPainter, QColor, QPen, QFontMetrics, QPixmap
from PyQt6.QtWidgets import QPushButton, QSizePolicy

from yh_mods_manager_sdk import ModIssueStatus, StatusType
from yh_mods_manager_sdk.enum_extension import EnumExtension
from utils.icons import get_icon, get_svg_base64
from ..i18n import tr
from ..styles import get_ui_constant, get_calculated_font_size, FontSize
from ..theme_manager import get_color


def _get_color_button_size() -> int:
    return get_ui_constant('color_button', 'size', 28)


class TagButton(QPushButton):
    """标签按钮 - 使用自定义绘制实现动态背景色"""

    def __init__(self, text: str, color: str, base_font_size: int = 14, parent=None):
        super().__init__(parent)
        self._color = color
        self._base_font_size = base_font_size
        self._hover = False
        self._cached_size = None

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        font = self.font()
        font.setPointSize(get_calculated_font_size(base_font_size, FontSize.TINY))
        self.setFont(font)

        self.setFixedHeight(get_ui_constant('info_panel', 'tag_button_height', 24))

        self._update_text(text)

    def _update_text(self, text: str):
        self._display_text = f"🏷️ {text} ✕"
        self._cached_size = None
        self.updateGeometry()

    def sizeHint(self):
        if self._cached_size is None:
            fm = QFontMetrics(self.font())
            text_width = fm.horizontalAdvance(self._display_text)
            height = get_ui_constant('info_panel', 'tag_button_height', 24)
            self._cached_size = QSize(text_width + 12, height)
        return self._cached_size

    def minimumSizeHint(self):
        return self.sizeHint()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)

        bg_color = QColor(self._color)
        if self._hover:
            bg_color = QColor(get_color('error'))

        painter.setBrush(bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 10, 10)

        if self._hover:
            painter.setPen(QPen(QColor(get_color('danger_hover')), 1))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect, 10, 10)

        text_color = QColor(get_color('white'))
        painter.setPen(text_color)
        painter.setFont(self.font())

        text_rect = rect.adjusted(6, 0, -6, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self._display_text)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def set_color(self, color: str):
        self._color = color
        self.update()


class ColorButton(QPushButton):
    def __init__(self, color: str, parent=None):
        super().__init__(parent)
        self._color = color
        self._hover = False
        self._size = _get_color_button_size()
        self.setFixedSize(self._size, self._size)
        self.setMinimumSize(self._size, self._size)
        self.setMaximumSize(self._size, self._size)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("buttonType", "color_picker")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self._color))
        painter.drawEllipse(2, 2, self._size - 4, self._size - 4)
        if self._hover:
            painter.setPen(QPen(QColor(get_color('white')), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(2, 2, self._size - 4, self._size - 4)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)


class ClearColorButton(QPushButton):
    def __init__(self, base_font_size: int, parent=None):
        super().__init__(parent)
        self._base_font_size = base_font_size
        self._hover = False
        self._size = _get_color_button_size()
        self.setFixedSize(self._size, self._size)
        self.setMinimumSize(self._size, self._size)
        self.setMaximumSize(self._size, self._size)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("buttonType", "color_clear")
        self._update_icon()

    def _update_icon(self):
        color = get_color('error') if self._hover else get_color('text_secondary')
        icon = get_icon('remove_circle', color, self._size - 4)
        self.setIcon(icon)
        self.setIconSize(QRect(0, 0, self._size - 4, self._size - 4).size())

    def enterEvent(self, event):
        self._hover = True
        self._update_icon()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self._update_icon()
        super().leaveEvent(event)


class AddColorButton(QPushButton):
    def __init__(self, base_font_size: int, parent=None):
        super().__init__(parent)
        self._base_font_size = base_font_size
        self._hover = False
        self._size = _get_color_button_size()
        self.setFixedSize(self._size, self._size)
        self.setMinimumSize(self._size, self._size)
        self.setMaximumSize(self._size, self._size)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("buttonType", "color_add")
        self._update_icon()

    def _update_icon(self):
        color = get_color('accent') if self._hover else get_color('text_secondary')
        icon = get_icon('add_circle', color, self._size - 4)
        self.setIcon(icon)
        self.setIconSize(QRect(0, 0, self._size - 4, self._size - 4).size())

    def enterEvent(self, event):
        self._hover = True
        self._update_icon()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self._update_icon()
        super().leaveEvent(event)


class IssueBadgeButton(QPushButton):
    def __init__(self, issue_status: ModIssueStatus, display_name: str, is_ignored: bool,
                 base_font_size: int = 14, has_issue: bool = False, parent=None):
        super().__init__(parent)
        self._issue_status = issue_status
        self._display_name = display_name
        self._is_ignored = is_ignored
        self._base_font_size = base_font_size
        self._has_issue = has_issue
        self._hover = False
        self._cached_size = None
        self._icon_size = 14

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)

        font = self.font()
        font.setPointSize(get_calculated_font_size(base_font_size, FontSize.TINY))
        self.setFont(font)

        self.setFixedHeight(get_ui_constant('info_panel', 'tag_button_height', 24))
        self._update_tooltip()

    def _update_tooltip(self):
        if self._is_ignored:
            self.setToolTip(f"{tr('click_to_toggle_ignore')}\n{tr('unignore_issue')}")
        else:
            self.setToolTip(f"{tr('click_to_toggle_ignore')}\n{tr('ignore_issue')}")

    def _get_icon_info(self):
        if self._is_ignored:
            return 'eye_slash', 'text_secondary'
        elif self._has_issue:
            return 'warning', 'error'
        else:
            return 'eye_light', 'primary'

    def set_ignored(self, ignored: bool):
        self._is_ignored = ignored
        self._cached_size = None
        self._update_tooltip()
        self.update()

    def set_has_issue(self, has_issue: bool):
        self._has_issue = has_issue
        self._cached_size = None
        self.update()

    def issue_status(self) -> ModIssueStatus:
        return self._issue_status

    def is_ignored(self) -> bool:
        return self._is_ignored

    def sizeHint(self):
        if self._cached_size is None:
            fm = QFontMetrics(self.font())
            suffix = f" ({tr('issue_ignored')})" if self._is_ignored else ""
            text = f"{self._display_name}{suffix}"
            text_width = fm.horizontalAdvance(text)
            icon_width = self._icon_size + 4
            height = get_ui_constant('info_panel', 'tag_button_height', 24)
            self._cached_size = QSize(text_width + icon_width + 16, height)
        return self._cached_size

    def minimumSizeHint(self):
        return self.sizeHint()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)

        category = EnumExtension.get_issue_category(self._issue_status)
        if category == StatusType.ERROR:
            bg_color_key = 'error_bg'
        else:
            bg_color_key = 'warning_bg'

        if self._is_ignored:
            bg_color = QColor(get_color('text_disabled'))
            text_color = QColor(get_color('text'))
            border_color = QColor(get_color('border'))
        elif self._has_issue:
            bg_color = QColor(get_color(bg_color_key))
            text_color = QColor(get_color('text'))
            border_color = QColor(get_color('border_focus'))
        else:
            bg_color = QColor(get_color('surface_lighter'))
            bg_color.setAlpha(120)
            text_color = QColor(get_color('text'))
            border_color = QColor(get_color('border'))

        if self._hover and self._has_issue and not self._is_ignored:
            bg_color = bg_color.lighter(110)

        painter.setBrush(bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 10, 10)

        painter.setPen(QPen(border_color, 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect, 10, 10)

        icon_name, icon_color_key = self._get_icon_info()
        icon_color = get_color(icon_color_key)
        icon_b64 = get_svg_base64(icon_name, icon_color)
        if icon_b64:
            import base64
            icon_pixmap = QPixmap()
            icon_pixmap.loadFromData(base64.b64decode(icon_b64))
            icon_rect = QRect(6, (rect.height() - self._icon_size) // 2, self._icon_size, self._icon_size)
            painter.drawPixmap(icon_rect, icon_pixmap)

        painter.setPen(text_color)
        painter.setFont(self.font())

        suffix = f" ({tr('issue_ignored')})" if self._is_ignored else ""
        display_text = f"{self._display_name}{suffix}"

        text_left = 6 + self._icon_size + 4
        text_rect = rect.adjusted(text_left, 0, -6, 0)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, display_text)

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)
