from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, QLabel
)
from PyQt5.QtCore import Qt


class SimulationProgressWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("")
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 6, 10, 6)
        root.setSpacing(0)

        top = QHBoxLayout()
        top.setSpacing(8)

        self.status_label = QLabel("Idle")
        self.status_label.setFixedWidth(180)
        self.status_label.setStyleSheet("color: #000000; font-weight: bold; font-size: 13px;")

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(14)
        self.bar.setStyleSheet("""
            QProgressBar { background: #333; border-radius: 4px; border: none; }
            QProgressBar::chunk { background: #00c97a; border-radius: 4px; }
        """)

        self.pct_label = QLabel("0%")
        self.pct_label.setFixedWidth(40)
        self.pct_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.pct_label.setStyleSheet("color: #000000; font-weight: bold; font-size: 13px;")

        top.addWidget(self.status_label)
        top.addWidget(self.bar, 1)
        top.addWidget(self.pct_label)
        root.addLayout(top)

    def clear(self):
        self.bar.setValue(0)
        self.pct_label.setText("0%")
        self.pct_label.setStyleSheet("color: #000000; font-weight: bold; font-size: 13px;")
        self.status_label.setText("Running...")
        self.status_label.setStyleSheet("color: #000000; font-weight: bold; font-size: 13px;")

    def append(self, message: str):
        import re
        lines = message.split("\n")
        header = lines[0].strip()
        detail_lines = [l for l in lines[1:] if l.strip()]

        pct_match = re.search(r'\[PROGRESS:\s*(\d+)\]', header)
        pct = int(pct_match.group(1)) if pct_match else self.bar.value()

        section_match = re.search(r'\[SECTION:\s*(.+?)\]', header)
        if section_match:
            display = f"◆ {section_match.group(1)}"
        else:
            display = re.sub(r'\[PROGRESS:\s*\d+\]', '', header).strip()

        if not display:
            return

        self.bar.setValue(pct)
        self.pct_label.setText(f"{pct}%")

        # Forward to log widget if connected
        if hasattr(self, '_log_widget') and self._log_widget:
            self._log_widget.append_entry(pct, display, detail_lines)

    def set_status(self, text: str, success: bool = None):
        self.status_label.setText(text)
        if success is True:
            self.status_label.setStyleSheet("color: #00c97a; font-weight: bold; font-size: 13px;")
            self.bar.setValue(100)
            self.pct_label.setText("100%")
        elif success is False:
            self.status_label.setStyleSheet("color: #e24b4a; font-weight: bold; font-size: 13px;")
        else:
            self.status_label.setStyleSheet("color: #000000; font-weight: bold; font-size: 13px;")

    def show_saved_path(self, results_dir: str):
        pass

    def set_log_widget(self, log_widget):
        self._log_widget = log_widget