"""
Interactive results widget with embedded matplotlib graphs
"""

import math

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QTextBrowser,
    QDialog,
    QSizePolicy,
)
from PyQt5.QtCore import Qt, QSignalBlocker, QTimer
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import json
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import traceback

from .chart_pane import ChartPaneWidget
from .results_loader import ResultsLoader
from .plot_creator import PlotCreator
from .components.dialogs import PlotHistoryDialog, TemplateDialog
from .components.toolbar import ResultsToolbar
from .components.reference_panel.help_content import (
    build_reference_html,
    default_reference_html,
)
from .components.reference_panel.variable_selector import VariableSelectorWidget


class ResultsWidget(QWidget):
    """
    Interactive results display widget with matplotlib integration

    Features:
    - Interactive matplotlib plots with pan, zoom, and hover
    - Multiple plot views via dropdown selector
    - Export functionality for saving plots
    - Strategy pattern for different visualization types
    """

    def __init__(self, file_handler=None, parent=None):
        super().__init__(parent)

        self.file_handler = file_handler
        self.plot_creator: Optional[PlotCreator] = None
        self.plots: List[Tuple[str, Figure]] = []
        self.plot_domains: List[str] = []
        self.current_plot_index: int = -1
        self.max_history_per_pane: int = 10
        self.chart_panes: List[ChartPaneWidget] = []
        self.active_chart_pane: Optional[ChartPaneWidget] = None
        self.grid_rows: int = 1
        self.grid_cols: int = 1
        self.pane_row_height: int = 320
        self.pane_col_width: int = 400
        self.reorder_mode_enabled: bool = False
        self.chart_grid_rows_key: str = "chart_grid_rows"
        self.chart_grid_cols_key: str = "chart_grid_cols"
        self.project_root_path: Optional[Path] = None
        self.current_project_path: Optional[Path] = None
        self.active_results_path: Optional[Path] = None
        self.active_version_name: str = "Current"
        self._is_loading_results: bool = False
        self.simulation_type: str = ""
        self.polarization_mode: str = ""
        self.dimension: str = "2D"
        self.all_variables: List[str] = []
        self.selected_variables: List[str] = []
        self.measurement_point_info: List = []
        self.selection_metadata_key = "selected_variables_chart"
        self.legacy_selection_metadata_key = "selected_variables"
        self._loaded_results_identity: Optional[str] = None

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Control bar: extracted toolbar module
        self.toolbar_controls = ResultsToolbar(self)
        self.toolbar_controls.add_chart_requested.connect(self._on_add_chart_requested)
        self.toolbar_controls.chart_layout_toggled.connect(self._on_chart_layout_panel_toggled)
        self.toolbar_controls.reorder_mode_changed.connect(self._on_reorder_mode_changed)
        self.toolbar_controls.export_requested.connect(self._export_current_plot)
        self.toolbar_controls.reference_toggled.connect(lambda _checked: self._toggle_reference_panel())

        self.add_chart_btn = self.toolbar_controls.add_chart_btn
        self.chart_layout_btn = self.toolbar_controls.chart_layout_btn
        self.reorder_mode_btn = self.toolbar_controls.reorder_mode_btn
        self.ref_toggle_btn = self.toolbar_controls.ref_toggle_btn
        self.export_btn = self.toolbar_controls.export_btn

        layout.addWidget(self.toolbar_controls)

        # Splitter: plot canvas (left) + reference panel (right)
        self.splitter = QSplitter(Qt.Horizontal)

        # Scroll area for matplotlib canvas
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.chart_grid_container: Optional[QWidget] = None
        self.splitter.addWidget(self.scroll_area)

        # Reference panel (collapsible, on the right)
        self.ref_panel_container = QWidget()
        self.ref_panel_layout = QVBoxLayout(self.ref_panel_container)
        self.ref_panel_layout.setContentsMargins(6, 6, 6, 6)

        self.ref_vertical_splitter = QSplitter(Qt.Vertical)
        self.ref_vertical_splitter.setChildrenCollapsible(False)

        self.variable_selector = VariableSelectorWidget(
            file_handler=self.file_handler,
            parent=self,
        )
        self.variable_selector.selection_changed.connect(self._apply_variable_selection)
        self.variable_selector.version_selector.currentTextChanged.connect(
            self._on_result_version_changed
        )

        self.ref_panel = QTextBrowser()
        self.ref_panel.setOpenExternalLinks(False)
        self.ref_vertical_splitter.addWidget(self.variable_selector)
        self.ref_panel.setHtml(self._default_reference_html())
        self.ref_vertical_splitter.addWidget(self.ref_panel)
        self.ref_vertical_splitter.setStretchFactor(0, 0)
        self.ref_vertical_splitter.setStretchFactor(1, 1)
        self.ref_vertical_splitter.setSizes([220, 320])
        self.ref_panel_layout.addWidget(self.ref_vertical_splitter)

        self.ref_panel_container.setMinimumWidth(200)
        self.ref_panel_container.setMaximumWidth(350)
        self.ref_panel_container.hide()
        self.splitter.addWidget(self.ref_panel_container)

        # Chart Layout panel (collapsible, right side, sibling to reference panel)
        self.chart_layout_panel_container = QWidget()
        _clp_layout = QVBoxLayout(self.chart_layout_panel_container)
        _clp_layout.setContentsMargins(6, 6, 6, 6)
        _clp_layout.setSpacing(8)

        _clp_title = QLabel("Chart Layout")
        _clp_title.setStyleSheet("QLabel { font-weight: 600; }")
        _clp_layout.addWidget(_clp_title)

        _grid_form = QGridLayout()
        _grid_form.setSpacing(6)
        _grid_form.addWidget(QLabel("Rows:"), 0, 0)
        self.grid_rows_spinbox = QSpinBox()
        self.grid_rows_spinbox.setMinimum(1)
        self.grid_rows_spinbox.setMaximum(8)
        self.grid_rows_spinbox.setValue(self.grid_rows)
        self.grid_rows_spinbox.valueChanged.connect(self._on_grid_rows_changed)
        _grid_form.addWidget(self.grid_rows_spinbox, 0, 1)
        _grid_form.addWidget(QLabel("Columns:"), 1, 0)
        self.grid_cols_spinbox = QSpinBox()
        self.grid_cols_spinbox.setMinimum(1)
        self.grid_cols_spinbox.setMaximum(8)
        self.grid_cols_spinbox.setValue(self.grid_cols)
        self.grid_cols_spinbox.valueChanged.connect(self._on_grid_cols_changed)
        _grid_form.addWidget(self.grid_cols_spinbox, 1, 1)
        _clp_layout.addLayout(_grid_form)

        _clp_layout.addWidget(QLabel("Presets:"))

        _presets_row1 = QHBoxLayout()
        _presets_row1.setSpacing(4)
        for _pt, (_pr, _pc) in [("1×1", (1, 1)), ("1×2", (1, 2)), ("2×1", (2, 1))]:
            _btn = QPushButton(_pt)
            _btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
            _btn.clicked.connect(lambda _chk=False, r=_pr, c=_pc: self._apply_grid_preset(r, c))
            _presets_row1.addWidget(_btn)
        _clp_layout.addLayout(_presets_row1)

        _presets_row2 = QHBoxLayout()
        _presets_row2.setSpacing(4)
        for _pt, (_pr, _pc) in [("2×2", (2, 2)), ("2×3", (2, 3)), ("3×3", (3, 3))]:
            _btn = QPushButton(_pt)
            _btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
            _btn.clicked.connect(lambda _chk=False, r=_pr, c=_pc: self._apply_grid_preset(r, c))
            _presets_row2.addWidget(_btn)
        _clp_layout.addLayout(_presets_row2)

        self.effective_layout_label = QLabel("")
        self.effective_layout_label.setStyleSheet("QLabel { color: #555; font-style: italic; }")
        self.effective_layout_label.setWordWrap(True)
        _clp_layout.addWidget(self.effective_layout_label)

        # Pane height slider
        _clp_layout.addWidget(QLabel("Pane Height:"))
        self.pane_size_slider = QSlider(Qt.Horizontal)
        self.pane_size_slider.setMinimum(150)
        self.pane_size_slider.setMaximum(800)
        self.pane_size_slider.setSingleStep(10)
        self.pane_size_slider.setPageStep(50)
        self.pane_size_slider.setValue(self.pane_row_height)
        self.pane_size_slider.setTickPosition(QSlider.TicksBelow)
        self.pane_size_slider.setTickInterval(100)
        self.pane_size_slider.valueChanged.connect(self._on_pane_size_changed)
        _clp_layout.addWidget(self.pane_size_slider)
        self.pane_size_label = QLabel(f"{self.pane_row_height} px")
        self.pane_size_label.setStyleSheet("QLabel { color: #555; font-size: 9pt; }")
        _clp_layout.addWidget(self.pane_size_label)

        # Pane width slider
        _clp_layout.addWidget(QLabel("Pane Width:"))
        self.pane_width_slider = QSlider(Qt.Horizontal)
        self.pane_width_slider.setMinimum(200)
        self.pane_width_slider.setMaximum(1200)
        self.pane_width_slider.setSingleStep(10)
        self.pane_width_slider.setPageStep(50)
        self.pane_width_slider.setValue(self.pane_col_width)
        self.pane_width_slider.setTickPosition(QSlider.TicksBelow)
        self.pane_width_slider.setTickInterval(200)
        self.pane_width_slider.valueChanged.connect(self._on_pane_col_width_changed)
        _clp_layout.addWidget(self.pane_width_slider)
        self.pane_width_label = QLabel(f"{self.pane_col_width} px")
        self.pane_width_label.setStyleSheet("QLabel { color: #555; font-size: 9pt; }")
        _clp_layout.addWidget(self.pane_width_label)

        _clp_layout.addStretch(1)
        self.chart_layout_panel_container.setMinimumWidth(180)
        self.chart_layout_panel_container.setMaximumWidth(260)
        self.chart_layout_panel_container.hide()
        self.splitter.addWidget(self.chart_layout_panel_container)
        self.splitter.splitterMoved.connect(
            lambda _pos, _index: QTimer.singleShot(0, self._refresh_all_chart_panes)
        )

        # Give most space to the plot area
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setStretchFactor(2, 0)

        layout.addWidget(self.splitter)

        self._add_chart_pane(set_active=True)

    def _show_placeholder_message(self, message: str):
        """Show placeholder text in the active chart pane."""
        pane = self._active_or_first_chart_pane()
        if pane is not None:
            pane.show_placeholder_message(message)

    def _on_plot_equation(self, pane: Optional[ChartPaneWidget] = None):
        """Evaluate and plot a user-entered equation."""
        pane = pane or self._active_or_first_chart_pane()
        if pane is None:
            return

        expression = pane.equation_input.text().strip()
        if not expression:
            QMessageBox.warning(
                self, "No Equation Error", "Please enter an equation to plot."
            )
            return

        domain = pane.current_domain()
        display_mode = pane.current_freq_mode() if domain == "frequency" else "real_imag"
        analyzer = getattr(self.plot_creator, "analyzer", None)
        if not analyzer:
            QMessageBox.critical(
                self, "Analyzer Error", "No analyzer loaded to evaluate the equation."
            )
            return

        try:
            title = f"{expression} ({domain})"
            fig = analyzer.plot_equation(expression, domain, title=title, display_mode=display_mode)
            self._set_active_chart_pane(pane)
            pane.add_plot(title, fig, domain)
            self.current_plot_index = pane.current_plot_index
            self.export_btn.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Equation Plotting Error", str(e))

    def _on_open_history(self, pane: Optional[ChartPaneWidget] = None):
        """Open the plot history dialog to select a past plot."""
        pane = pane or self._active_or_first_chart_pane()
        if pane is None or not pane.plots:
            return

        dialog = pane.open_history_dialog()
        if dialog.exec_() == QDialog.Accepted and dialog.selected_index >= 0:
            self._on_plot_selected(dialog.selected_index, pane)

    def _on_open_templates(self, pane: Optional[ChartPaneWidget] = None):
        """Open the template selection dialog and load into equation editor."""
        pane = pane or self._active_or_first_chart_pane()
        if pane is None:
            return

        self._set_active_chart_pane(pane)
        analyzer = getattr(self.plot_creator, "analyzer", None)
        if not analyzer:
            return

        templates = analyzer.get_templates()
        if not templates:
            QMessageBox.information(
                self, "Templates", "No templates available for this simulation type."
            )
            return

        unavailable_templates = self._get_unavailable_template_messages(templates)
        dialog = TemplateDialog(templates, unavailable_templates, self)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_template:
            t = dialog.selected_template
            pane.set_equation_text(t.expression)
            pane.set_domain(t.domain)

    def _create_chart_pane(self) -> ChartPaneWidget:
        pane = ChartPaneWidget(self, max_plot_history=self.max_history_per_pane)
        pane.plot_requested.connect(self._on_plot_equation)
        pane.templates_requested.connect(self._on_open_templates)
        pane.history_requested.connect(self._on_open_history)
        pane.move_up_requested.connect(self._on_move_chart_pane_up_requested)
        pane.move_down_requested.connect(self._on_move_chart_pane_down_requested)
        pane.close_requested.connect(self._on_close_chart_pane_requested)
        pane.activated.connect(self._set_active_chart_pane)
        return pane

    def _add_chart_pane(self, set_active: bool = True) -> ChartPaneWidget:
        pane = self._create_chart_pane()
        pane.set_controls_enabled(self.plot_creator is not None)
        self.chart_panes.append(pane)
        if set_active or self.active_chart_pane is None:
            self._set_active_chart_pane(pane)
        self._rebuild_chart_grid()
        self._update_chart_reorder_buttons()
        return pane

    def _on_add_chart_requested(self):
        pane = self._add_chart_pane(set_active=True)
        self._refresh_all_chart_panes()
        QTimer.singleShot(0, self._refresh_all_chart_panes)
        if self.plot_creator is None:
            pane.show_placeholder_message(
                "Load results before plotting equations in this chart pane."
            )

    def _set_active_chart_pane(self, pane: Optional[ChartPaneWidget]):
        if pane in self.chart_panes:
            self.active_chart_pane = pane

    def _active_or_first_chart_pane(self) -> Optional[ChartPaneWidget]:
        if self.active_chart_pane in self.chart_panes:
            return self.active_chart_pane
        if self.chart_panes:
            self.active_chart_pane = self.chart_panes[0]
            return self.active_chart_pane
        return self._add_chart_pane(set_active=True)

    def _set_all_chart_controls_enabled(self, enabled: bool):
        for pane in self.chart_panes:
            pane.set_controls_enabled(enabled)
            pane.history_btn.setEnabled(enabled and bool(pane.plots))

    def _update_chart_reorder_buttons(self):
        show_reorder = self.reorder_mode_enabled
        has_multiple = len(self.chart_panes) > 1
        for index, pane in enumerate(self.chart_panes):
            pane.set_reorder_direction(False)
            pane.set_reorder_controls_visible(show_reorder)
            pane.set_reorder_controls_enabled(
                show_reorder and has_multiple and index > 0,
                show_reorder and has_multiple and index < len(self.chart_panes) - 1,
            )

    def _refresh_all_chart_panes(self):
        for pane in self.chart_panes:
            pane.refresh_plot_size()

    def _reset_chart_panes(self):
        for pane in self.chart_panes:
            try:
                pane.cleanup()
            except Exception:
                pass

        blocker = QSignalBlocker(self.reorder_mode_btn)
        self.reorder_mode_btn.setChecked(False)
        del blocker
        self.reorder_mode_enabled = False
        self.chart_panes = []
        self.active_chart_pane = None
        self._add_chart_pane(set_active=True)

    def _compute_effective_grid(self) -> tuple:
        """Return (effective_rows, effective_cols) from grid settings and pane count.

        Empty configured rows/columns are collapsed so existing panes use as much
        visible space as possible.
        """
        configured_cols = max(1, self.grid_cols)
        configured_rows = max(1, self.grid_rows)
        pane_count = max(1, len(self.chart_panes))

        # Always allow overflow rows when panes exceed configured capacity.
        effective_rows = max(1, math.ceil(pane_count / configured_cols))

        # If all panes fit in one row, collapse unused columns for better width.
        if pane_count <= configured_cols:
            effective_cols = pane_count
        else:
            effective_cols = configured_cols

        # If panes fit within configured capacity, collapse unused trailing rows.
        if pane_count <= configured_rows * configured_cols:
            effective_rows = max(1, math.ceil(pane_count / effective_cols))

        return effective_rows, effective_cols

    def _rebuild_chart_grid(self):
        """Rebuild the chart area using nested QSplitters so panes are resizable.

        Layout: a vertical QSplitter of rows; each row is a horizontal QSplitter
        of ChartPaneWidgets.  Sizes are distributed equally on build.
        """
        for pane in self.chart_panes:
            try:
                pane.setParent(None)
            except RuntimeError:
                pass

        old_container = getattr(self, "chart_grid_container", None)
        if old_container is not None:
            try:
                old_container.setParent(None)
                old_container.deleteLater()
            except RuntimeError:
                pass

        effective_rows, effective_cols = self._compute_effective_grid()

        # Minimum pixel height per row. The outer splitter's minimum height is
        # effective_rows * this value, so a scrollbar appears once the rows no
        # longer fit in the visible viewport (~2-3 rows at typical window sizes).
        _MIN_ROW_H = self.pane_row_height

        # Outer vertical splitter – one child per row.
        v_splitter = QSplitter(Qt.Vertical)
        v_splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        v_splitter.setChildrenCollapsible(False)
        v_splitter.setMinimumHeight(effective_rows * _MIN_ROW_H)

        for row in range(effective_rows):
            h_splitter = QSplitter(Qt.Horizontal)
            h_splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            h_splitter.setChildrenCollapsible(False)
            h_splitter.setMinimumHeight(_MIN_ROW_H)
            h_splitter.setMinimumWidth(effective_cols * self.pane_col_width)
            for col in range(effective_cols):
                idx = row * effective_cols + col
                if idx < len(self.chart_panes):
                    self.chart_panes[idx].setMinimumWidth(self.pane_col_width)
                    h_splitter.addWidget(self.chart_panes[idx])
                else:
                    # Empty placeholder so row has correct column count.
                    _placeholder = QWidget()
                    _placeholder.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                    _placeholder.setMinimumWidth(self.pane_col_width)
                    h_splitter.addWidget(_placeholder)
            # Equal column widths.
            h_splitter.setSizes([self.pane_col_width] * h_splitter.count())
            v_splitter.addWidget(h_splitter)

        # Equal row heights.
        v_splitter.setSizes([1000] * v_splitter.count())

        # Refresh canvas sizes whenever a splitter handle is dragged.
        v_splitter.splitterMoved.connect(
            lambda _pos, _idx: QTimer.singleShot(0, self._refresh_all_chart_panes)
        )
        for i in range(v_splitter.count()):
            child = v_splitter.widget(i)
            if isinstance(child, QSplitter):
                child.splitterMoved.connect(
                    lambda _pos, _idx: QTimer.singleShot(0, self._refresh_all_chart_panes)
                )

        self.chart_grid_container = v_splitter
        self.scroll_area.setWidget(v_splitter)
        self._update_effective_layout_label()
        QTimer.singleShot(0, self._refresh_all_chart_panes)

    def _on_pane_size_changed(self, value: int):
        """Update pane row height from the slider and rebuild the grid."""
        self.pane_row_height = value
        if hasattr(self, "pane_size_label"):
            self.pane_size_label.setText(f"{value} px")
        self._rebuild_chart_grid()

    def _on_pane_col_width_changed(self, value: int):
        """Update pane column width from the slider and rebuild the grid."""
        self.pane_col_width = value
        if hasattr(self, "pane_width_label"):
            self.pane_width_label.setText(f"{value} px")
        self._rebuild_chart_grid()

    def _refresh_chart_grid_sizing(self):
        """Refresh canvas sizing across panes (called on widget/splitter resize)."""
        self._refresh_all_chart_panes()

    def _on_chart_layout_panel_toggled(self, checked: bool):
        """Show or hide the chart layout panel."""
        if checked:
            self.chart_layout_panel_container.show()
        else:
            self.chart_layout_panel_container.hide()
        QTimer.singleShot(0, self._refresh_chart_grid_sizing)

    def _on_grid_rows_changed(self, value: int):
        if self.grid_rows == value:
            return
        self.grid_rows = value
        self._rebuild_chart_grid()
        self._update_chart_reorder_buttons()
        self._store_grid_layout()

    def _on_grid_cols_changed(self, value: int):
        if self.grid_cols == value:
            return
        self.grid_cols = value
        self._rebuild_chart_grid()
        self._update_chart_reorder_buttons()
        self._store_grid_layout()

    def _apply_grid_preset(self, rows: int, cols: int):
        self.grid_rows = rows
        self.grid_cols = cols
        blocker_r = QSignalBlocker(self.grid_rows_spinbox)
        self.grid_rows_spinbox.setValue(rows)
        del blocker_r
        blocker_c = QSignalBlocker(self.grid_cols_spinbox)
        self.grid_cols_spinbox.setValue(cols)
        del blocker_c
        self._rebuild_chart_grid()
        self._update_chart_reorder_buttons()
        self._store_grid_layout()

    def _update_effective_layout_label(self):
        if not hasattr(self, "effective_layout_label"):
            return
        effective_rows, effective_cols = self._compute_effective_grid()
        pane_count = len(self.chart_panes)
        capacity = effective_rows * effective_cols
        empty_cells = capacity - pane_count
        text = f"Effective: {effective_rows}\u00d7{effective_cols}"
        if empty_cells > 0:
            text += f" ({empty_cells} empty cell{'s' if empty_cells != 1 else ''})"
        self.effective_layout_label.setText(text)

    def _on_reorder_mode_changed(self, enabled: bool):
        if self.reorder_mode_enabled == enabled:
            return

        self.reorder_mode_enabled = enabled
        self._update_chart_reorder_buttons()

    def _reorder_chart_panes(self, pane: ChartPaneWidget, insert_index: int):
        if pane not in self.chart_panes:
            return

        remaining_panes = [existing_pane for existing_pane in self.chart_panes if existing_pane is not pane]
        insert_index = max(0, min(insert_index, len(remaining_panes)))
        new_order = list(remaining_panes)
        new_order.insert(insert_index, pane)

        if new_order == self.chart_panes:
            return

        self.chart_panes = new_order
        self.active_chart_pane = pane
        self._rebuild_chart_grid()

    def _move_chart_pane(self, pane: ChartPaneWidget, direction: int):
        if pane not in self.chart_panes or len(self.chart_panes) < 2:
            return

        current_index = self.chart_panes.index(pane)
        target_index = current_index + direction
        if target_index < 0 or target_index >= len(self.chart_panes):
            return

        self._reorder_chart_panes(pane, target_index)

    def _on_move_chart_pane_up_requested(self, pane: ChartPaneWidget):
        self._move_chart_pane(pane, -1)

    def _on_move_chart_pane_down_requested(self, pane: ChartPaneWidget):
        self._move_chart_pane(pane, 1)

    def _on_close_chart_pane_requested(self, pane: ChartPaneWidget):
        if pane not in self.chart_panes or len(self.chart_panes) <= 1:
            return
        idx = self.chart_panes.index(pane)
        self.chart_panes.remove(pane)
        if self.active_chart_pane is pane:
            replacement_idx = min(idx, len(self.chart_panes) - 1)
            self._set_active_chart_pane(self.chart_panes[replacement_idx])
        try:
            pane.cleanup()
        except Exception:
            pass
        self._rebuild_chart_grid()
        self._update_chart_reorder_buttons()
        QTimer.singleShot(0, self._refresh_all_chart_panes)

    @staticmethod
    def _default_reference_html() -> str:
        """Return placeholder HTML for the reference panel before results load."""
        return default_reference_html()

    def _toggle_reference_panel(self):
        """Show or hide the reference panel."""
        if self.ref_toggle_btn.isChecked():
            self._refresh_result_versions()
            self.ref_panel_container.show()
        else:
            self.ref_panel_container.hide()

    def _refresh_result_versions(self):
        """Refresh archive choices and keep the active version selected."""
        self.variable_selector.update_result_versions()
        self._set_version_selector(self.active_version_name)

    def _set_version_selector(self, version_name: str):
        """Update the version selector without triggering a reload."""
        if not hasattr(self, "variable_selector"):
            return

        selector = self.variable_selector.version_selector
        index = selector.findText(version_name)
        if index < 0:
            index = selector.findText("Current")

        blocker = QSignalBlocker(selector)
        selector.setCurrentIndex(index)
        del blocker

    def _resolve_snapshot_root(self, version_name: Optional[str] = None) -> Optional[Path]:
        """Return the project or archive root for the requested version."""
        if not self.project_root_path:
            return None

        if not version_name or version_name == "Current":
            return self.project_root_path

        archive_root = None
        if self.file_handler and getattr(self.file_handler, "archive_dir_path", None):
            archive_root = Path(self.file_handler.archive_dir_path)
        else:
            archive_root = self.project_root_path / "archive"

        return archive_root / version_name

    def _on_result_version_changed(self, version_name: str):
        """Reload results when the archive selector changes."""
        if self._is_loading_results or not self.project_root_path:
            return

        if version_name == self.active_version_name:
            return

        snapshot_root = self._resolve_snapshot_root(version_name)
        if snapshot_root is None or not snapshot_root.exists():
            return

        self.load_results(self.project_root_path, archive_name=version_name)

    def _update_reference_panel(self):
        """Populate the reference panel with functions, and constants."""
        from .analysis.equation_engine import EquationEngine

        functions = sorted(EquationEngine.ALLOWED_FUNCTIONS.keys())
        constants = sorted(EquationEngine.ALLOWED_CONSTANTS.keys())

        self.ref_panel.setHtml(
            build_reference_html(functions, constants, self.measurement_point_info)
        )

    def _populate_variable_list(self):
        """Populate variable checkboxes in table and reflect selected state."""
        self.variable_selector.set_variable_sources(
            self.all_variables, self.measurement_point_info
        )
        self.variable_selector.populate(self.selected_variables)

    def _sync_variable_table_check_states(self):
        """Sync row and section checkbox states from self.selected_variables."""
        self.variable_selector.set_selected_variables(self.selected_variables)

    def _get_available_vars(self) -> List[str]:
        """Collect selected variables from the checkbox table."""
        return self.variable_selector.get_checked_variables()

    def _copy_selected_variable_names(self):
        """Copy selected variable names from the selector table."""
        self.variable_selector.copy_selected_variable_names()

    def _sanitize_selected_variables(
        self,
        selected: Optional[List[str]],
    ) -> List[str]:
        """Restrict selection to valid variables and preserve configured order."""
        self.variable_selector.set_variable_sources(
            self.all_variables, self.measurement_point_info
        )
        return self.variable_selector.sanitize_selected_variables(selected)

    def _select_all_variables(self):
        """Select all variables in the table."""
        self.variable_selector.select_all()

    def _deselect_all_variables(self):
        """Deselect all variables in the table."""
        self.variable_selector.deselect_all()

    def _on_variable_item_changed(self, _changed_item):
        """Apply selection changes as the user checks/unchecks variables."""
        self._apply_variable_selection(self._get_available_vars())

    def _apply_variable_selection(
        self,
        selected: List[str],
    ):
        """Apply selected variables to current analyzer and persist metadata."""
        sanitized = self._sanitize_selected_variables(selected)

        self.selected_variables = sanitized
        self._sync_variable_table_check_states()
        try:
            if self.plot_creator and hasattr(
                self.plot_creator, "set_selected_variables"
            ):
                self.plot_creator.set_selected_variables(self.selected_variables)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Setting Selection Failed",
                f"Failed to apply variable selection:\n{str(e)}",
            )
            return

        self._store_selected_variables()
        self._update_reference_panel()

    def _store_selected_variables(self):
        """Store selected variables in project metadata for future loads."""
        if not self.current_project_path:
            return

        metadata_path = self.current_project_path / "project_metadata.json"
        if not metadata_path.exists():
            return

        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            metadata[self.selection_metadata_key] = list(self.selected_variables)

            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Saving Variable Selection Failed", str(e))

    def _read_persisted_selection(self, metadata: Dict) -> Optional[List[str]]:
        """Read chart selection from metadata with backward-compatible fallback."""
        persisted = metadata.get(self.selection_metadata_key)
        if isinstance(persisted, list):
            return persisted

        legacy = metadata.get(self.legacy_selection_metadata_key)
        if isinstance(legacy, list):
            return legacy
        return None

    def _store_grid_layout(self):
        """Persist current grid rows/cols to project metadata."""
        if not self.current_project_path:
            return
        metadata_path = self.current_project_path / "project_metadata.json"
        if not metadata_path.exists():
            return
        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
            metadata[self.chart_grid_rows_key] = self.grid_rows
            metadata[self.chart_grid_cols_key] = self.grid_cols
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
        except Exception:
            pass

    def _read_persisted_grid_layout(self, metadata: Dict):
        """Restore grid rows/cols from metadata and update spinboxes."""
        rows = metadata.get(self.chart_grid_rows_key)
        cols = metadata.get(self.chart_grid_cols_key)
        changed = False
        if isinstance(rows, int) and rows >= 1 and rows != self.grid_rows:
            self.grid_rows = rows
            changed = True
        if isinstance(cols, int) and cols >= 1 and cols != self.grid_cols:
            self.grid_cols = cols
            changed = True
        if hasattr(self, "grid_rows_spinbox"):
            blocker_r = QSignalBlocker(self.grid_rows_spinbox)
            self.grid_rows_spinbox.setValue(self.grid_rows)
            del blocker_r
        if hasattr(self, "grid_cols_spinbox"):
            blocker_c = QSignalBlocker(self.grid_cols_spinbox)
            self.grid_cols_spinbox.setValue(self.grid_cols)
            del blocker_c
        if changed:
            self._rebuild_chart_grid()
            self._update_chart_reorder_buttons()

    @staticmethod
    def _build_results_identity(snapshot_root: Path, version_name: str) -> str:
        try:
            resolved_root = snapshot_root.resolve()
        except Exception:
            resolved_root = snapshot_root
        return f"{resolved_root}|{version_name}"

    def _get_unavailable_template_messages(self, templates) -> Dict[int, str]:
        """Return row-indexed message for each template blocked by selection."""
        analyzer = getattr(self.plot_creator, "analyzer", None)
        if not analyzer:
            return {}

        unavailable = {}
        for idx, template in enumerate(templates):
            valid, reason = analyzer.validate_expression(template.expression)
            if not valid:
                unavailable[idx] = f"Template is unavailable: {reason}"
        return unavailable

    def load_results(self, project_path: Path, archive_name: Optional[str] = None):
        """
        Load and display results from a project directory.

        Reads simulation_type from project_metadata.json inside project_path.

        Args:
            project_path: Path to the project root containing project_metadata.json
                          and archive snapshots.
            archive_name: Optional archive snapshot name to load instead of Current.
        """
        self._is_loading_results = True
        try:
            self.project_root_path = Path(project_path)

            selected_version = archive_name or "Current"
            snapshot_root = self._resolve_snapshot_root(selected_version)
            if snapshot_root is None:
                raise FileNotFoundError("No project path available for results loading.")

            requested_identity = self._build_results_identity(
                snapshot_root, selected_version
            )
            if (
                self._loaded_results_identity == requested_identity
                and self.plot_creator is not None
                and bool(self.chart_panes)
            ):
                if (
                    self.active_results_path is not None
                    and self.active_results_path.parent == snapshot_root
                ):
                    preserved_results_path = self.active_results_path
                else:
                    fast_path_metadata = ResultsLoader.read_metadata(snapshot_root) or {}
                    preserved_results_path = snapshot_root / fast_path_metadata.get(
                        "results_path", "Results"
                    )

                self.current_project_path = snapshot_root
                self.active_version_name = selected_version
                self.active_results_path = preserved_results_path
                self._refresh_result_versions()
                self._refresh_all_chart_panes()
                return

            self._clear_old_plots()
            self._reset_chart_panes()
            self._loaded_results_identity = None

            self.current_project_path = snapshot_root
            self.active_version_name = selected_version

            metadata = ResultsLoader.read_metadata(snapshot_root)
            if not metadata or "simulation_type" not in metadata:
                QMessageBox.critical(
                    self,
                    "Error Loading Results",
                    f"No project_metadata.json with simulation_type found in:\n{snapshot_root}",
                )
                return

            simulation_type = metadata["simulation_type"].strip()
            polarization_mode = metadata.get("polarization_mode", "TE").strip()
            dimension = metadata.get("dimension", "2D").strip()

            self._read_persisted_grid_layout(metadata)

            from .analysis.field_loader import FieldLoader

            self.simulation_type = simulation_type
            self.polarization_mode = polarization_mode
            self.dimension = dimension
            self.all_variables = FieldLoader.get_available_variables(
                simulation_type,
                polarization_mode,
                dimension,
            )

            # Discover measurement points
            results_dir = snapshot_root / metadata.get("results_path", "Results")
            self.active_results_path = results_dir
            loader = FieldLoader(results_dir)
            self.measurement_point_info = loader.discover_measurement_points()

            persisted_selection = self._read_persisted_selection(metadata)
            self.selected_variables = self._sanitize_selected_variables(
                persisted_selection if isinstance(persisted_selection, list) else None
            )
            self._populate_variable_list()

            # Load results using loader
            self.plot_creator = ResultsLoader.load_results(
                snapshot_root,
                simulation_type,
                parent=self,
                results_dir=results_dir,
                selected_variables=self.selected_variables,
            )

            if not self.plot_creator:
                return

            # Create plots
            self.plots = self.plot_creator.create_plots()

            # Copy per-plot domain info from strategy if available
            self.plot_domains = getattr(self.plot_creator, "plot_domains", [])

            # Ensure metadata carries default/all-selected state for next load.
            self._store_selected_variables()

            self.export_btn.setEnabled(bool(self.plots))
            self._set_all_chart_controls_enabled(True)
            self._refresh_result_versions()
            self._update_reference_panel()

            # Display first plot
            if self.plots:
                first_pane = self._active_or_first_chart_pane()
                if first_pane is not None:
                    title, figure = self.plots[0]
                    first_pane.clear_history()
                    first_pane.add_plot(title, figure, self.plot_domains[0] if self.plot_domains else "time")
                    self.current_plot_index = first_pane.current_plot_index

                # Set default domain based on simulation type
                # FDTD simulations produce time-domain data; S-Parameters
                # and Scattering Loss are frequency-domain analyses.
                freq_types = {"s-parameters", "scattering loss"}
                if simulation_type.lower() in freq_types:
                    first_pane.set_domain("frequency")
                else:
                    first_pane.set_domain("time")
                first_pane.history_btn.setEnabled(True)
            else:
                if not self.selected_variables:
                    self._show_placeholder_message(
                        "Results are loaded, but no variables are selected.\n"
                        "Use the variable selector to choose one or more variables."
                    )
                else:
                    self._show_placeholder_message(
                        "Results are loaded, but no plots were generated.\n"
                        "Try selecting different variables or check the loaded results files."
                    )

            self._loaded_results_identity = requested_identity

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Loading Results",
                f"Failed to load results:\n\n{str(e)}",
            )
            print(traceback.format_exc())
        finally:
            self._is_loading_results = False

    def _display_plot(self, index: int):
        """Display a stored plot in the active chart pane."""
        pane = self._active_or_first_chart_pane()
        if pane is None or index < 0 or index >= len(pane.plots):
            return

        pane.show_history_plot(index)
        self.current_plot_index = pane.current_plot_index

    def _on_plot_selected(self, index: int, pane: Optional[ChartPaneWidget] = None):
        """Handle plot selection by index."""
        if index >= 0:
            self.current_plot_index = index
            if pane is not None:
                self._set_active_chart_pane(pane)
            self._display_plot(index)

    def _clear_old_plots(self):
        """Close old matplotlib figures and clear plot history."""
        if self.plots:
            for title, figure in self.plots:
                try:
                    plt.close(figure)
                except Exception:
                    pass
            self.plots.clear()
            self.plot_domains.clear()
        for pane in self.chart_panes:
            pane.clear_history()
        self.current_plot_index = -1

    def _export_current_plot(self):
        """Export the currently displayed plot to file"""
        if not self.plot_creator:
            return

        pane = self._active_or_first_chart_pane()
        if pane is None or pane.current_figure is None:
            return

        figure = pane.current_figure
        title = pane.current_title or "chart"

        # Create safe filename from title
        filename = title.replace(" ", "_").replace("/", "_") + ".png"

        try:
            self.plot_creator.export(figure, filename)
            QMessageBox.information(
                self,
                "Export Successful",
                f"Plot exported to:\n{self.plot_creator.default_export_path / filename}",
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Export Failed", f"Failed to export plot:\n{str(e)}"
            )

    def cleanup_canvas(self):
        """Cleanup current canvas and close any displayed figures."""
        self._clear_old_plots()
        self._reset_chart_panes()
        self._loaded_results_identity = None

    def invalidate_loaded_results_cache(self):
        """Mark cached load identity stale so the next load_results call reloads data."""
        self._loaded_results_identity = None

    def hideEvent(self, event):
        super().hideEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._refresh_chart_grid_sizing)

    def clear(self):
        """Clear all displayed plots"""
        # Close matplotlib figures
        self._clear_old_plots()
        self._reset_chart_panes()

        # Reset grid layout to 1×1 defaults
        self.grid_rows = 1
        self.grid_cols = 1
        if hasattr(self, "grid_rows_spinbox"):
            blocker_r = QSignalBlocker(self.grid_rows_spinbox)
            self.grid_rows_spinbox.setValue(1)
            del blocker_r
        if hasattr(self, "grid_cols_spinbox"):
            blocker_c = QSignalBlocker(self.grid_cols_spinbox)
            self.grid_cols_spinbox.setValue(1)
            del blocker_c

        # Reset controls
        self.current_plot_index = -1
        self.project_root_path = None
        self.current_project_path = None
        self.active_results_path = None
        self.active_version_name = "Current"
        self._loaded_results_identity = None
        self.export_btn.setEnabled(False)
        self.all_variables = []
        self.selected_variables = []
        self.measurement_point_info = []
        self._populate_variable_list()
        self.ref_panel.setHtml(self._default_reference_html())
        self.variable_selector.version_selector.clear()
        self.variable_selector.version_selector.addItem("Current")
        self.variable_selector.version_selector.setEnabled(False)

        self._show_placeholder_message(
            "No results loaded.\nRun a simulation to see results here."
        )
