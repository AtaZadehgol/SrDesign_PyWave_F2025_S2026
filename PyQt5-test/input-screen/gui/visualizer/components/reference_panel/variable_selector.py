"""Variable selector module for the reference panel subpackage."""

from typing import Dict, List, Optional

from PyQt5.QtCore import Qt, QSignalBlocker, pyqtSignal
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QShortcut,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QComboBox,
)

from utils.file_handler import FileHandler


class VariableSelectorWidget(QWidget):
    """Selector table with grouped checkboxes for available variables."""

    selection_changed = pyqtSignal(list)

    def __init__(self, file_handler, parent=None):
        super().__init__(parent)

        self.file_handler = file_handler
        self.all_variables: List[str] = []
        self.measurement_point_info: List = []
        self._updating_variable_list: bool = False
        self._section_variable_rows: Dict[int, List[int]] = {}
        self.include_aggregates: bool = True
        self.surface_only_mode: bool = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        selector_header = QLabel("Available Variables")
        selector_header.setStyleSheet("QLabel { font-weight: 600; }")
        layout.addWidget(selector_header)

        self.select_all_btn = QPushButton("Select All")
        self.select_all_btn.clicked.connect(self.select_all)
        self.select_all_btn.setEnabled(False)

        self.deselect_all_btn = QPushButton("Deselect All")
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        self.deselect_all_btn.setEnabled(False)

        self.version_selector = QComboBox()
        self.version_selector.setEnabled(False)

        selector_controls = QHBoxLayout()
        selector_controls.addWidget(self.select_all_btn)
        selector_controls.addWidget(self.deselect_all_btn)
        selector_controls.addWidget(self.version_selector)
        selector_controls.addStretch(1)
        layout.addLayout(selector_controls)

        self.variable_list = QTableWidget()
        self.variable_list.setColumnCount(2)
        self.variable_list.setHorizontalHeaderLabels(["Variable", "Shape"])
        self.variable_list.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.variable_list.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.variable_list.verticalHeader().hide()
        self.variable_list.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.variable_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.variable_list.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.variable_list.itemChanged.connect(self._on_variable_item_changed)
        self.copy_variable_names_shortcut = QShortcut(QKeySequence.Copy, self.variable_list)
        self.copy_variable_names_shortcut.activated.connect(self.copy_selected_variable_names)
        self.variable_list.setEnabled(False)
        self.variable_list.setMinimumHeight(120)
        self.variable_list.setStyleSheet(
            "QTableWidget { border: none; gridline-color: transparent; }"
        )
        layout.addWidget(self.variable_list)

    def set_variable_sources(self, all_variables: List[str], measurement_point_info: List):
        """Set available variables and measurement-point metadata."""
        self.all_variables = list(all_variables)
        self.measurement_point_info = list(measurement_point_info)

    def set_include_aggregates(self, include_aggregates: bool):
        """Toggle display/selection of aggregate variables (e.g., *_mean)."""
        self.include_aggregates = bool(include_aggregates)

    def set_surface_only_mode(self, surface_only_mode: bool):
        """Show one row per measurement point instead of expanding fields."""
        self.surface_only_mode = bool(surface_only_mode)

    def sanitize_selected_variables(self, selected: Optional[List[str]]) -> List[str]:
        """Restrict selection to currently valid variables."""
        valid_variables: List[str] = []

        if self.surface_only_mode and self.measurement_point_info:
            valid_variables = [mp_info.safe_name for mp_info in self.measurement_point_info]
        elif self.measurement_point_info:
            for mp_info in self.measurement_point_info:
                for field in mp_info.available_fields:
                    var_base = f"{field}_{mp_info.safe_name}"
                    valid_variables.append(var_base)
                    if mp_info.num_points > 1 and self.include_aggregates:
                        valid_variables.append(f"{var_base}_mean")
        else:
            valid_variables = list(self.all_variables)

        if not valid_variables:
            return []
        if selected is None:
            return valid_variables
        if not selected:
            return []

        selected_set = set(selected)
        return [variable_name for variable_name in valid_variables if variable_name in selected_set]

    def update_result_versions(self):
        archived_names = self.file_handler.get_archived_names()
        blocker = QSignalBlocker(self.version_selector)
        self.version_selector.clear()
        self.version_selector.addItem("Current")
        self.version_selector.addItems(archived_names)
        del blocker
        self.version_selector.setEnabled(bool(archived_names))


    def populate(self, selected_variables: List[str]):
        """Populate variable table and apply selected state."""
        self._updating_variable_list = True
        self.variable_list.setRowCount(0)
        self._section_variable_rows = {}

        selected_set = set(selected_variables)
        current_row = 0

        if self.surface_only_mode and self.measurement_point_info:
            for mp_info in self.measurement_point_info:
                self.variable_list.insertRow(current_row)

                checkbox_item = QTableWidgetItem()
                checkbox_item.setText(mp_info.name)
                checkbox_item.setCheckState(
                    Qt.Checked if mp_info.safe_name in selected_set else Qt.Unchecked
                )
                checkbox_item.setData(Qt.UserRole, mp_info.safe_name)
                self.variable_list.setItem(current_row, 0, checkbox_item)

                type_label = mp_info.point_type
                if mp_info.num_points > 1:
                    type_label = f"{mp_info.point_type}, {mp_info.num_points} pts"
                self.variable_list.setItem(current_row, 1, QTableWidgetItem(type_label))
                current_row += 1

            has_variables = bool(self.measurement_point_info)
            self.variable_list.setEnabled(has_variables)
            self.select_all_btn.setEnabled(has_variables)
            self.deselect_all_btn.setEnabled(has_variables)
            self._updating_variable_list = False
            return

        if self.all_variables and not self.measurement_point_info:
            section_vars = list(self.all_variables)
            self.variable_list.insertRow(current_row)
            header = QTableWidgetItem("-- Standard Fields --")
            header.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            if all(var in selected_set for var in section_vars):
                header.setCheckState(Qt.Checked)
            elif any(var in selected_set for var in section_vars):
                header.setCheckState(Qt.PartiallyChecked)
            else:
                header.setCheckState(Qt.Unchecked)
            header.setBackground(Qt.lightGray)
            self.variable_list.setItem(current_row, 0, header)
            self.variable_list.setSpan(current_row, 0, 1, 2)
            section_row = current_row
            self._section_variable_rows[section_row] = []
            current_row += 1

            for variable_name in self.all_variables:
                self.variable_list.insertRow(current_row)

                checkbox_item = QTableWidgetItem()
                checkbox_item.setText(variable_name)
                checkbox_item.setCheckState(
                    Qt.Checked if variable_name in selected_set else Qt.Unchecked
                )
                checkbox_item.setData(Qt.UserRole, variable_name)
                self.variable_list.setItem(current_row, 0, checkbox_item)

                self.variable_list.setItem(current_row, 1, QTableWidgetItem(""))
                self._section_variable_rows[section_row].append(current_row)
                current_row += 1

        for mp_info in self.measurement_point_info:
            type_label = mp_info.point_type
            if mp_info.num_points > 1:
                type_label = f"{mp_info.point_type}, {mp_info.num_points} pts"

            section_vars = []
            for field in mp_info.available_fields:
                var_base = f"{field}_{mp_info.safe_name}"
                section_vars.append(var_base)
                if mp_info.num_points > 1 and self.include_aggregates:
                    section_vars.append(f"{var_base}_mean")

            self.variable_list.insertRow(current_row)
            header = QTableWidgetItem(f"-- {mp_info.name} ({type_label}) --")
            header.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            if all(var in selected_set for var in section_vars):
                header.setCheckState(Qt.Checked)
            elif any(var in selected_set for var in section_vars):
                header.setCheckState(Qt.PartiallyChecked)
            else:
                header.setCheckState(Qt.Unchecked)
            header.setBackground(Qt.lightGray)
            self.variable_list.setItem(current_row, 0, header)
            self.variable_list.setSpan(current_row, 0, 1, 2)
            section_row = current_row
            self._section_variable_rows[section_row] = []
            current_row += 1

            for field in mp_info.available_fields:
                var_base = f"{field}_{mp_info.safe_name}"

                if mp_info.num_points == 1:
                    self.variable_list.insertRow(current_row)

                    checkbox_item = QTableWidgetItem()
                    checkbox_item.setText(var_base)
                    checkbox_item.setCheckState(
                        Qt.Checked if var_base in selected_set else Qt.Unchecked
                    )
                    checkbox_item.setData(Qt.UserRole, var_base)
                    self.variable_list.setItem(current_row, 0, checkbox_item)
                    self.variable_list.setItem(current_row, 1, QTableWidgetItem(str(mp_info.shape)))

                    self._section_variable_rows[section_row].append(current_row)
                    current_row += 1
                else:
                    suffixes = [""]
                    if self.include_aggregates:
                        suffixes.append("_mean")

                    for suffix in suffixes:
                        var_name = f"{var_base}{suffix}"
                        self.variable_list.insertRow(current_row)

                        checkbox_item = QTableWidgetItem()
                        checkbox_item.setText(var_name)
                        checkbox_item.setCheckState(
                            Qt.Checked if var_name in selected_set else Qt.Unchecked
                        )
                        checkbox_item.setData(Qt.UserRole, var_name)
                        self.variable_list.setItem(current_row, 0, checkbox_item)

                        shape_text = str(mp_info.shape) if suffix == "" else "[1]"
                        self.variable_list.setItem(current_row, 1, QTableWidgetItem(shape_text))
                        self._section_variable_rows[section_row].append(current_row)
                        current_row += 1

        has_variables = bool(self.measurement_point_info) or bool(
            self.all_variables and not self.measurement_point_info
        )
        self.variable_list.setEnabled(has_variables)
        self.select_all_btn.setEnabled(has_variables)
        self.deselect_all_btn.setEnabled(has_variables)
        self._updating_variable_list = False

    def set_selected_variables(self, selected_variables: List[str]):
        """Sync table check states from selected variable names."""
        selected_set = set(selected_variables)
        self._updating_variable_list = True

        for row in range(self.variable_list.rowCount()):
            item = self.variable_list.item(row, 0)
            if not item:
                continue
            var_name = item.data(Qt.UserRole)
            if var_name:
                item.setCheckState(Qt.Checked if var_name in selected_set else Qt.Unchecked)

        self._updating_variable_list = False
        self._refresh_section_header_states()

    def get_checked_variables(self) -> List[str]:
        """Return currently checked variable names from the table."""
        selected = []
        for row in range(self.variable_list.rowCount()):
            item = self.variable_list.item(row, 0)
            if not item:
                continue
            var_name = item.data(Qt.UserRole)
            if var_name and item.checkState() == Qt.Checked:
                selected.append(var_name)
        return selected

    def select_all(self):
        """Select all variable rows and emit updated selection."""
        if not self.all_variables and not self.measurement_point_info:
            return
        self._updating_variable_list = True
        for row in range(self.variable_list.rowCount()):
            item = self.variable_list.item(row, 0)
            if item and item.data(Qt.UserRole):
                item.setCheckState(Qt.Checked)
        self._updating_variable_list = False
        self._refresh_section_header_states()
        self.selection_changed.emit(self.get_checked_variables())

    def deselect_all(self):
        """Deselect all variable rows and emit updated selection."""
        if not self.all_variables and not self.measurement_point_info:
            return
        self._updating_variable_list = True
        for row in range(self.variable_list.rowCount()):
            item = self.variable_list.item(row, 0)
            if item and item.data(Qt.UserRole):
                item.setCheckState(Qt.Unchecked)
        self._updating_variable_list = False
        self._refresh_section_header_states()
        self.selection_changed.emit([])

    def copy_selected_variable_names(self):
        """Copy selected variable names from current selected rows."""
        selected_rows = sorted({index.row() for index in self.variable_list.selectedIndexes()})

        names = []
        seen = set()
        for row in selected_rows:
            item = self.variable_list.item(row, 0)
            if not item:
                continue
            var_name = item.data(Qt.UserRole)
            if var_name and var_name not in seen:
                names.append(var_name)
                seen.add(var_name)

        if names:
            QApplication.clipboard().setText("\n".join(names))

    def _refresh_section_header_states(self):
        self._updating_variable_list = True
        for section_row, child_rows in self._section_variable_rows.items():
            header_item = self.variable_list.item(section_row, 0)
            if not header_item or not child_rows:
                continue

            checked_count = 0
            for row in child_rows:
                item = self.variable_list.item(row, 0)
                if item and item.checkState() == Qt.Checked:
                    checked_count += 1

            if checked_count == len(child_rows):
                header_item.setCheckState(Qt.Checked)
            elif checked_count == 0:
                header_item.setCheckState(Qt.Unchecked)
            else:
                header_item.setCheckState(Qt.PartiallyChecked)
        self._updating_variable_list = False

    def _on_variable_item_changed(self, changed_item: QTableWidgetItem):
        if self._updating_variable_list:
            return

        row = changed_item.row()
        if row in self._section_variable_rows:
            target_state = changed_item.checkState()
            if target_state == Qt.PartiallyChecked:
                target_state = Qt.Checked

            child_rows = self._section_variable_rows[row]
            self._updating_variable_list = True
            for child_row in child_rows:
                child_item = self.variable_list.item(child_row, 0)
                if child_item:
                    child_item.setCheckState(target_state)
            self._updating_variable_list = False

        self._refresh_section_header_states()
        self.selection_changed.emit(self.get_checked_variables())
