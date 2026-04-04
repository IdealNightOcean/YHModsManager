import base64
import logging
import os
import re
from typing import Dict, Optional, Tuple

from PyQt6.QtCore import Qt, QByteArray
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtSvg import QSvgRenderer

from yh_mods_manager_sdk.enum_types import ActionTypes, ModIssueStatus, ModType
from ui.theme_manager import get_color
from utils.file_utils import get_resource_path

logger = logging.getLogger(__name__)


class IconManager:
    _instance: Optional['IconManager'] = None
    _cache: Dict[Tuple[str, str, int], QIcon] = {}
    _svg_cache: Dict[str, str] = {}
    _icon_dir: Optional[str] = None
    _color_replace_pattern = re.compile(
        r'(fill|stroke)=["\']#(?:ffffff|FFFFFF|fff|FFF)["\']|'
        r'(fill|stroke)=["\']white["\']|'
        r'(fill|stroke)=["\']WHITE["\']',
        re.IGNORECASE
    )

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def _get_icon_dir(cls) -> str:
        if cls._icon_dir is None:
            cls._icon_dir = get_resource_path('icons')
        return cls._icon_dir

    @classmethod
    def load_svg_file(cls, icon_name: str) -> Optional[str]:
        if icon_name in cls._svg_cache:
            return cls._svg_cache[icon_name]

        file_path = os.path.join(cls._get_icon_dir(),'svg', f'{icon_name}.svg')
        if not os.path.exists(file_path):
            return None

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()
            cls._svg_cache[icon_name] = svg_content
            return svg_content
        except Exception as e:
            logger.debug(f"Failed to load SVG file {icon_name}: {e}")
            return None

    @classmethod
    def replace_svg_colors(cls, svg_content: str, color: str) -> str:
        """统一的SVG颜色替换方法，使用正则表达式提高效率"""

        def replacer(match):
            attr = match.group(1) or match.group(2)
            return f'{attr}="{color}"'

        return cls._color_replace_pattern.sub(replacer, svg_content)

    @classmethod
    def get_icon(cls, icon_name: str, color: str = None, size: int = 24) -> QIcon:
        if color is None:
            color = get_color('text')

        cache_key = (icon_name, color, size)
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        icon = cls._create_icon(icon_name, color, size)
        cls._cache[cache_key] = icon
        return icon

    @classmethod
    def _create_icon(cls, icon_name: str, color: str, size: int) -> QIcon:
        pixmap = cls._create_pixmap(icon_name, color, size)
        return QIcon(pixmap)

    @classmethod
    def _create_pixmap(cls, icon_name: str, color: str, size: int) -> QPixmap:
        svg_content = cls.load_svg_file(icon_name)
        if not svg_content:
            return cls._create_placeholder_pixmap(size)

        svg_data = cls.replace_svg_colors(svg_content, color)

        renderer = QSvgRenderer(QByteArray(svg_data.encode('utf-8')))
        if not renderer.isValid():
            return cls._create_placeholder_pixmap(size)

        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        return pixmap

    @classmethod
    def _create_placeholder_pixmap(cls, size: int) -> QPixmap:
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setPen(QColor(get_color('text_secondary')))
        painter.drawRect(0, 0, size - 1, size - 1)
        painter.end()
        return pixmap

    @classmethod
    def clear_cache(cls):
        cls._cache.clear()
        cls._svg_cache.clear()

    @classmethod
    def get_mod_type_icon(cls, mod_type: ModType, size: int = 16) -> QIcon:
        match mod_type:
            case ModType.CORE:
                return cls.get_icon('letter_g', get_color('game_base'), size)
            case ModType.DLC:
                return cls.get_icon('letter_d', get_color('official_dlc'), size)
            case ModType.WORKSHOP:
                return cls.get_icon('steam', get_color('workshop_mod'), size)
            case _:
                return cls.get_icon('folder', get_color('warning'), size)

    STATUS_ICON_MAP = {
        ModIssueStatus.INCOMPLETE: ('error_circle', 'error'),
        ModIssueStatus.CUSTOM_STATIC_ERROR: ('error_circle', 'error'),
        ModIssueStatus.CUSTOM_DYNAMIC_ERROR: ('error_circle', 'error'),
        ModIssueStatus.MISSING_DEPENDENCIES: ('error_circle', 'missing_dependencies'),

        ModIssueStatus.CONFLICT: ('warn_outline', 'warning'),
        ModIssueStatus.VERSION_MISMATCH: ('warn_outline', 'warning'),
        ModIssueStatus.CUSTOM_STATIC_WARNING: ('warn_outline', 'warning'),
        ModIssueStatus.CUSTOM_DYNAMIC_WARNING: ('warn_outline', 'warning'),

        ModIssueStatus.ORDER_ERROR: ('warn_sort', 'warning'),
        ModIssueStatus.DUPLICATE: ('duplicate', 'warning'),
    }

    @staticmethod
    def get_status_icon(status_type: ModIssueStatus, size: int = 16) -> QIcon:
        if status_type in IconManager.STATUS_ICON_MAP:
            icon_name, color_key = IconManager.STATUS_ICON_MAP[status_type]
            return IconManager.get_icon(icon_name, get_color(color_key), size)

        return IconManager.get_icon('info', get_color('text_secondary'), size)

    ACTION_ICON_MAP = {
        ActionTypes.COPY: ('content_copy', 'text'),
        ActionTypes.LOCATE: ('aiming', 'text'),
        ActionTypes.FOLDER: ('folder', 'text'),
        ActionTypes.STEAM: ('steam', 'workshop_mod'),
    }

    @staticmethod
    def get_action_icon(action_type: ActionTypes, size: int = 16) -> QIcon:
        if action_type in IconManager.ACTION_ICON_MAP:
            icon_name, color_key = IconManager.ACTION_ICON_MAP[action_type]
            return IconManager.get_icon(icon_name, get_color(color_key), size)

        return IconManager.get_icon('info', get_color('text_secondary'), size)


def get_icon(icon_name: str, color: str = None, size: int = 24) -> QIcon:
    return IconManager.get_icon(icon_name, color, size)


def get_mod_type_icon(mod_type, size: int = 16) -> QIcon:
    return IconManager.get_mod_type_icon(mod_type, size)


def get_status_icon(status_type: ModIssueStatus, size: int = 16) -> QIcon:
    return IconManager.get_status_icon(status_type, size)


def get_action_icon(action_type: ActionTypes, size: int = 16) -> QIcon:
    return IconManager.get_action_icon(action_type, size)


def get_svg_base64(icon_name: str, color: str = None) -> str:
    if color is None:
        color = get_color('text')

    svg_content = IconManager.load_svg_file(icon_name)
    if not svg_content:
        return ""

    svg_data = IconManager.replace_svg_colors(svg_content, color)

    svg_bytes = svg_data.encode('utf-8')
    return base64.b64encode(svg_bytes).decode('utf-8')


def get_tooltip_with_icon(text: str, icon_name: str, color: str = None, size: int = 14) -> str:
    b64_data = get_svg_base64(icon_name, color)
    if not b64_data:
        return text
    return f'<img src="data:image/svg+xml;base64,{b64_data}" width="{size}" height="{size}" style="vertical-align: middle;"> {text}'
