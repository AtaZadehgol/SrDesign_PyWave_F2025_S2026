"""Dialog widgets used by the results visualizer."""

from typing import Dict, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class PlotHistoryDialog(QDialog):
    """Dialog for selecting a previously plotted figure to re-display."""

    def __init__(self, plots, plot_domains, current_index, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Plot History")
        self.setMinimumSize(450, 300)
        self.selected_index = -1

        layout = QVBoxLayout(self)

        self.table = QTableWidget(len(plots), 2)
        self.table.setHorizontalHeaderLabels(["Title", "Domain"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().hide()

        for row, (title, _fig) in enumerate(plots):
            self.table.setItem(row, 0, QTableWidgetItem(title))
            domain = plot_domains[row] if row < len(plot_domains) else ""
            domain_label = "Time" if domain == "time" else "Frequency"
            self.table.setItem(row, 1, QTableWidgetItem(domain_label))

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)

        self.table.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("Show")
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        if 0 <= current_index < len(plots):
            self.table.selectRow(current_index)

    def _on_accept(self):
        row = self.table.currentRow()
        if row >= 0:
            self.selected_index = row
        self.accept()

    def _on_double_click(self, index):
        row = index.row()
        if row >= 0:
            self.selected_index = row
        self.accept()


class TemplateDialog(QDialog):
    """Dialog for selecting an equation template to load into the editor."""

    def __init__(
        self,
        templates,
        availability: Optional[Dict[int, str]] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle("Equation Templates")
        self.setMinimumSize(550, 350)
        self.selected_template = None
        self._availability = availability or {}

        layout = QVBoxLayout(self)

        self.table = QTableWidget(len(templates), 4)
        self.table.setHorizontalHeaderLabels(
            ["Name", "Expression", "Domain", "Description"]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().hide()

        for row, t in enumerate(templates):
            name_item = QTableWidgetItem(t.name)
            expr_item = QTableWidgetItem(t.expression)
            domain_label = "Time" if t.domain == "time" else "Frequency"
            domain_item = QTableWidgetItem(domain_label)
            desc_item = QTableWidgetItem(t.description)

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, expr_item)
            self.table.setItem(row, 2, domain_item)
            self.table.setItem(row, 3, desc_item)

            if row in self._availability:
                unavailable_msg = self._availability[row]
                for col in range(4):
                    item = self.table.item(row, col)
                    item.setForeground(Qt.gray)
                    item.setToolTip(unavailable_msg)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        self.table.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("Load")
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self._templates = templates

    def _on_accept(self):
        row = self.table.currentRow()
        if row in self._availability:
            QMessageBox.information(
                self, "Template Unavailable", self._availability[row]
            )
            return
        if 0 <= row < len(self._templates):
            self.selected_template = self._templates[row]
        self.accept()

    def _on_double_click(self, index):
        row = index.row()
        if row in self._availability:
            QMessageBox.information(
                self, "Template Unavailable", self._availability[row]
            )
            return
        if 0 <= row < len(self._templates):
            self.selected_template = self._templates[row]
        self.accept()
