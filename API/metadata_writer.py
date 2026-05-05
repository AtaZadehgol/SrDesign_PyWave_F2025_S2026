"""
Metadata file writer for simulation results
Writes project_metadata.json - output metadata (what was simulated and where results are)
The GUI's simulation_config.json serves as the input description.
"""

from datetime import datetime
import json
from pathlib import Path
import traceback


def write_metadata(
    config,
    simulation_type,
    polarization_mode,
    dimension,
    json_data=None,
    project_dir=None,
):
    """
    Write project_metadata.json file to project directory
    This file describes the OUTPUT - what was actually simulated and where results are
    References the existing simulation_config.json as the input description.

    Args:
        config: InitialValues instance with simulation configuration
        simulation_type: Type of simulation (e.g., "Wave Impedance")
        polarization_mode: Polarization mode (e.g., "TE", "TM")
        dimension: Dimension (e.g., "2D", "3D")
        json_data: Original JSON data from GUI (not used, kept for compatibility)
        project_dir: Path to project directory (if None, uses config.output_dir parent)

    Returns:
        Path to written metadata file, or None if error
    """
    try:
        if project_dir is None:
            project_dir = Path(config.output_dir).parent
        else:
            project_dir = Path(project_dir)

        metadata = {
            "project_name": project_dir.name,
            "simulation_type": simulation_type,
            "polarization_mode": polarization_mode,
            "dimension": dimension,
            "results_path": "./Results",  # Relative to project root
            "timestamp": datetime.now().isoformat(),
            "simulation_config_file": "./simulation_config.json",
            "solver_parameters": {
                "dt": float(config.delta_t),
                "nt": int(config.nt) if hasattr(config, "nt") else None,
                "nx": int(config.nx) if hasattr(config, "nx") else None,
                "ny": int(config.ny) if hasattr(config, "ny") else None,
                "by": int(config.by) if hasattr(config, "by") else None,
                "cell": 3,  # Default cell offset for probe positioning
                "dy": float(config.delta_x) if hasattr(config, "delta_x") else None,
            },
        }

        project_dir.mkdir(parents=True, exist_ok=True)

        metadata_path = project_dir / "project_metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=4)

        print(f"Project metadata saved to: {metadata_path}")
        return str(metadata_path)

    except Exception as e:
        print(f"[WARNING] Failed to write metadata: {e}")

        traceback.print_exc()
        return None


def read_metadata(project_dir):
    """
    Read project_metadata.json from project directory

    Args:
        project_dir: Path to project directory

    Returns:
        Dictionary with metadata, or None if not found
    """
    try:
        metadata_path = Path(project_dir) / "project_metadata.json"
        if not metadata_path.exists():
            return None

        with open(metadata_path, "r") as f:
            return json.load(f)

    except Exception as e:
        print(f"Warning: Failed to read metadata: {e}")
        return None


def read_simulation_config(project_dir):
    """
    Read simulation_config.json from project directory

    Args:
        project_dir: Path to project directory

    Returns:
        Dictionary with simulation configuration, or None if not found
    """
    try:
        config_path = Path(project_dir) / "simulation_config.json"
        if not config_path.exists():
            return None

        with open(config_path, "r") as f:
            return json.load(f)

    except Exception as e:
        print(f"Warning: Failed to read simulation config: {e}")
        return None
