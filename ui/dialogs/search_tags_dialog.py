from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QApplication
)

from ..i18n import tr
from ..styles import refresh_widget_style
from ..toast_widget import ToastManager


class SearchTagsDialog(QDialog):
    """标签化搜索一览表对话框"""

    SEARCH_TAGS = [
        ("tag", "tag_value", "tag_desc"),
        ("author", "author_name", "author_desc"),
        ("name", "mod_name", "name_desc"),
        ("id", "mod_id", "id_desc"),
        ("issue", "issue_type", "issue_desc"),
        ("workshopid", "workshop_id_value", "workshopid_desc"),
        ("desc", "desc_value", "desc_desc"),
        ("note", "note_text", "note_desc"),
        ("color", "color_value", "color_desc"),
    ]

    def __init__(self, parent=None, base_font_size=12):
        super().__init__(parent)
        self._base_font_size = base_font_size
        self.setWindowTitle(tr("search_tags_title"))
        self.setMinimumSize(650, 500)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.Window)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        title_label = QLabel(tr("search_tags_title"))
        title_label.setProperty("labelType", "dialog_title")
        refresh_widget_style(title_label)
        layout.addWidget(title_label)

        desc_label = QLabel(tr("search_tags_desc"))
        desc_label.setWordWrap(True)
        desc_label.setProperty("labelType", "settings_info")
        refresh_widget_style(desc_label)
        layout.addWidget(desc_label)

        self.table = QTableWidget()
        self.table.setProperty("tableType", "search_tags")
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([
            tr("search_tag_column"),
            tr("search_example_column"),
            tr("search_desc_column")
        ])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectItems)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self._populate_table()

        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)

        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()

        copy_btn = QPushButton(tr("copy_selected_tag"))
        copy_btn.clicked.connect(self._copy_selected_tag)
        btn_layout.addWidget(copy_btn)

        btn_layout.addStretch()

        close_btn = QPushButton(tr("close"))
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _populate_table(self):
        self.table.setRowCount(len(self.SEARCH_TAGS))

        for row, (tag, example, desc_key) in enumerate(self.SEARCH_TAGS):
            tag_item = QTableWidgetItem(f"@{tag}")
            tag_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, tag_item)

            example_item = QTableWidgetItem(f"@{tag}={tr(example)}")
            example_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            example_item.setForeground(tag_item.foreground())
            self.table.setItem(row, 1, example_item)

            desc_item = QTableWidgetItem(tr(desc_key))
            self.table.setItem(row, 2, desc_item)

    def _on_cell_double_clicked(self, row: int):
        self._copy_tag_at_row(row)

    def _copy_selected_tag(self):
        current_row = self.table.currentRow()
        if current_row >= 0:
            self._copy_tag_at_row(current_row)

    def _copy_tag_at_row(self, row: int):
        if row < 0 or row >= len(self.SEARCH_TAGS):
            return

        tag, example, _ = self.SEARCH_TAGS[row]
        tag_text = f"@{tag}={tr(example)}"

        clipboard = QApplication.clipboard()
        clipboard.setText(tag_text)

        ToastManager.show(tr("tag_copied").format(tag_text))
