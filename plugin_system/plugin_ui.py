"""
插件UI扩展管理器
支持插件添加自定义面板到主窗口
"""

import logging
from typing import Dict, List, Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QMainWindow
)

if TYPE_CHECKING:
    from plugin_system import FeaturePlugin

logger = logging.getLogger(__name__)


class PluginPanelManager:
    """插件面板管理器
    
    管理插件添加的自定义面板，支持：
    - 左侧面板区域
    - 右侧面板区域
    - 底部面板区域
    - 中央面板区域（作为标签页）
    """

    PANEL_POSITIONS = {
        "left": Qt.DockWidgetArea.LeftDockWidgetArea,
        "right": Qt.DockWidgetArea.RightDockWidgetArea,
        "bottom": Qt.DockWidgetArea.BottomDockWidgetArea,
        "center": Qt.DockWidgetArea.RightDockWidgetArea,
    }

    def __init__(self, main_window: QMainWindow):
        self._main_window = main_window
        self._panels: Dict[str, QDockWidget] = {}
        self._panel_widgets: Dict[str, QWidget] = {}
        self._plugin_panels: Dict[str, List[str]] = {}

    def register_panel(
            self,
            plugin_id: str,
            panel_id: str,
            title: str,
            widget: QWidget,
            position: str = "right",
            icon: str = None,
            visible: bool = True
    ) -> bool:
        """注册插件面板
        
        Args:
            plugin_id: 插件ID
            panel_id: 面板唯一标识
            title: 面板标题
            widget: 面板Widget
            position: 面板位置 (left, right, bottom, center)
            icon: 图标路径或图标名
            visible: 默认是否可见
        
        Returns:
            是否注册成功
        """
        full_id = f"{plugin_id}_{panel_id}"

        if full_id in self._panels:
            return False

        dock_widget = QDockWidget(title, self._main_window)
        dock_widget.setWidget(widget)
        dock_widget.setObjectName(full_id)
        dock_widget.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetClosable
        )

        dock_area = self.PANEL_POSITIONS.get(position, Qt.DockWidgetArea.RightDockWidgetArea)
        self._main_window.addDockWidget(dock_area, dock_widget)

        if not visible:
            dock_widget.hide()

        self._panels[full_id] = dock_widget
        self._panel_widgets[full_id] = widget

        if plugin_id not in self._plugin_panels:
            self._plugin_panels[plugin_id] = []
        self._plugin_panels[plugin_id].append(full_id)

        return True

    def unregister_panel(self, plugin_id: str, panel_id: str) -> bool:
        """注销插件面板
        
        Args:
            plugin_id: 插件ID
            panel_id: 面板唯一标识
        
        Returns:
            是否注销成功
        """
        full_id = f"{plugin_id}_{panel_id}"

        if full_id not in self._panels:
            return False

        dock_widget = self._panels.pop(full_id)
        self._main_window.removeDockWidget(dock_widget)
        dock_widget.deleteLater()

        self._panel_widgets.pop(full_id, None)

        if plugin_id in self._plugin_panels:
            if full_id in self._plugin_panels[plugin_id]:
                self._plugin_panels[plugin_id].remove(full_id)
            if not self._plugin_panels[plugin_id]:
                del self._plugin_panels[plugin_id]

        return True

    def unregister_all_panels(self, plugin_id: str) -> None:
        """注销插件的所有面板
        
        Args:
            plugin_id: 插件ID
        """
        if plugin_id not in self._plugin_panels:
            return

        for full_id in self._plugin_panels[plugin_id].copy():
            panel_id = full_id.replace(f"{plugin_id}_", "", 1)
            self.unregister_panel(plugin_id, panel_id)

    def get_panel(self, plugin_id: str, panel_id: str) -> Optional[QWidget]:
        """获取插件面板Widget
        
        Args:
            plugin_id: 插件ID
            panel_id: 面板唯一标识
        
        Returns:
            面板Widget或None
        """
        full_id = f"{plugin_id}_{panel_id}"
        return self._panel_widgets.get(full_id)

    def show_panel(self, plugin_id: str, panel_id: str) -> None:
        """显示插件面板"""
        full_id = f"{plugin_id}_{panel_id}"
        if full_id in self._panels:
            self._panels[full_id].show()
            self._panels[full_id].raise_()

    def hide_panel(self, plugin_id: str, panel_id: str) -> None:
        """隐藏插件面板"""
        full_id = f"{plugin_id}_{panel_id}"
        if full_id in self._panels:
            self._panels[full_id].hide()

    def toggle_panel(self, plugin_id: str, panel_id: str) -> None:
        """切换插件面板可见性"""
        full_id = f"{plugin_id}_{panel_id}"
        if full_id in self._panels:
            if self._panels[full_id].isVisible():
                self._panels[full_id].hide()
            else:
                self._panels[full_id].show()
                self._panels[full_id].raise_()

    def get_all_panels(self, plugin_id: str = None) -> Dict[str, QDockWidget]:
        """获取所有面板
        
        Args:
            plugin_id: 插件ID，为None时返回所有面板
        
        Returns:
            面板字典
        """
        if plugin_id is None:
            return self._panels.copy()

        if plugin_id not in self._plugin_panels:
            return {}

        return {
            full_id: self._panels[full_id]
            for full_id in self._plugin_panels[plugin_id]
            if full_id in self._panels
        }

    def load_plugin_panels(self, plugin: "FeaturePlugin") -> None:
        """加载插件的所有面板
        
        Args:
            plugin: 功能插件实例
        """
        panels = plugin.get_panels()
        plugin_id = plugin.get_plugin_id()

        for panel_config in panels:
            panel_id = panel_config.get("id")
            title = panel_config.get("title", panel_id)
            position = panel_config.get("position", "right")
            widget_factory = panel_config.get("widget_factory")
            visible = panel_config.get("visible", True)

            if not panel_id or not widget_factory:
                continue

            try:
                widget = widget_factory()
                self.register_panel(
                    plugin_id=plugin_id,
                    panel_id=panel_id,
                    title=title,
                    widget=widget,
                    position=position,
                    visible=visible
                )
            except Exception as e:
                logger.error(f"Failed to create panel {panel_id} for plugin {plugin_id}: {e}")

    def unload_plugin_panels(self, plugin_id: str) -> None:
        """卸载插件的所有面板
        
        Args:
            plugin_id: 插件ID
        """
        self.unregister_all_panels(plugin_id)


_panel_manager: Optional[PluginPanelManager] = None


def init_panel_manager(main_window: QMainWindow) -> PluginPanelManager:
    """初始化面板管理器"""
    global _panel_manager
    _panel_manager = PluginPanelManager(main_window)
    return _panel_manager


def get_panel_manager() -> Optional[PluginPanelManager]:
    """获取面板管理器实例"""
    return _panel_manager
