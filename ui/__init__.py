"""
UI模块
包含所有UI组件、样式、主题管理等
"""

from .dependency_lines import DependencyLinesWidget, DependencyLegendWidget
from .draggable_list import DraggableListWidget
from .i18n import init_i18n, tr, Language
from .styles import apply_theme
from .theme_manager import init_theme_manager, get_theme_manager, get_color
from .toast_widget import ToastManager

__all__ = [
    'apply_theme',
    'init_theme_manager',
    'get_theme_manager',
    'get_color',
    'init_i18n',
    'tr',
    'Language',
    'ToastManager',
    'DependencyLinesWidget',
    'DependencyLegendWidget',
    'DraggableListWidget',
]
