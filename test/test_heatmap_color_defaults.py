"""Tests for default heatmap colormap and normalization behavior."""

import os
import sys

import numpy as np
import pytest
from matplotlib import colors as mcolors

pytest.importorskip("PyQt5")

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "PyQt5-test",
        "input-screen",
    ),
)

from gui.visualizer.heatmap_results_widget import HeatmapResultsWidget


def test_build_default_color_norm_uses_symlog_for_signed_data():
    merged_values = np.array([-10.0, -1.0, -0.1, 0.0, 0.05, 1.0, 15.0])

    norm = HeatmapResultsWidget._build_default_color_norm(merged_values)

    assert isinstance(norm, mcolors.SymLogNorm)
    assert norm.vmin == pytest.approx(np.percentile(merged_values, 1.0))
    assert norm.vmax == pytest.approx(np.percentile(merged_values, 99.0))
    assert norm.linthresh > 0.0


def test_build_default_color_norm_falls_back_for_constant_data():
    merged_values = np.array([3.0, 3.0, 3.0])

    norm = HeatmapResultsWidget._build_default_color_norm(merged_values)

    assert isinstance(norm, mcolors.Normalize)
    assert not isinstance(norm, mcolors.SymLogNorm)
    # Bounds should be derived from data magnitude, not collapsed to 0..1
    assert norm.vmin < 3.0
    assert norm.vmax > 3.0


def test_default_colormap_is_bwr():
    cmap = HeatmapResultsWidget._DEFAULT_HEATMAP_COLORMAP

    assert cmap == "bwr"


def test_build_default_color_norm_ignores_extreme_outliers():
    merged_values = np.concatenate(
        [np.linspace(-2.0, 2.0, 1000), np.array([250.0])]
    )

    norm = HeatmapResultsWidget._build_default_color_norm(merged_values)

    assert norm.vmax == pytest.approx(np.percentile(merged_values, 99.0))
    assert norm.vmax < 250.0
