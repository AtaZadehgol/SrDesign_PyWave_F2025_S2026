"""
Loads simulation result .npy files based on simulation configuration.

Maps (simulation_type, polarization_mode, dimension) to the expected
field variable names and filenames, then loads and validates them.
"""

from dataclasses import dataclass
import json
from pathlib import Path
import re
import numpy as np
from typing import Dict, List, Optional, Set, Tuple

# Maps simulation config to {variable_name: filename}
FIELD_FILES: Dict[Tuple[str, str, str], Dict[str, str]] = {
    ("Wave Impedance", "TE", "2D"): {
        "Ex": "ex_zwave.npy",
        "Hz": "hz_zwave.npy",
    },
    ("Wave Impedance", "TM", "2D"): {
        "Ez": "ez_zwave.npy",
        "Hx": "hx_zwave.npy",
    },
    ("Wave Impedance", "TE", "3D"): {
        "Ey": "ey_zwave.npy",
        "Hz": "hz_zwave.npy",
    },
    ("Wave Impedance", "TM", "3D"): {
        "Ez": "ez_zwave.npy",
        "Hy": "hy_zwave.npy",
    },
    # S-parameter exports are frequency-domain arrays.
    ("S-Parameters", "TE", "2D"): {
        "S11": "s11.npy",
        "S21": "s21.npy",
        "S12": "s12.npy",
        "S22": "s22.npy",
    },
    ("S-Parameters", "TM", "2D"): {
        "S11": "s11.npy",
        "S21": "s21.npy",
        "S12": "s12.npy",
        "S22": "s22.npy",
    },
    ("S-Parameters", "TE", "3D"): {
        "S11": "s11.npy",
        "S21": "s21.npy",
        "S12": "s12.npy",
        "S22": "s22.npy",
    },
    ("S-Parameters", "TM", "3D"): {
        "S11": "s11.npy",
        "S21": "s21.npy",
        "S12": "s12.npy",
        "S22": "s22.npy",
    },
    ("Scattering Loss", "TE", "2D"): {
        "Ex": "ex_zwave.npy",
        "Hz": "hz_zwave.npy",
    },
    ("Scattering Loss", "TM", "2D"): {
        "Ez": "ez_zwave.npy",
        "Hx": "hx_zwave.npy",
    },
    ("Scattering Loss", "TE", "3D"): {
        "Ey": "ey_zwave.npy",
        "Hz": "hz_zwave.npy",
    },
    ("Scattering Loss", "TM", "3D"): {
        "Ez": "ez_zwave.npy",
        "Hy": "hy_zwave.npy",
    },
    # Custom Experiment currently reuses standard wave-style field exports.
    ("Custom Experiment", "TE", "2D"): {
        "Ex": "ex_zwave.npy",
        "Hz": "hz_zwave.npy",
    },
    ("Custom Experiment", "TM", "2D"): {
        "Ez": "ez_zwave.npy",
        "Hx": "hx_zwave.npy",
    },
    ("Custom Experiment", "TE", "3D"): {
        "Ey": "ey_zwave.npy",
        "Hz": "hz_zwave.npy",
    },
    ("Custom Experiment", "TM", "3D"): {
        "Ez": "ez_zwave.npy",
        "Hy": "hy_zwave.npy",
    },
}


def _normalize_token(value: str) -> str:
    """Normalize config tokens for tolerant matching."""
    return re.sub(r"[^a-z0-9]", "", str(value).strip().lower())


_NORMALIZED_CONFIG_KEYS: Dict[Tuple[str, str, str], Tuple[str, str, str]] = {
    (_normalize_token(sim), _normalize_token(pol), _normalize_token(dim)): (sim, pol, dim)
    for (sim, pol, dim) in FIELD_FILES.keys()
}


@dataclass
class MeasurementPointInfo:
    """Information about a measurement point discovered from metadata files."""

    name: str  # Human-readable name (e.g., "Measurement Point 1")
    safe_name: str  # File-safe name (e.g., "Measurement_Point_1")
    point_type: str  # "point", "line", or "surface"
    num_points: int  # Number of spatial points
    available_fields: List[str]  # e.g., ["Ex", "Ey", "Hz"]
    shape: Optional[Tuple]  # Shape of the data arrays (e.g., (timesteps, num_points))
    metadata: dict  # Full metadata dict


