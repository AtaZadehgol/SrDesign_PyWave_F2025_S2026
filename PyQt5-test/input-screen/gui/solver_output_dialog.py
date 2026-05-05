from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QListWidget, QListWidgetItem,
    QFrame, QTextEdit, QLabel
)
from PyQt5.QtCore import Qt


class SolverLogWidget(QFrame):
    """The step log + detail panel, lives inside SolverOutputDialog."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QFrame { background: #1e1e1e; }")
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(4)

        self.log_list = QListWidget()
        self.log_list.setStyleSheet("""
            QListWidget {
                background: #1e1e1e; border-top: 1px solid #333;
                border-left: none; border-right: none; border-bottom: none;
                font-family: 'Courier New'; font-size: 14px; color: #ffffff;
            }
            QListWidget::item { padding: 3px 4px; border-radius: 3px; }
            QListWidget::item:selected { background: #1a3a5c; color: #5af; }
            QListWidget::item:hover { background: #2a2a2a; }
        """)
        self.log_list.itemClicked.connect(self._on_step_clicked)
        root.addWidget(self.log_list)

        self.detail_frame = QFrame()
        self.detail_frame.setStyleSheet(
            "QFrame { border-left: 2px solid #00c97a; background: #252525; }"
        )
        detail_layout = QVBoxLayout(self.detail_frame)
        detail_layout.setContentsMargins(10, 6, 10, 6)
        self.detail_label = QTextEdit()
        self.detail_label.setReadOnly(True)
        self.detail_label.setFixedHeight(160)
        self.detail_label.setStyleSheet("""
            QTextEdit {
                background: #252525; color: #ffffff;
                font-family: 'Courier New'; font-size: 14px; border: none;
            }
        """)
        detail_layout.addWidget(self.detail_label)
        self.detail_frame.setVisible(False)
        root.addWidget(self.detail_frame)

    def clear(self):
        self.log_list.clear()
        self.detail_frame.setVisible(False)

    def append_entry(self, pct, display, detail_lines):
        item = QListWidgetItem(display)
        detail_text = "\n".join(detail_lines) if detail_lines else display
        item.setData(Qt.UserRole, detail_text)
        self.log_list.addItem(item)
        self.log_list.scrollToBottom()

    def _on_step_clicked(self, item):
        detail = item.data(Qt.UserRole)
        if self.detail_frame.isVisible() and self.detail_label.toPlainText() == detail:
            self.detail_frame.setVisible(False)
        else:
            self.detail_label.setPlainText(detail)
            self.detail_frame.setVisible(True)


class SolverOutputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Solver Output")
        self.setMinimumSize(800, 400)
        self.setStyleSheet("background: #1e1e1e;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.log_widget = SolverLogWidget()
        layout.addWidget(self.log_widget)

    def closeEvent(self, event):
        self.hide()
        event.ignore()