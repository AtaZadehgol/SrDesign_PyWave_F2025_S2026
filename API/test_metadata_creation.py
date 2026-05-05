"""
Pytest tests for project directory structure and metadata file creation
Run with: pytest test_metadata_creation.py -v
"""

import json
import os
import sys
import pytest
import shutil
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from metadata_writer import write_metadata


class MockConfig:
    """Mock InitialValues object for testing"""

    def __init__(self):
        # Time parameters
        self.delta_t = 1e-17
        self.nt = 1000
        self.sim_time = 1e-14

        # Spatial parameters
        self.delta_x = 1e-9
        self.nx = 100
        self.ny = 100
        self.nx_swg = 50
        self.ny_swg = 25
        self.bx = 25
        self.by = 37

        # Frequency
        self.f0 = 200e12

        # Material
        self.eps_rel_bg = 1.5
        self.eps_rel_fg = 3.5

        # Geometry
        self.sgl_wg_length = 5e-7
        self.sgl_wg_width = 1e-7

        # Source
        self.source_type = 2
        self.source_amp = 1.0
        self.sx = 20
        self.sy = 50

        # Output directory (will be project/Results)
        self.output_dir = "./test_project/Results"


@pytest.fixture
def mock_config():
    """Fixture providing a mock configuration"""
    return MockConfig()


@pytest.fixture
def mock_gui_data():
    """Fixture providing mock GUI JSON data"""
    return {
        "simulation_type": "Wave Impedance",
        "polarization_mode": "TE",
        "dimension": "2D",
        "geometry": {
            "rectangles": [
                {
                    "position": {"x": 48.0, "y": 64.0},
                    "dimensions": {"width": 37.6, "height": 23.8},
                    "name": "R_1",
                    "material": {
                        "name": "Silicon",
                        "permittivity": 3.5,
                        "permeability": 1.0,
                        "conductivity": 0.0,
                    },
                }
            ],
            "grid_spacing": {"delta_x": 10, "delta_y": 10, "units": "nanometers"},
        },
        "sources": [{"x": 45.0, "y": 79.2}, {"x": 86.4, "y": 80.0}],
        "measurement_points": [{"x": 71.6, "y": 78.2}, {"x": 57.8, "y": 69.4}],
    }


