"""Tests for multi-chart pane behavior in ResultsWidget."""

import os
import sys

import pytest

pytest.importorskip("PyQt5")

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "PyQt5-test",
        "input-screen",
    ),
)

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QHideEvent
from matplotlib.figure import Figure

from gui.visualizer.chart_pane import ChartPaneWidget
from gui.visualizer.results_widget import ResultsWidget


class _StubAnalyzer:
    def plot_equation(self, expression, domain, title=None):
        return Figure()


class _StubPlotCreator:
    def __init__(self):
        self.analyzer = _StubAnalyzer()


@pytest.fixture(scope="module")
def app():
    existing = QApplication.instance()
    if existing is not None:
        return existing
    return QApplication([])


def test_add_equation_creates_new_chart_pane(app):
    widget = ResultsWidget()
    try:
        assert len(widget.chart_panes) == 1

        widget._on_add_chart_requested()

        assert len(widget.chart_panes) == 2
        assert widget.active_chart_pane is widget.chart_panes[-1]
    finally:
        widget.cleanup_canvas()
        widget.deleteLater()


def test_chart_controls_toggle_for_all_panes(app):
    widget = ResultsWidget()
    try:
        widget._on_add_chart_requested()
        widget._set_all_chart_controls_enabled(True)

        for pane in widget.chart_panes:
            assert pane.equation_input.isEnabled()
            assert pane.domain_selector.isEnabled()
            assert pane.templates_btn.isEnabled()
            assert pane.plot_btn.isEnabled()

        widget._set_all_chart_controls_enabled(False)

        for pane in widget.chart_panes:
            assert not pane.equation_input.isEnabled()
            assert not pane.domain_selector.isEnabled()
            assert not pane.templates_btn.isEnabled()
            assert not pane.plot_btn.isEnabled()
    finally:
        widget.cleanup_canvas()
        widget.deleteLater()


def test_history_button_is_per_pane(app):
    widget = ResultsWidget()
    try:
        first_pane = widget.chart_panes[0]
        first_pane.set_controls_enabled(True)
        first_pane.add_plot("Pane 1 Plot", Figure(), "time")

        widget._on_add_chart_requested()
        second_pane = widget.chart_panes[-1]

        assert first_pane.history_btn.isEnabled()
        assert second_pane.history_btn.isEnabled() is False
        assert second_pane.plots == []
    finally:
        widget.cleanup_canvas()
        widget.deleteLater()


def test_layout_mode_toggle_changes_splitter_orientation(app):
    widget = ResultsWidget()
    try:
        assert widget.chart_splitter.orientation() == Qt.Horizontal

        widget.layout_mode_btn.setChecked(True)

        assert widget.layout_mode_stacked is True
        assert widget.chart_splitter.orientation() == Qt.Vertical

        widget.layout_mode_btn.setChecked(False)

        assert widget.layout_mode_stacked is False
        assert widget.chart_splitter.orientation() == Qt.Horizontal
    finally:
        widget.cleanup_canvas()
        widget.deleteLater()


def test_reset_chart_panes_restores_default_layout(app):
    widget = ResultsWidget()
    try:
        widget.layout_mode_btn.setChecked(True)
        assert widget.chart_splitter.orientation() == Qt.Vertical

        widget._reset_chart_panes()

        assert widget.layout_mode_stacked is False
        assert widget.layout_mode_btn.isChecked() is False
        assert widget.chart_splitter.orientation() == Qt.Horizontal
        assert len(widget.chart_panes) == 1
    finally:
        widget.cleanup_canvas()
        widget.deleteLater()


def test_stacked_layout_reorders_panes(app):
    widget = ResultsWidget()
    try:
        widget.layout_mode_btn.setChecked(True)
        widget.reorder_mode_btn.setChecked(True)
        first_pane = widget.chart_panes[0]
        second_pane = widget._add_chart_pane(set_active=False)

        assert first_pane.move_up_btn.isHidden() is False
        assert first_pane.move_down_btn.isHidden() is False
        assert second_pane.move_up_btn.isHidden() is False
        assert second_pane.move_down_btn.isHidden() is False

        widget._move_chart_pane(second_pane, -1)

        assert widget.chart_panes[0] is second_pane
        assert widget.chart_panes[1] is first_pane
        assert widget.chart_splitter.orientation() == Qt.Vertical
        assert second_pane.move_up_btn.isEnabled() is False
        assert second_pane.move_down_btn.isEnabled()

        widget.reorder_mode_btn.setChecked(False)

        assert first_pane.move_up_btn.isHidden()
        assert first_pane.move_down_btn.isHidden()
    finally:
        widget.cleanup_canvas()
        widget.deleteLater()


