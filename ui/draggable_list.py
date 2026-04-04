import logging
from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QMimeData, QTimer, QByteArray, QDataStream, QIODevice, QPoint
from PyQt6.QtGui import QDrag, QColor, QPainter, QPen, QBrush
from PyQt6.QtWidgets import QListWidget, QAbstractItemView, QListView

from yh_mods_manager_sdk import ListType
from .dependency_lines import DependencyLinesWidget
from .theme_manager import get_color

logger = logging.getLogger(__name__)


class DraggableListWidget(QListWidget):
    MOD_MIME_TYPE = "application/x-mod"
    mods_moved = pyqtSignal(list, ListType, int)
    items_dropped = pyqtSignal()
    highlight_changed = pyqtSignal(str)
    clear_selection_requested = pyqtSignal()

    @classmethod
    def set_game_mime_type(cls, game_id: str):
        cls.MOD_MIME_TYPE = f"application/x-{game_id}-mod"

    def __init__(self, list_type: ListType = ListType.DISABLED, parent=None):
        super().__init__(parent)
        self.list_type = list_type
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(False)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self._drag_source_row = -1
        self._dependency_widget: Optional[DependencyLinesWidget] = None
        self._show_dependency_lines = True
        self._highlight_mod_id: Optional[str] = None
        self._pending_mod_ids: List[str] = []
        self._pending_source_type: ListType = ListType.DISABLED
        self._pending_drop_pos: int = -1
        self._drop_indicator_row: int = -1
        self._is_dragging: bool = False
        self._batch_operation: bool = False
        self._auto_scroll_timer = QTimer(self)
        self._auto_scroll_timer.timeout.connect(self._do_auto_scroll)
        self._scroll_direction = 0
        self._scroll_speed = 0

    def set_dependency_widget(self, widget: DependencyLinesWidget):
        self._dependency_widget = widget

    def get_dependency_widget(self) -> Optional[DependencyLinesWidget]:
        return self._dependency_widget

    def has_dependency_widget(self) -> bool:
        return self._dependency_widget is not None

    def is_showing_dependency_lines(self) -> bool:
        return self._show_dependency_lines

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

    def set_highlight_mod(self, mod_id: Optional[str]):
        """设置悬停高亮的Mod（掠过）"""
        if self._dependency_widget:
            self._dependency_widget.set_highlight_mod(mod_id, is_selected=False)
        self.highlight_changed.emit(mod_id or "")

    def _update_dependency_lines(self):
        try:
            if not self._dependency_widget:
                return

            if not self._show_dependency_lines:
                self._dependency_widget.set_show_lines(False)
                return

            self._dependency_widget.set_show_lines(True)
            item_height = self.sizeHintForRow(0) or 25
            self._dependency_widget.set_item_height(item_height)
            self._dependency_widget.update()
        except RuntimeError as e:
            logger.debug(f"Dependency lines update error: {e}")

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if not item:
            self.clear_selection_requested.emit()
            self.clearSelection()
        super().mousePressEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._dependency_widget:
            self._dependency_widget.setGeometry(0, 0, self.viewport().width(), self.viewport().height())

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)
        if self._dependency_widget:
            self._dependency_widget.setGeometry(0, 0, self.viewport().width(), self.viewport().height())
            self._dependency_widget.update_scroll_positions()
            self._dependency_widget.update()

    def rowsInserted(self, parent, start, end):
        super().rowsInserted(parent, start, end)
        if self.list_type == ListType.ENABLED and not self._batch_operation:
            QTimer.singleShot(0, self._update_dependency_lines)

    def rowsAboutToBeRemoved(self, parent, start, end):
        super().rowsAboutToBeRemoved(parent, start, end)
        if self.list_type == ListType.ENABLED and not self._batch_operation:
            QTimer.singleShot(0, self._update_dependency_lines)

    def begin_batch_operation(self):
        self._batch_operation = True

    def end_batch_operation(self):
        self._batch_operation = False
        if self.list_type == ListType.ENABLED:
            QTimer.singleShot(0, self._update_dependency_lines)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.list_type == ListType.ENABLED and self._dependency_widget:
            item = self.itemAt(event.pos())
            if item:
                self.set_highlight_mod(item.mod.id)
            else:
                self.set_highlight_mod(None)

    def leaveEvent(self, event):
        super().leaveEvent(event)
        if self.list_type == ListType.ENABLED and self._dependency_widget:
            self.set_highlight_mod(None)

    def startDrag(self, supported_actions):
        selected_items = self.selectedItems()
        if not selected_items:
            return

        mod_ids = []
        for item in selected_items:
            mod_ids.append(item.mod.id)

        mime_data = QMimeData()
        data = QByteArray()
        stream = QDataStream(data, QIODevice.OpenModeFlag.WriteOnly)
        stream.writeString(self.list_type.value.encode('utf-8'))
        stream.writeInt32(len(mod_ids))
        for mod_id in mod_ids:
            stream.writeString(mod_id.encode('utf-8'))
        mime_data.setData(self.MOD_MIME_TYPE, data)

        drag = QDrag(self)
        drag.setMimeData(mime_data)

        from PyQt6.QtGui import QPixmap
        pixmap = QPixmap(1, 1)
        pixmap.fill(Qt.GlobalColor.transparent)
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(0, 0))

        drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(self.MOD_MIME_TYPE):
            event.acceptProposedAction()
            self._is_dragging = True
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(self.MOD_MIME_TYPE):
            event.acceptProposedAction()
            pos = event.position().toPoint()
            item = self.itemAt(pos)
            if item:
                self._drop_indicator_row = self.row(item)
            else:
                self._drop_indicator_row = self.count()
            self._is_dragging = True
            self.viewport().update()

            viewport_height = self.viewport().height()
            y = pos.y()
            scroll_margin = 30

            if y < scroll_margin:
                self._scroll_direction = -1
                self._scroll_speed = max(1, (scroll_margin - y) // 5)
                if not self._auto_scroll_timer.isActive():
                    self._auto_scroll_timer.start(50)
            elif y > viewport_height - scroll_margin:
                self._scroll_direction = 1
                self._scroll_speed = max(1, (y - (viewport_height - scroll_margin)) // 5)
                if not self._auto_scroll_timer.isActive():
                    self._auto_scroll_timer.start(50)
            else:
                self._stop_auto_scroll()
        else:
            super().dragMoveEvent(event)

    def _do_auto_scroll(self):
        if self._scroll_direction == 0:
            return
        scrollbar = self.verticalScrollBar()
        new_value = scrollbar.value() + (self._scroll_direction * self._scroll_speed)
        new_value = max(scrollbar.minimum(), min(scrollbar.maximum(), new_value))
        scrollbar.setValue(new_value)

    def _stop_auto_scroll(self):
        self._auto_scroll_timer.stop()
        self._scroll_direction = 0
        self._scroll_speed = 0

    def dragLeaveEvent(self, event):
        self._drop_indicator_row = -1
        self._is_dragging = False
        self._stop_auto_scroll()
        self.viewport().update()
        super().dragLeaveEvent(event)

    def paintEvent(self, event):
        super().paintEvent(event)

        if self._is_dragging and self._drop_indicator_row >= 0:
            painter = QPainter(self.viewport())
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

            item = self.item(self._drop_indicator_row)
            if item:
                rect = self.visualItemRect(item)
                y_pos = rect.top()
            else:
                last_item = self.item(self.count() - 1) if self.count() > 0 else None
                if last_item:
                    last_rect = self.visualItemRect(last_item)
                    y_pos = last_rect.bottom()
                else:
                    y_pos = 0

            if 0 <= y_pos <= self.viewport().height():
                pen = QPen(QColor(get_color('drop_indicator')), 3)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)

                line_width = self.viewport().width() - 20
                painter.drawLine(10, y_pos, line_width, y_pos)

                painter.setBrush(QBrush(QColor(get_color('drop_indicator'))))
                painter.drawEllipse(10 - 3, y_pos - 3, 6, 6)
                painter.drawEllipse(line_width - 3, y_pos - 3, 6, 6)

            painter.end()

    def dropEvent(self, event):
        self._drop_indicator_row = -1
        self._is_dragging = False
        self._stop_auto_scroll()
        self.viewport().update()

        if event.mimeData().hasFormat(self.MOD_MIME_TYPE):
            data = event.mimeData().data(self.MOD_MIME_TYPE)
            stream = QDataStream(data, QIODevice.OpenModeFlag.ReadOnly)
            source_type_str = stream.readString().decode('utf-8')
            source_type = ListType(source_type_str)
            count = stream.readInt32()

            mod_ids = []
            for _ in range(count):
                mod_ids.append(stream.readString().decode('utf-8'))

            if source_type != self.list_type:
                event.acceptProposedAction()
                event.setDropAction(Qt.DropAction.MoveAction)
                drop_pos = self.indexAt(event.position().toPoint()).row()
                if drop_pos < 0:
                    drop_pos = self.count()
                self._pending_drop_pos = drop_pos
                self._pending_mod_ids = mod_ids
                self._pending_source_type = source_type
                QTimer.singleShot(50, self._emit_mods_moved)
            else:
                super().dropEvent(event)
                QTimer.singleShot(10, self.items_dropped.emit)
        else:
            super().dropEvent(event)
            QTimer.singleShot(10, self.items_dropped.emit)

    def _emit_mods_moved(self):
        try:
            if self._pending_mod_ids and not self.signalsBlocked():
                self.mods_moved.emit(list(self._pending_mod_ids), self._pending_source_type,
                                     int(self._pending_drop_pos))
        except RuntimeError:
            pass
        finally:
            self._pending_mod_ids = []
            self._pending_source_type = ListType.DISABLED
            self._pending_drop_pos = -1