class FieldLoader:
    """Loads simulation field arrays from a results directory."""

    def __init__(self, results_dir):
        self.results_dir = Path(results_dir)
        self.frequency_domain_variables: Set[str] = set()
        self.time_domain_variables: Set[str] = set()

    @staticmethod
    def _build_frequency_variant(filename: str) -> str:
        """Build an `_fft` variant of a base `.npy` filename."""
        path = Path(filename)
        stem = path.stem
        suffix = path.suffix or ".npy"

        if stem.endswith("_fft"):
            return filename
        if stem.endswith("_zwave"):
            stem = stem[: -len("_zwave")]
        return f"{stem}_fft{suffix}"

    @staticmethod
    def _filename_candidates(filename: str) -> List[Tuple[str, bool]]:
        """Return candidate filenames in lookup order with frequency-domain flags."""
        candidates: List[Tuple[str, bool]] = []
        seen = set()

        def _add(name: str):
            if name in seen:
                return
            seen.add(name)
            candidates.append((name, Path(name).stem.endswith("_fft")))

        # Prefer `_fft` files when both frequency and legacy variants exist.
        _add(FieldLoader._build_frequency_variant(filename))
        _add(filename)

        stem = Path(filename).stem
        suffix = Path(filename).suffix or ".npy"
        if stem.endswith("_fft"):
            _add(f"{stem[: -len('_fft')]}{suffix}")

        return candidates

    def _resolve_existing_file(self, filename: str) -> Optional[Tuple[Path, bool]]:
        """Resolve a requested result filename to an existing file path."""
        for candidate, is_frequency_domain in self._filename_candidates(filename):
            path = self.results_dir / candidate
            if path.exists():
                return path, is_frequency_domain
        return None

    def _register_loaded_variable(self, variable_name: str, is_frequency_domain: bool):
        """Track whether a loaded variable came from frequency-domain files."""
        if is_frequency_domain:
            self.frequency_domain_variables.add(variable_name)
            self.time_domain_variables.discard(variable_name)
        else:
            self.time_domain_variables.add(variable_name)
            self.frequency_domain_variables.discard(variable_name)

    @staticmethod
    def _resolve_config_key(
        simulation_type: str,
        polarization_mode: str,
        dimension: str,
    ) -> Optional[Tuple[str, str, str]]:
        """Resolve user-provided config values to a canonical FIELD_FILES key."""
        direct_key = (simulation_type, polarization_mode, dimension)
        if direct_key in FIELD_FILES:
            return direct_key

        normalized_key = (
            _normalize_token(simulation_type),
            _normalize_token(polarization_mode),
            _normalize_token(dimension),
        )
        return _NORMALIZED_CONFIG_KEYS.get(normalized_key)

    def load(
        self,
        simulation_type: str,
        polarization_mode: str,
        dimension: str = "2D",
        selected_variables: Optional[List[str]] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Load all field arrays for the given simulation configuration.

        Returns:
            Dict mapping variable names (e.g., "Ex", "Hz") to numpy arrays.

        Raises:
            ValueError: Unknown simulation config.
            FileNotFoundError: Missing result file.
            ValueError: Shape mismatch between fields.
        """
        key = self._resolve_config_key(simulation_type, polarization_mode, dimension)
        file_map = FIELD_FILES.get(key) if key is not None else None
        if file_map is None:
            raise ValueError(
                f"Unknown simulation configuration: "
                f"type={simulation_type}, mode={polarization_mode}, dim={dimension}"
            )

        if selected_variables is not None:
            selected_set = set(selected_variables)
            unknown = selected_set - set(file_map.keys())
            if unknown:
                unknown_str = ", ".join(sorted(unknown))
                raise ValueError(
                    f"Unknown selected variable(s) for this configuration: {unknown_str}"
                )

            file_map = {
                var_name: filename
                for var_name, filename in file_map.items()
                if var_name in selected_set
            }

        self.frequency_domain_variables.clear()
        self.time_domain_variables.clear()

        fields: Dict[str, np.ndarray] = {}
        for var_name, filename in file_map.items():
            resolved = self._resolve_existing_file(filename)
            if resolved is None:
                raise FileNotFoundError(
                    f"Expected result file not found. Tried: "
                    f"{[name for name, _ in self._filename_candidates(filename)]}"
                )

            path, is_frequency_domain = resolved
            fields[var_name] = np.load(path)
            self._register_loaded_variable(var_name, is_frequency_domain)

        # Validate all fields have the same shape
        shapes = {name: arr.shape for name, arr in fields.items()}
        unique_shapes = set(shapes.values())
        if len(unique_shapes) > 1:
            shape_str = ", ".join(f"{n}: {s}" for n, s in shapes.items())
            raise ValueError(f"Shape mismatch between fields: {shape_str}")

        return fields

    @staticmethod
    def get_available_variables(
        simulation_type: str,
        polarization_mode: str,
        dimension: str = "2D",
    ) -> List[str]:
        """Return list of variable names available for this config."""
        key = FieldLoader._resolve_config_key(
            simulation_type,
            polarization_mode,
            dimension,
        )
        file_map = FIELD_FILES.get(key) if key is not None else None
        if file_map is None:
            return []
        return list(file_map.keys())

    def discover_measurement_points(self) -> List[MeasurementPointInfo]:
        """
        Scan results directory for metadata_*.json files and return measurement point info.

        Returns:
            List of MeasurementPointInfo dataclasses describing available measurement points.
        """
        measurement_points = []

        for metadata_path in sorted(self.results_dir.glob("metadata_*.json")):
            # Extract safe_name from filename: metadata_{safe_name}.json
            safe_name = metadata_path.stem[len("metadata_") :]
            if not safe_name:
                continue

            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue

            # Find available field files for this measurement point
            available_fields = []
            for field_prefix in ["ex", "ey", "ez", "hx", "hy", "hz"]:
                filename = f"{field_prefix}_{safe_name}.npy"
                resolved = self._resolve_existing_file(filename)
                if resolved is not None:
                    # Capitalize field name to match convention (ex -> Ex)
                    field_name = field_prefix[0].upper() + field_prefix[1]
                    available_fields.append(field_name)

            if not available_fields:
                continue

            mp_info = MeasurementPointInfo(
                name=metadata.get("name", safe_name),
                safe_name=safe_name,
                point_type=metadata.get("type", "point"),
                num_points=metadata.get("num_points", 1),
                available_fields=available_fields,
                shape=metadata.get("shape", None),
                metadata=metadata,
            )
            measurement_points.append(mp_info)

        return measurement_points

    def load_measurement_point(
        self,
        safe_name: str,
        fields: Optional[List[str]] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Load measurement point data files.

        Args:
            safe_name: The safe (filesystem-friendly) name of the measurement point.
            fields: Optional list of field names to load (e.g., ["Ex", "Hz"]).
                   If None, loads all available fields.

        Returns:
            Dict mapping field names (e.g., "Ex") to numpy arrays of shape [timesteps, num_points].

        Raises:
            FileNotFoundError: If no data files found for this measurement point.
        """
        data = {}

        # Determine which fields to load
        if fields is None:
            # Discover available fields
            fields_to_load = []
            for field_prefix in ["ex", "ey", "ez", "hx", "hy", "hz"]:
                filename = f"{field_prefix}_{safe_name}.npy"
                resolved = self._resolve_existing_file(filename)
                if resolved is not None:
                    field_file, is_frequency_domain = resolved
                    field_name = field_prefix[0].upper() + field_prefix[1]
                    fields_to_load.append((field_name, field_file, is_frequency_domain))
        else:
            fields_to_load = []
            for field_name in fields:
                field_prefix = field_name[0].lower() + field_name[1].lower()
                filename = f"{field_prefix}_{safe_name}.npy"
                resolved = self._resolve_existing_file(filename)
                if resolved is not None:
                    field_file, is_frequency_domain = resolved
                    fields_to_load.append((field_name, field_file, is_frequency_domain))

        if not fields_to_load:
            raise FileNotFoundError(
                f"No data files found for measurement point '{safe_name}'"
            )

        for field_name, field_file, is_frequency_domain in fields_to_load:
            data[field_name] = np.load(field_file)
            self._register_loaded_variable(
                f"{field_name}_{safe_name}",
                is_frequency_domain,
            )

        return data