def test_reorder_toggle_shows_single_pane_arrows_disabled(app):
    widget = ResultsWidget()
    try:
        pane = widget.chart_panes[0]
        widget.reorder_mode_btn.setChecked(True)

        assert pane.move_up_btn.isHidden() is False
        assert pane.move_down_btn.isHidden() is False
        assert pane.move_up_btn.isEnabled() is False
        assert pane.move_down_btn.isEnabled() is False
        assert pane.move_up_btn.text() == "Left"
        assert pane.move_down_btn.text() == "Right"

        widget.layout_mode_btn.setChecked(True)
        assert pane.move_up_btn.text() == "Up"
        assert pane.move_down_btn.text() == "Down"

        widget.reorder_mode_btn.setChecked(False)

        assert pane.move_up_btn.isHidden()
        assert pane.move_down_btn.isHidden()
    finally:
        widget.cleanup_canvas()
        widget.deleteLater()


def test_chart_hide_event_preserves_plots(app):
    widget = ResultsWidget()
    try:
        pane = widget.chart_panes[0]
        pane.set_controls_enabled(True)

        figure = Figure()
        pane.add_plot("Persisted Plot", figure, "time")

        widget.hideEvent(QHideEvent())

        assert len(pane.plots) == 1
        assert pane.current_figure is figure
        assert pane.current_title == "Persisted Plot"
    finally:
        widget.cleanup_canvas()
        widget.deleteLater()


def test_chart_cache_invalidation_preserves_current_plot_state(app):
    widget = ResultsWidget()
    try:
        pane = widget.chart_panes[0]
        pane.set_controls_enabled(True)

        figure = Figure()
        pane.add_plot("Persisted Plot", figure, "time")
        widget._loaded_results_identity = "project|Current"

        widget.invalidate_loaded_results_cache()

        assert widget._loaded_results_identity is None
        assert len(pane.plots) == 1
        assert pane.current_figure is figure
    finally:
        widget.cleanup_canvas()
        widget.deleteLater()


def test_chart_pane_history_cap_eviction(app):
    pane = ChartPaneWidget(max_plot_history=2)
    try:
        pane.set_controls_enabled(True)
        pane.add_plot("plot-1", Figure(), "time")
        pane.add_plot("plot-2", Figure(), "time")
        pane.add_plot("plot-3", Figure(), "time")

        assert [title for title, _figure in pane.plots] == ["plot-2", "plot-3"]
        assert pane.current_plot_index == 1
        assert pane.history_btn.isEnabled()
    finally:
        pane.clear_history()
        pane.deleteLater()


def test_equation_plot_does_not_append_global_loaded_results_lists(app):
    widget = ResultsWidget()
    try:
        pane = widget.chart_panes[0]
        pane.set_controls_enabled(True)

        widget.plot_creator = _StubPlotCreator()
        loaded_figure = Figure()
        widget.plots = [("Loaded Plot", loaded_figure)]
        widget.plot_domains = ["time"]

        pane.equation_input.setText("Ex")
        pane.set_domain("time")

        widget._on_plot_equation(pane)

        # Equation plotting should only affect pane-local history.
        assert len(widget.plots) == 1
        assert widget.plots[0][0] == "Loaded Plot"
        assert len(widget.plot_domains) == 1
        assert widget.plot_domains[0] == "time"
        assert len(pane.plots) == 1
        assert pane.plots[0][0] == "Ex (time)"
    finally:
        widget.cleanup_canvas()
        widget.deleteLater()


def test_close_pane_removes_targeted_pane(app):
    widget = ResultsWidget()
    try:
        widget._on_add_chart_requested()
        widget._on_add_chart_requested()
        assert len(widget.chart_panes) == 3
        target = widget.chart_panes[1]

        widget._on_close_chart_pane_requested(target)

        assert len(widget.chart_panes) == 2
        assert target not in widget.chart_panes
    finally:
        widget.cleanup_canvas()
        widget.deleteLater()


def test_close_active_pane_reassigns_active_chart_pane(app):
    widget = ResultsWidget()
    try:
        widget._on_add_chart_requested()
        active_pane = widget.chart_panes[-1]
        widget._set_active_chart_pane(active_pane)
        assert widget.active_chart_pane is active_pane

        widget._on_close_chart_pane_requested(active_pane)

        assert widget.active_chart_pane is not active_pane
        assert widget.active_chart_pane in widget.chart_panes
    finally:
        widget.cleanup_canvas()
        widget.deleteLater()


def test_close_single_remaining_pane_is_blocked(app):
    widget = ResultsWidget()
    try:
        assert len(widget.chart_panes) == 1
        only_pane = widget.chart_panes[0]

        widget._on_close_chart_pane_requested(only_pane)

        assert len(widget.chart_panes) == 1
        assert widget.chart_panes[0] is only_pane
    finally:
        widget.cleanup_canvas()
        widget.deleteLater()


def test_close_btn_click_removes_pane(app):
    widget = ResultsWidget()
    try:
        widget._on_add_chart_requested()
        assert len(widget.chart_panes) == 2
        target = widget.chart_panes[1]

        target.close_btn.click()

        assert len(widget.chart_panes) == 1
        assert target not in widget.chart_panes
    finally:
        widget.cleanup_canvas()
        widget.deleteLater()
