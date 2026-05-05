"""Tests for archive-aware results loading."""

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

from gui.visualizer.results_loader import ResultsLoader
from gui.visualizer.wave_impedance_strategy import DynamicAnalysisStrategy


def _write_project_metadata(project_root: Path, simulation_type: str = "Wave Impedance"):
    project_root.mkdir(parents=True, exist_ok=True)
    metadata = {
        "simulation_type": simulation_type,
        "polarization_mode": "TE",
        "dimension": "2D",
        "results_path": "Results",
    }
    (project_root / "project_metadata.json").write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )
    return metadata


def test_read_metadata_from_archive_snapshot(tmp_path):
    archive_root = tmp_path / "project" / "archive" / "archive_1"
    expected = _write_project_metadata(archive_root)

    metadata = ResultsLoader.read_metadata(archive_root)

    assert metadata == expected


def test_create_strategy_uses_explicit_results_dir(tmp_path):
    snapshot_root = tmp_path / "project" / "archive" / "archive_1"
    results_dir = snapshot_root / "Results"
    results_dir.mkdir(parents=True, exist_ok=True)

    strategy = ResultsLoader.create_strategy(
        snapshot_root,
        "Wave Impedance",
        results_dir=results_dir,
        selected_variables=["Ex"],
    )

    assert isinstance(strategy, DynamicAnalysisStrategy)
    assert strategy.project_path == snapshot_root
    assert strategy.results_path == results_dir
    assert strategy.default_export_path == results_dir


def test_create_strategy_preserves_results_dir_for_placeholder_strategies(tmp_path):
    snapshot_root = tmp_path / "project" / "archive" / "archive_1"
    results_dir = snapshot_root / "Results"
    results_dir.mkdir(parents=True, exist_ok=True)

    strategy = ResultsLoader.create_strategy(
        snapshot_root,
        "S-Parameters",
        results_dir=results_dir,
    )

    assert strategy is not None
    assert isinstance(strategy, DynamicAnalysisStrategy)
    assert strategy.project_path == snapshot_root
    assert strategy.results_path == results_dir
    assert strategy.default_export_path == results_dir


@pytest.mark.parametrize(
    "simulation_type",
    ["Wave Impedance", "S-Parameters", "Scattering Loss", "Custom Experiment"],
)
def test_create_strategy_all_types_use_dynamic_analysis(tmp_path, simulation_type):
    snapshot_root = tmp_path / "project" / "archive" / "archive_1"
    results_dir = snapshot_root / "Results"
    results_dir.mkdir(parents=True, exist_ok=True)

    strategy = ResultsLoader.create_strategy(
        snapshot_root,
        simulation_type,
        results_dir=results_dir,
    )

    assert isinstance(strategy, DynamicAnalysisStrategy)
    assert strategy.results_path == results_dir