"""Regression tests for heatmap view persistence across hide/show navigation."""

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

from PyQt5.QtGui import QHideEvent
from PyQt5.QtWidgets import QApplication
from matplotlib.figure import Figure

from gui.visualizer.heatmap_results_widget import HeatmapResultsWidget


@pytest.fixture(scope="module")
def app():
    existing = QApplication.instance()
    if existing is not None:
        return existing
    return QApplication([])


def test_heatmap_hide_event_preserves_current_figure(app):
    widget = HeatmapResultsWidget()
    try:
        figure = Figure()
        widget.current_figure = figure
        widget.frame_index = 100
        widget.frame_slider.setEnabled(True)
        widget.frame_slider.setMaximum(200)
        widget.frame_slider.setValue(100)

        widget.hideEvent(QHideEvent())

        assert widget.current_figure is figure
        assert widget.frame_index == 100
        assert widget.frame_slider.value() == 100
    finally:
        widget.cleanup_canvas()
        widget.deleteLater()


def test_heatmap_cache_invalidation_preserves_current_figure(app):
    widget = HeatmapResultsWidget()
    try:
        figure = Figure()
        widget.current_figure = figure
        widget._loaded_results_identity = "project|Current"

        widget.invalidate_loaded_results_cache()

        assert widget._loaded_results_identity is None
        assert widget.current_figure is figure
    finally:
        widget.cleanup_canvas()
        widget.deleteLater()


def test_heatmap_resize_can_shrink_canvas_container(app):
    widget = HeatmapResultsWidget()
    try:
        widget.resize(1000, 700)
        widget.show()
        app.processEvents()

        figure = Figure(figsize=(9, 6), dpi=100)
        widget.current_figure = figure
        assert widget._display_figure(figure)
        app.processEvents()

        widget.resize(1100, 700)
        app.processEvents()
        widget._resize_canvas_to_viewport()
        app.processEvents()
        grown_width = widget.canvas_container.width()

        widget.resize(650, 700)
        app.processEvents()
        widget._resize_canvas_to_viewport()
        app.processEvents()
        shrunk_width = widget.canvas_container.width()

        assert shrunk_width < grown_width
    finally:
        widget.cleanup_canvas()
        widget.close()
        widget.deleteLater()
