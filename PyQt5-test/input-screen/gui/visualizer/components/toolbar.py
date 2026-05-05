"""Top toolbar controls for the results visualizer."""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QWidget,
)


class ResultsToolbar(QWidget):
    """Encapsulates equation and action controls shown above the canvas."""

    add_chart_requested = pyqtSignal()
    chart_layout_toggled = pyqtSignal(bool)
    reorder_mode_changed = pyqtSignal(bool)
    export_requested = pyqtSignal()
    reference_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        control_layout = QHBoxLayout(self)
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(4)

        # Keep controls compact without hard-coding pixel heights.
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setStyleSheet(
            "QLabel { margin: 0px; }"
        )

        self.add_chart_btn = QPushButton("Add Equation")
        self.add_chart_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.add_chart_btn.clicked.connect(self.add_chart_requested.emit)
        control_layout.addWidget(self.add_chart_btn)

        self.chart_layout_btn = QPushButton("Chart Layout")
        self.chart_layout_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.chart_layout_btn.setCheckable(True)
        self.chart_layout_btn.setChecked(False)
        self.chart_layout_btn.toggled.connect(self.chart_layout_toggled.emit)
        control_layout.addWidget(self.chart_layout_btn)

        self.reorder_mode_btn = QPushButton("Reorder")
        self.reorder_mode_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.reorder_mode_btn.setCheckable(True)
        self.reorder_mode_btn.setChecked(False)
        self.reorder_mode_btn.toggled.connect(self.reorder_mode_changed.emit)
        control_layout.addWidget(self.reorder_mode_btn)

        control_layout.addStretch(1)

        self.ref_toggle_btn = QPushButton("Reference")
        self.ref_toggle_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.ref_toggle_btn.setCheckable(True)
        self.ref_toggle_btn.setChecked(False)
        self.ref_toggle_btn.toggled.connect(self.reference_toggled.emit)
        control_layout.addWidget(self.ref_toggle_btn)

        self.export_btn = QPushButton("Export Plot")
        self.export_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.export_btn.clicked.connect(self.export_requested.emit)
        self.export_btn.setEnabled(False)
        self.export_btn.hide()
        control_layout.addWidget(self.export_btn)
