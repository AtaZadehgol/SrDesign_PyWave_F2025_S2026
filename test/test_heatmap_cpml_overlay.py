"""Tests for CPML overlay rectangle derivation in the heatmap widget."""

import json
import os
import sys
from pathlib import Path

import pytest

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


def _write_simulation_config(project_root: Path, cfg: dict):
    config_path = project_root / "simulation_config.json"
    config_path.write_text(json.dumps(cfg), encoding="utf-8")


def test_load_cpml_rectangles_from_simulation_config(tmp_path):
    domain_bounds = (0.0, 1.0e-6, 0.0, 5.0e-7)
    _write_simulation_config(
        tmp_path,
        {
            "geometry": {
                "grid_spacing": {
                    "delta_x": 5.0e-8,
                    "delta_y": 5.0e-8,
                }
            },
            "advanced_parameters": {
                "num_cpml": 2,
            },
        },
    )

    rectangles = HeatmapResultsWidget._load_cpml_rectangles(tmp_path, domain_bounds)

    assert len(rectangles) == 4
    names = {rect["name"] for rect in rectangles}
    assert names == {"CPML Left", "CPML Right", "CPML Bottom", "CPML Top"}

    left = next(rect for rect in rectangles if rect["name"] == "CPML Left")
    assert left["dimensions"]["width"] == pytest.approx(1.0e-7)
    assert left["dimensions"]["height"] == pytest.approx(5.0e-7)


def test_load_cpml_rectangles_missing_cpml_settings(tmp_path):
    domain_bounds = (0.0, 1.0e-6, 0.0, 5.0e-7)
    _write_simulation_config(
        tmp_path,
        {
            "geometry": {
                "grid_spacing": {
                    "delta_x": 5.0e-8,
                    "delta_y": 5.0e-8,
                }
            },
            "advanced_parameters": {},
        },
    )

    rectangles = HeatmapResultsWidget._load_cpml_rectangles(tmp_path, domain_bounds)

    assert rectangles == []


def test_load_cpml_rectangles_rejects_oversized_cpml(tmp_path):
    domain_bounds = (0.0, 1.0e-6, 0.0, 5.0e-7)
    _write_simulation_config(
        tmp_path,
        {
            "geometry": {
                "grid_spacing": {
                    "delta_x": 1.0e-7,
                    "delta_y": 1.0e-7,
                }
            },
            "advanced_parameters": {
                "num_cpml": 5,
            },
        },
    )

    rectangles = HeatmapResultsWidget._load_cpml_rectangles(tmp_path, domain_bounds)

    assert rectangles == []
