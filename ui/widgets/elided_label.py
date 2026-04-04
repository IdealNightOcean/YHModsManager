from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFontMetrics, QCursor
from PyQt6.QtWidgets import QLabel, QApplication

from ..i18n import tr
from ..toast_widget import ToastManager


class ElidedLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, text: str = "", parent=None, copyable: bool = False,
                 max_lines: int = 1, elide_mode: Qt.TextElideMode = Qt.TextElideMode.ElideRight):
        super().__init__(parent)
        self._full_text = text
        self._copyable = copyable
        self._max_lines = max_lines
        self._elide_mode = elide_mode
        self._elided = False

        if copyable:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        super().setText(text)

    def setCopyable(self, copyable: bool):
        self._copyable = copyable
        if copyable:
            self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        else:
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))

    def setText(self, text: str):
        self._full_text = text
        self._elided = False
        super().setText(text)
        QTimer.singleShot(0, self._update_elide)

    def text(self) -> str:
        return self._full_text

    def fullText(self) -> str:
        return self._full_text

    def setMaxLines(self, lines: int):
        self._max_lines = lines
        self._update_elide()

    def setStyleSheet(self, style: str):
        super().setStyleSheet(style)
        QTimer.singleShot(0, self._update_elide)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_elide()

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(10, self._update_elide)

    def _update_elide(self):
        if not self._full_text:
            self.setToolTip("")
            self._elided = False
            return

        fm = QFontMetrics(self.font())
        available_width = self.width()

        if available_width <= 0:
            return

        if self._max_lines == 1:
            text_width = fm.horizontalAdvance(self._full_text)
            if text_width > available_width:
                elided = fm.elidedText(self._full_text, self._elide_mode, available_width)
                super().setText(elided)
                self._elided = True
            else:
                super().setText(self._full_text)
                self._elided = False
        else:
            lines = []
            remaining = self._full_text
            elided = False

            for i in range(self._max_lines):
                if not remaining:
                    break

                if i == self._max_lines - 1:
                    text_width = fm.horizontalAdvance(remaining)
                    if text_width > available_width:
                        lines.append(fm.elidedText(remaining, self._elide_mode, available_width))
                        elided = True
                    else:
                        lines.append(remaining)
                else:
                    for j, char in enumerate(remaining):
                        if fm.horizontalAdvance(remaining[:j + 1]) > available_width:
                            chars = j
                            break
                    else:
                        chars = len(remaining)

                    if chars > 0:
                        lines.append(remaining[:chars])
                        remaining = remaining[chars:]
                    else:
                        break

            super().setText('\n'.join(lines))
            self._elided = elided

        if self._elided or len(self._full_text) > 50:
            self.setToolTip(self._full_text)
        else:
            self.setToolTip("")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._copyable:
            self._copy_to_clipboard()
        super().mousePressEvent(event)

    def _copy_to_clipboard(self):
        if not self._full_text:
            return

        clipboard = QApplication.clipboard()
        clipboard.setText(self._full_text)

        global_pos = self.mapToGlobal(self.rect().center())
        ToastManager.show_at_click(tr("copied_to_clipboard").format(self._full_text), global_pos, duration=2000)
        self.clicked.emit()