@pytest.fixture
def test_project_dir(tmp_path):
    """Fixture providing a temporary project directory"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_dir = tmp_path / f"test_project_{timestamp}"
    yield project_dir
    # Cleanup after test
    if project_dir.exists():
        shutil.rmtree(project_dir, ignore_errors=True)


def test_metadata_file_creation(mock_config, mock_gui_data, test_project_dir):
    """Test that metadata file is created successfully"""
    metadata_path = write_metadata(
        config=mock_config,
        simulation_type="Wave Impedance",
        polarization_mode="TE",
        dimension="2D",
        json_data=mock_gui_data,
        project_dir=test_project_dir,
    )

    assert metadata_path is not None, "Metadata file creation failed"
    assert Path(metadata_path).exists(), "Metadata file does not exist"
    assert Path(metadata_path).name == "project_metadata.json", "Incorrect filename"


def test_project_directory_structure(mock_config, mock_gui_data, test_project_dir):
    """Test that project directory structure is correct"""
    write_metadata(
        config=mock_config,
        simulation_type="Wave Impedance",
        polarization_mode="TE",
        dimension="2D",
        json_data=mock_gui_data,
        project_dir=test_project_dir,
    )

    assert test_project_dir.exists(), "Project directory not created"
    assert (
        test_project_dir / "project_metadata.json"
    ).exists(), "Metadata file missing"


def test_metadata_required_fields(mock_config, mock_gui_data, test_project_dir):
    """Test that all required fields are present in metadata"""
    write_metadata(
        config=mock_config,
        simulation_type="Wave Impedance",
        polarization_mode="TE",
        dimension="2D",
        json_data=mock_gui_data,
        project_dir=test_project_dir,
    )

    with open(test_project_dir / "project_metadata.json", "r") as f:
        metadata = json.load(f)

    required_fields = [
        "project_name",
        "simulation_type",
        "polarization_mode",
        "dimension",
        "results_path",
        "timestamp",
        "geometry",
        "sources",
        "measurement_points",
        "configuration",
    ]

    for field in required_fields:
        assert field in metadata, f"Required field '{field}' missing from metadata"


def test_metadata_configuration_structure(mock_config, mock_gui_data, test_project_dir):
    """Test that configuration section has correct structure"""
    write_metadata(
        config=mock_config,
        simulation_type="Wave Impedance",
        polarization_mode="TE",
        dimension="2D",
        json_data=mock_gui_data,
        project_dir=test_project_dir,
    )

    with open(test_project_dir / "project_metadata.json", "r") as f:
        metadata = json.load(f)

    assert "configuration" in metadata
    config_sections = [
        "time_parameters",
        "spatial_parameters",
        "frequency",
        "material",
        "geometry",
        "source",
    ]

    for section in config_sections:
        assert (
            section in metadata["configuration"]
        ), f"Configuration section '{section}' missing"


def test_metadata_values_correctness(mock_config, mock_gui_data, test_project_dir):
    """Test that metadata contains correct values"""
    write_metadata(
        config=mock_config,
        simulation_type="Wave Impedance",
        polarization_mode="TE",
        dimension="2D",
        json_data=mock_gui_data,
        project_dir=test_project_dir,
    )

    with open(test_project_dir / "project_metadata.json", "r") as f:
        metadata = json.load(f)

    # Test top-level values
    assert metadata["simulation_type"] == "Wave Impedance"
    assert metadata["polarization_mode"] == "TE"
    assert metadata["dimension"] == "2D"
    assert metadata["results_path"] == "./Results"

    # Test configuration values
    config = metadata["configuration"]
    assert config["time_parameters"]["delta_t"] == 1e-17
    assert config["time_parameters"]["nt"] == 1000
    assert config["spatial_parameters"]["nx"] == 100
    assert config["spatial_parameters"]["ny"] == 100
    assert config["frequency"]["f0"] == 200e12
    assert config["material"]["eps_rel_bg"] == 1.5
    assert config["material"]["eps_rel_fg"] == 3.5


def test_metadata_gui_data_preservation(mock_config, mock_gui_data, test_project_dir):
    """Test that GUI geometry, sources, and measurement points are preserved"""
    write_metadata(
        config=mock_config,
        simulation_type="Wave Impedance",
        polarization_mode="TE",
        dimension="2D",
        json_data=mock_gui_data,
        project_dir=test_project_dir,
    )

    with open(test_project_dir / "project_metadata.json", "r") as f:
        metadata = json.load(f)

    # Test geometry preservation
    assert "geometry" in metadata
    assert "rectangles" in metadata["geometry"]
    assert len(metadata["geometry"]["rectangles"]) == 1
    assert metadata["geometry"]["rectangles"][0]["name"] == "R_1"

    # Test sources preservation
    assert "sources" in metadata
    assert len(metadata["sources"]) == 2
    assert metadata["sources"][0]["x"] == 45.0

    # Test measurement points preservation
    assert "measurement_points" in metadata
    assert len(metadata["measurement_points"]) == 2
    assert metadata["measurement_points"][0]["x"] == 71.6


def test_read_metadata_function(mock_config, mock_gui_data, test_project_dir):
    """Test that read_metadata function works correctly"""
    write_metadata(
        config=mock_config,
        simulation_type="Wave Impedance",
        polarization_mode="TE",
        dimension="2D",
        json_data=mock_gui_data,
        project_dir=test_project_dir,
    )

    with open(test_project_dir / "project_metadata.json", "r") as f:
        metadata = json.load(f)

    assert metadata is not None, "read_metadata returned None"
    assert metadata["simulation_type"] == "Wave Impedance"
    assert "configuration" in metadata


def test_metadata_with_none_project_dir(mock_config, mock_gui_data):
    """Test metadata creation when project_dir is None (uses output_dir parent)"""
    # Set up a specific output directory
    test_dir = Path("./temp_test_auto")
    mock_config.output_dir = str(test_dir / "Results")

    try:
        metadata_path = write_metadata(
            config=mock_config,
            simulation_type="Wave Impedance",
            polarization_mode="TE",
            dimension="2D",
            json_data=mock_gui_data,
            project_dir=None,  # Should use parent of output_dir
        )

        assert metadata_path is not None
        assert Path(metadata_path).exists()
        assert Path(metadata_path).parent == test_dir

    finally:
        # Cleanup
        if test_dir.exists():
            shutil.rmtree(test_dir, ignore_errors=True)


def test_metadata_json_validity(mock_config, mock_gui_data, test_project_dir):
    """Test that generated JSON is valid and parseable"""
    write_metadata(
        config=mock_config,
        simulation_type="Wave Impedance",
        polarization_mode="TE",
        dimension="2D",
        json_data=mock_gui_data,
        project_dir=test_project_dir,
    )

    metadata_path = test_project_dir / "project_metadata.json"

    # Should not raise any exceptions
    with open(metadata_path, "r") as f:
        metadata = json.load(f)

    # Should be able to dump and reload
    json_str = json.dumps(metadata, indent=4)
    reloaded = json.loads(json_str)

    assert reloaded == metadata, "JSON round-trip failed"


if __name__ == "__main__":
    # Allow running with: python test_metadata_creation.py
    pytest.main([__file__, "-v", "--tb=short"])
