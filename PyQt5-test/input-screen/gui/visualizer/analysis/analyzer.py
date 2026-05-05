"""
Top-level analysis coordinator.

Orchestrates field loading, probe extraction, FFT computation,
and plot generation for any simulation configuration.
"""

from pathlib import Path
import re
import numpy as np
from typing import Dict, List, Tuple, Optional
from matplotlib.figure import Figure

from .field_loader import FieldLoader, MeasurementPointInfo
from .probe import ProbeExtractor
from .templates import (
    get_templates,
    get_templates_by_domain,
    EquationTemplate,
)
from .plotter import TimeDomainPlotter, FrequencyDomainPlotter
from .equation_engine import EquationEngine


class Analyzer:
    """
    Coordinates field loading, probe extraction, equation evaluation,
    and plot generation for any simulation configuration.

    Usage:
        analyzer = Analyzer(results_dir, "Wave Impedance", "TE", "2D",
                            cfg={"dt": 1e-17})
        analyzer.load()
        plots = analyzer.create_default_plots()
    """

    def __init__(
        self,
        results_dir,
        simulation_type: str,
        polarization_mode: str,
        dimension: str = "2D",
        cfg: Optional[Dict] = None,
        probe_index: Optional[int] = None,
        selected_variables: Optional[List[str]] = None,
    ):
        self.results_dir = Path(results_dir)
        self.simulation_type = simulation_type
        self.polarization_mode = polarization_mode
        self.dimension = dimension
        self.cfg = cfg or {}
        self.probe_index = probe_index  # None = spatial midpoint
        if selected_variables is None:
            self.selected_variables = None
        else:
            self.selected_variables = list(dict.fromkeys(selected_variables))

        self.fields: Optional[Dict[str, np.ndarray]] = None
        self.probe_data: Optional[Dict[str, np.ndarray]] = None
        self.freq_data: Optional[Dict[str, np.ndarray]] = None
        self.dt: Optional[float] = None
        self.time_axis: Optional[np.ndarray] = None
        self.freq_axis: Optional[np.ndarray] = None
        self.measurement_point_info: List[MeasurementPointInfo] = []
        self._frequency_domain_variables = set()
        self._time_domain_variables = set()

    def load(self):
        """Load fields, extract probe data, compute FFTs."""
        loader = FieldLoader(self.results_dir)

        # FieldLoader only accepts base simulation fields (Ex, Hz, etc.).
        base_fields = FieldLoader.get_available_variables(
            self.simulation_type,
            self.polarization_mode,
            self.dimension,
        )
        selected_base_fields = None
        if self.selected_variables is not None:
            selected_base_fields = [
                var_name for var_name in self.selected_variables if var_name in base_fields
            ]
            if not selected_base_fields:
                selected_base_fields = None

        self.fields = loader.load(
            self.simulation_type,
            self.polarization_mode,
            self.dimension,
            selected_variables=selected_base_fields,
        )
        self._frequency_domain_variables = set(loader.frequency_domain_variables)
        self._time_domain_variables = set(loader.time_domain_variables)

        extractor = ProbeExtractor(self.fields, self.probe_index)
        self.probe_data = extractor.extract()

        self.dt = float(self.cfg.get("dt", 1.0))
        nt = next(iter(self.probe_data.values())).shape[0]
        self.time_axis = np.arange(nt) * self.dt
        self.freq_axis = np.fft.rfftfreq(nt, self.dt)

        # Discover and load measurement points
        self.measurement_point_info = loader.discover_measurement_points()
        self._load_measurement_points(loader)
        self._alias_selected_measurement_fields()
        self._frequency_domain_variables.update(loader.frequency_domain_variables)
        self._time_domain_variables.update(loader.time_domain_variables)

        if self._uses_frequency_domain_inputs():
            self._populate_domain_data_from_frequency_inputs()
            return

        # Pre-compute Hann-windowed FFTs for frequency domain
        win = np.hanning(nt)
        cg = np.mean(win) if nt > 0 else 1.0
        self.freq_data = {}
        for name, arr in self.probe_data.items():
            # Support both time-first and time-last arrays.
            if arr.ndim == 1:
                time_axis = 0
                win_reshaped = win
            else:
                time_axis = 0 if arr.shape[0] == nt else arr.ndim - 1
                if time_axis == 0:
                    win_reshaped = win.reshape(-1, 1)
                else:
                    win_reshaped = win.reshape(1, -1)
            # Sparse surfaces intentionally use NaN placeholders for unmeasured cells.
            # Multiplying those values by the Hann window can raise benign invalid warnings.
            with np.errstate(invalid="ignore"):
                windowed = arr * win_reshaped
            # Apply FFT along detected time axis.
            fft_result = np.fft.rfft(windowed, axis=time_axis) / cg
            self.freq_data[name] = fft_result

    def _uses_frequency_domain_inputs(self) -> bool:
        """Return True when loaded data is frequency-domain and needs inverse synthesis."""
        if not self.probe_data:
            return False

        available = set(self.probe_data.keys())
        freq_available = available.intersection(self._frequency_domain_variables)
        time_available = available.intersection(self._time_domain_variables)

        if freq_available and not time_available:
            return True

        if not freq_available:
            return all(np.iscomplexobj(np.asarray(arr)) for arr in self.probe_data.values())

        return False

    @staticmethod
    def _sample_count(arr: np.ndarray) -> int:
        """Return sample count along the analyzer's trailing sample axis."""
        if arr.ndim == 1:
            return arr.shape[0]
        return arr.shape[-1]

    @staticmethod
    def _resize_frequency_axis(arr: np.ndarray, target_bins: int, axis: int) -> np.ndarray:
        """Pad or truncate frequency bins so inverse transforms use one consistent axis size."""
        current_bins = arr.shape[axis]
        if current_bins == target_bins:
            return arr

        moved = np.moveaxis(arr, axis, -1)
        if current_bins > target_bins:
            resized = moved[..., :target_bins]
        else:
            pad_width = [(0, 0)] * moved.ndim
            pad_width[-1] = (0, target_bins - current_bins)
            resized = np.pad(moved, pad_width, mode="constant")
        return np.moveaxis(resized, -1, axis)

    def _inverse_frequency_series(
        self,
        arr: np.ndarray,
        nt: int,
        target_freq_bins: int,
    ) -> np.ndarray:
        """Convert frequency-domain samples to synthetic time-domain samples."""
        axis = 0 if arr.ndim == 1 else arr.ndim - 1

        bins = arr.shape[axis]
        if bins <= 0:
            shape = list(arr.shape)
            shape[axis] = nt
            return np.zeros(shape, dtype=float)

        if bins == 1:
            repeated = np.repeat(arr, nt, axis=axis)
            return np.real(repeated)

        prepared = self._resize_frequency_axis(arr, target_freq_bins, axis)
        return np.fft.irfft(prepared, n=nt, axis=axis)

    def _populate_domain_data_from_frequency_inputs(self):
        """Populate freq/time analyzer data when source arrays are frequency-domain."""
        self.dt = float(self.cfg.get("dt", 1.0))
        self.freq_data = {
            name: np.asarray(arr)
            for name, arr in self.probe_data.items()
        }

        max_freq_bins = max(self._sample_count(arr) for arr in self.freq_data.values())
        if max_freq_bins <= 0:
            raise ValueError("Frequency-domain data contains no samples")

        if max_freq_bins == 1:
            nt = max(int(self.cfg.get("nt", 2)), 2)
            freq0 = float(self.cfg.get("f0", 0.0) or 0.0)
            self.freq_axis = np.array([freq0], dtype=float)
        else:
            nt = max(2, (max_freq_bins - 1) * 2)
            self.freq_axis = np.fft.rfftfreq(nt, self.dt)

        converted = {}
        for name, arr in self.freq_data.items():
            converted[name] = self._inverse_frequency_series(
                np.asarray(arr),
                nt,
                max_freq_bins,
            )
        self.probe_data = converted
        self.time_axis = np.arange(nt) * self.dt

    def _load_measurement_points(self, loader: FieldLoader):
        """Load selected measurement points and add to probe_data."""
        if not self.measurement_point_info:
            return

        # Always load discovered measurement points; field-level filtering is handled
        # in _process_measurement_data so aliases can still resolve across surfaces.
        for mp_info in self.measurement_point_info:
            try:
                mp_data = loader.load_measurement_point(mp_info.safe_name)
            except FileNotFoundError:
                continue

            self._process_measurement_data(mp_info, mp_data)

    def _alias_selected_measurement_fields(self):
        """Map template field names (Ex, Hz, etc.) to selected measurement data."""
        if not self.measurement_point_info:
            return

        ordered_points = []
        seen_safe_names = set()

        if self.selected_variables is not None:
            for selected_var in self.selected_variables:
                for mp_info in self.measurement_point_info:
                    if mp_info.safe_name in seen_safe_names:
                        continue
                    for field_name in mp_info.available_fields:
                        var_base = f"{field_name}_{mp_info.safe_name}"
                        if selected_var == var_base or selected_var == f"{var_base}_mean":
                            ordered_points.append(mp_info)
                            seen_safe_names.add(mp_info.safe_name)
                            break

        for mp_info in self.measurement_point_info:
            if mp_info.safe_name not in seen_safe_names:
                ordered_points.append(mp_info)

        # First provider wins for each alias, preserving the selected variable order.
        assigned_aliases = set()
        for mp_info in ordered_points:
            for field_name in mp_info.available_fields:
                # Preserve base field probe series when present; only use
                # measurement aliases to fill missing template names.
                if field_name in self.probe_data:
                    assigned_aliases.add(field_name)
                    continue
                if field_name in assigned_aliases:
                    continue

                var_base = f"{field_name}_{mp_info.safe_name}"

                if mp_info.num_points > 1:
                    alias_data = self.probe_data.get(f"{var_base}_mean")
                    if alias_data is None and var_base in self.probe_data:
                        raw = np.asarray(self.probe_data[var_base])
                        alias_data = raw if raw.ndim == 1 else self._safe_spatial_mean(raw)
                else:
                    alias_data = self.probe_data.get(var_base)

                if alias_data is None:
                    continue

                # Overwrite standard probe aliases so templates use measurement data.
                self.probe_data[field_name] = alias_data
                assigned_aliases.add(field_name)
                if var_base in self._frequency_domain_variables:
                    self._frequency_domain_variables.add(field_name)
                if var_base in self._time_domain_variables:
                    self._time_domain_variables.add(field_name)

    @staticmethod
    def _infer_surface_shape(num_points: int) -> Tuple[int, int]:
        """Infer a near-square [x, y] shape for flattened surface data."""
        if num_points <= 0:
            return 0, 0

        root = int(np.sqrt(num_points))
        for x_count in range(root, 0, -1):
            if num_points % x_count == 0:
                return x_count, num_points // x_count
        return 1, num_points

    def _process_measurement_data(
        self,
        mp_info: MeasurementPointInfo,
        mp_data: Dict[str, np.ndarray],
    ):
        """Add measurement point data to probe_data dictionary."""
        selected_set = (
            set(self.selected_variables)
            if self.selected_variables is not None
            else None
        )

        for field_name, data in mp_data.items():
            # data shape: [timesteps, num_points]
            # Create variable name like Ex_MeasurementPoint1
            var_base = f"{field_name}_{mp_info.safe_name}"

            # Skip if selected_variables filter is active and this variable isn't selected
            if selected_set is not None:
                if var_base not in selected_set and f"{var_base}_mean" not in selected_set:
                    continue

            if mp_info.num_points == 1:
                # Single point: normalize both [samples, 1] and [samples] into 1D.
                arr = np.asarray(data)
                if arr.ndim == 2 and arr.shape[1] == 1:
                    self.probe_data[var_base] = arr.squeeze(axis=1)
                else:
                    self.probe_data[var_base] = arr.reshape(-1)
            else:
                raw_data = np.asarray(data)

                if raw_data.ndim == 1:
                    shape_meta = mp_info.metadata.get("shape") if mp_info.metadata else None
                    if (
                        mp_info.point_type == "surface"
                        and isinstance(shape_meta, (list, tuple))
                        and len(shape_meta) == 2
                        and raw_data.shape[0] == int(shape_meta[0]) * int(shape_meta[1])
                    ):
                        sx, sy = int(shape_meta[0]), int(shape_meta[1])
                        surface_frame = raw_data.reshape(sx, sy)
                        self.probe_data[var_base] = surface_frame[..., np.newaxis]
                    else:
                        # Generic multi-point single-frame data.
                        self.probe_data[var_base] = raw_data.reshape(-1, 1)

                    var_arr = np.asarray(self.probe_data[var_base])
                    mean_var = f"{var_base}_mean"
                    if selected_set is None or f"{var_base}_mean" in selected_set:
                        self.probe_data[mean_var] = self._safe_spatial_mean(var_arr)
                    continue

                # Surface with 2D shape metadata: reshape to [x, y, time]
                shape_meta = mp_info.metadata.get("shape") if mp_info.metadata else None
                grid_indices = (
                    mp_info.metadata.get("grid_indices")
                    if mp_info.metadata
                    else None
                )
                if mp_info.point_type == "surface" and raw_data.ndim == 2:
                    x_idx = None
                    y_idx = None
                    if isinstance(grid_indices, dict):
                        x_idx = grid_indices.get("x")
                        y_idx = grid_indices.get("y")

                    if (
                        isinstance(x_idx, list)
                        and isinstance(y_idx, list)
                        and len(x_idx) == raw_data.shape[1]
                        and len(y_idx) == raw_data.shape[1]
                    ):
                        min_x = min(int(v) for v in x_idx)
                        max_x = max(int(v) for v in x_idx)
                        min_y = min(int(v) for v in y_idx)
                        max_y = max(int(v) for v in y_idx)
                        nx_grid = max_x - min_x + 1
                        ny_grid = max_y - min_y + 1
                        mapped_dtype = np.result_type(raw_data.dtype, np.float64)

                        # Use a full uniform grid so every cell is exactly
                        # one grid-cell wide; the imshow extent then aligns
                        # perfectly with physical coords.
                        mapped = np.full(
                            (nx_grid, ny_grid, raw_data.shape[0]),
                            np.nan,
                            dtype=mapped_dtype,
                        )
                        for p in range(raw_data.shape[1]):
                            mapped[int(x_idx[p]) - min_x, int(y_idx[p]) - min_y, :] = raw_data[:, p]

                        # Some grid indices may be skipped due to floating-point
                        # rounding in measurement-point generation (multiple float
                        # positions snapping to the same integer cell).  Fill those
                        # entirely-NaN rows/columns by linear interpolation so they
                        # don't appear as solid bad-color bars in the heatmap.
                        observed_x = set(int(v) - min_x for v in x_idx)
                        observed_y = set(int(v) - min_y for v in y_idx)

                        for ix in range(nx_grid):
                            if ix not in observed_x:
                                prev_ix = next((j for j in range(ix - 1, -1, -1) if j in observed_x), None)
                                next_ix = next((j for j in range(ix + 1, nx_grid) if j in observed_x), None)
                                if prev_ix is not None and next_ix is not None:
                                    t = (ix - prev_ix) / (next_ix - prev_ix)
                                    mapped[ix, :, :] = (1 - t) * mapped[prev_ix, :, :] + t * mapped[next_ix, :, :]
                                elif prev_ix is not None:
                                    mapped[ix, :, :] = mapped[prev_ix, :, :]
                                elif next_ix is not None:
                                    mapped[ix, :, :] = mapped[next_ix, :, :]

                        for iy in range(ny_grid):
                            if iy not in observed_y:
                                prev_iy = next((j for j in range(iy - 1, -1, -1) if j in observed_y), None)
                                next_iy = next((j for j in range(iy + 1, ny_grid) if j in observed_y), None)
                                if prev_iy is not None and next_iy is not None:
                                    t = (iy - prev_iy) / (next_iy - prev_iy)
                                    mapped[:, iy, :] = (1 - t) * mapped[:, prev_iy, :] + t * mapped[:, next_iy, :]
                                elif prev_iy is not None:
                                    mapped[:, iy, :] = mapped[:, prev_iy, :]
                                elif next_iy is not None:
                                    mapped[:, iy, :] = mapped[:, next_iy, :]

                        self.probe_data[var_base] = mapped
                    else:
                        sx = 0
                        sy = 0
                        if (
                            isinstance(shape_meta, (list, tuple))
                            and len(shape_meta) == 2
                        ):
                            sx = max(int(shape_meta[0]), 0)
                            sy = max(int(shape_meta[1]), 0)

                        point_count = raw_data.shape[1]
                        if sx > 0 and sy > 0 and (sx * sy) != point_count:
                            if point_count % sx == 0:
                                sy = point_count // sx
                            elif point_count % sy == 0:
                                sx = point_count // sy
                            else:
                                sx, sy = self._infer_surface_shape(point_count)
                        elif sx <= 0 or sy <= 0:
                            sx, sy = self._infer_surface_shape(point_count)

                        if sx <= 0 or sy <= 0 or (sx * sy) != point_count:
                            # Keep behavior explicit and recoverable for rendering diagnostics.
                            self.probe_data[var_base] = raw_data.T
                        else:
                            surface_time = raw_data.reshape(raw_data.shape[0], sx, sy)
                            self.probe_data[var_base] = np.transpose(surface_time, (1, 2, 0))
                else:
                    # Generic multi-point: store as [num_points, timesteps]
                    self.probe_data[var_base] = raw_data.T

                # Also create pre-computed aggregate over all spatial axes -> [timesteps]
                # Only if explicitly selected or if no filter is active
                var_arr = np.asarray(self.probe_data[var_base])
                mean_var = f"{var_base}_mean"
                if selected_set is None or f"{var_base}_mean" in selected_set:
                    self.probe_data[mean_var] = self._safe_spatial_mean(var_arr)

    @staticmethod
    def _safe_spatial_mean(arr: np.ndarray) -> np.ndarray:
        """Average over all spatial axes while ignoring non-finite samples."""
        arr_np = np.asarray(arr)
        if arr_np.ndim <= 1:
            return arr_np

        axes = tuple(range(arr_np.ndim - 1))
        finite_mask = np.isfinite(arr_np)
        result_dtype = np.result_type(arr_np.dtype, np.float64)

        sum_values = np.where(finite_mask, arr_np, 0).sum(axis=axes, dtype=result_dtype)
        valid_counts = finite_mask.sum(axis=axes)

        output = np.full(sum_values.shape, np.nan, dtype=result_dtype)
        np.divide(sum_values, valid_counts, out=output, where=valid_counts > 0)
        return output

    def get_templates(self, domain: Optional[str] = None) -> List[EquationTemplate]:
        """Get equation templates, optionally filtered by domain."""
        if domain:
            return get_templates_by_domain(
                self.simulation_type,
                self.polarization_mode,
                self.dimension,
                domain,
            )
        return get_templates(
            self.simulation_type, self.polarization_mode, self.dimension
        )

    def get_available_variables(self) -> List[str]:
        """Return variable names available for equations."""
        if self.selected_variables is not None:
            selected_set = set(self.selected_variables)
            if self.probe_data is not None:
                available = {
                    var_name
                    for var_name in self.probe_data.keys()
                    if var_name in selected_set
                }

                # Template aliases (Ex/Ey/Hz/etc.) should be available only when
                # a corresponding selected variable exists (base or measurement).
                alias_candidates = set(self.get_all_variables())
                for mp_info in self.measurement_point_info:
                    alias_candidates.update(mp_info.available_fields)

                for field_name in alias_candidates:
                    if field_name not in self.probe_data:
                        continue
                    if field_name in selected_set:
                        available.add(field_name)
                        continue
                    if any(
                        selected_name.startswith(f"{field_name}_")
                        for selected_name in selected_set
                    ):
                        available.add(field_name)

                return list(available)
            return [
                var_name
                for var_name in self.get_all_variables()
                if var_name in selected_set
            ]
        if self.probe_data is not None:
            return list(self.probe_data.keys())
        return self.get_all_variables()

    def get_all_variables(self) -> List[str]:
        """Return all variable names for the simulation configuration."""
        return FieldLoader.get_available_variables(
            self.simulation_type, self.polarization_mode, self.dimension
        )

    def get_measurement_point_info(self) -> List[MeasurementPointInfo]:
        """Return discovered measurement point info for UI display."""
        return self.measurement_point_info

    def validate_expression(self, expression: str) -> Tuple[bool, str]:
        """Validate an expression against currently available variables."""
        available_variables = self.get_available_variables()
        variables = {name: np.array([0.0]) for name in available_variables}
        unavailable_variables = set(self.get_all_variables()) - set(available_variables)
        engine = EquationEngine(
            variables,
            unavailable_variables=unavailable_variables,
        )
        return engine.validate(expression)

    def plot_equation(
        self,
        expression: str,
        domain: str = "time",
        title: Optional[str] = None,
        y_label: Optional[str] = None,
        y_unit: str = "",
        display_mode: str = "real_imag",
    ) -> Figure:
        """Evaluate an arbitrary equation and return a matplotlib Figure."""
        if self.probe_data is None:
            raise RuntimeError("Call load() before plotting")

        # Re-resolve aliases at plot time so template variables track current selection.
        self._alias_selected_measurement_fields()
        valid, reason = self.validate_expression(expression)
        if not valid:
            raise ValueError(f"Invalid expression '{expression}': {reason}")

        if domain == "time":
            plotter = TimeDomainPlotter(self.probe_data, self.dt)
        else:
            plotter = FrequencyDomainPlotter(self.freq_data, self.freq_axis)

        resolved_label, resolved_unit = self._infer_y_axis_metadata(
            expression,
            domain,
            y_label,
            y_unit,
        )
        if domain == "time":
            return plotter.plot(expression, title, resolved_label, resolved_unit)
        return plotter.plot(expression, title, resolved_label, resolved_unit, display_mode)

    def _infer_y_axis_metadata(
        self,
        expression: str,
        domain: str,
        y_label: Optional[str],
        y_unit: str,
    ) -> Tuple[str, str]:
        """Infer clearer y-axis metadata when callers don't specify one."""
        explicit_label = (y_label or "").strip()
        explicit_unit = (y_unit or "").strip()

        if explicit_label and explicit_label.lower() != "value":
            return explicit_label, explicit_unit

        expr = expression.strip()
        expr_lower = expr.lower()

        available_variables = set(self.get_available_variables())
        if expr in available_variables:
            return self._axis_label_for_variable(expr, explicit_unit)

        # Common function-driven defaults for user-entered equations.
        if "log10(" in expr_lower:
            return "Magnitude", explicit_unit or "dB"
        if expr_lower.startswith("abs("):
            return "Magnitude", explicit_unit
        if expr_lower.startswith("real("):
            return "Real Component", explicit_unit
        if expr_lower.startswith("imag("):
            return "Imaginary Component", explicit_unit

        # If a known variable appears in the expression, derive a contextual label.
        tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr)
        for token in tokens:
            if token in available_variables:
                label, unit = self._axis_label_for_variable(token, explicit_unit)
                if expr_lower.startswith("abs("):
                    return f"|{label}|", unit
                return label, unit

        fallback_label = "Spectral Value" if domain == "frequency" else "Signal Value"
        return fallback_label, explicit_unit

    @staticmethod
    def _axis_label_for_variable(variable_name: str, explicit_unit: str) -> Tuple[str, str]:
        """Map variable naming conventions to user-facing labels and units."""
        name = variable_name.strip()
        upper = name.upper()

        if upper.startswith("E"):
            return f"Electric Field {name}", explicit_unit or "V/m"
        if upper.startswith("H"):
            return f"Magnetic Field {name}", explicit_unit or "A/m"
        if upper.startswith("S") and len(upper) >= 3 and upper[1:].isdigit():
            return name, explicit_unit

        return name, explicit_unit

    def plot_template(self, template: EquationTemplate) -> Figure:
        """Plot a specific template equation."""
        if self.probe_data is None:
            raise RuntimeError("Call load() before plotting")

        # Re-resolve aliases at plot time so templates use the selected point.
        self._alias_selected_measurement_fields()

        if template.domain == "time":
            plotter = TimeDomainPlotter(self.probe_data, self.dt)
        else:
            plotter = FrequencyDomainPlotter(self.freq_data, self.freq_axis)
        return plotter.plot_template(template)

    def create_default_plots(self) -> List[Tuple[str, Figure]]:
        """
        Create figures for all templates.

        Returns:
            List of (title, figure) tuples.
        """
        if self.probe_data is None:
            raise RuntimeError("Call load() before plotting")

        plots = []
        for template in self.get_templates():
            fig = self.plot_template(template)
            plots.append((template.name, fig))
        return plots
