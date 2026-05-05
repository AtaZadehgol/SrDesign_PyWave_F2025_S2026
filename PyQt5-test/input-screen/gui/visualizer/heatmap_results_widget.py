"""Heatmap-focused results widget for measurement surfaces."""

import json
from pathlib import Path
from typing import Dict, List, Optional

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colors as mcolors
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle as MplRectangle
from matplotlib.ticker import FuncFormatter
from PyQt5.QtCore import QEvent, Qt, QSignalBlocker, QTimer
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSlider,
    QSizePolicy,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .analysis.analyzer import Analyzer
from .canvas_manager import CanvasManager
from .components.reference_panel.variable_selector import VariableSelectorWidget
from .components.animation_controller import AnimationController
from .components.geometry_overlay_manager import (
    GeometryOverlayManager,
    CPML_OVERLAY_COLOR,
    SOURCE_LEGEND_COLOR,
)
from .results_loader import ResultsLoader


class HeatmapResultsWidget(QWidget):
    """Display a single-frame surface heatmap with geometry overlay."""

    _DEFAULT_HEATMAP_COLORMAP = "bwr"
    _DEFAULT_HEATMAP_PERCENTILES = (1.0, 99.0)

    def __init__(self, file_handler=None, parent=None):
        super().__init__(parent)

        self.file_handler = file_handler
        self.canvas_manager: Optional[CanvasManager] = None
        self.analyzer: Optional[Analyzer] = None
        self.current_figure: Optional[Figure] = None

        self.project_root_path: Optional[Path] = None
        self.current_project_path: Optional[Path] = None
        self.active_results_path: Optional[Path] = None
        self.active_version_name: str = "Current"
        self._is_loading_results: bool = False

        self.simulation_type: str = ""
        self.polarization_mode: str = ""
        self.dimension: str = "2D"
        self.surface_measurement_info: List = []
        self.surface_variables: List[str] = []
        self.selected_variables: List[str] = []
        self.active_variable: Optional[str] = None
        self.active_field: Optional[str] = None
        self.active_domain: str = "time"
        self.frequency_display_mode: str = "magnitude"
        self.frame_index: int = 0
        self.geometry_rectangles: List[dict] = []
        self.measurement_surface_rectangles: List[dict] = []
        self.cpml_rectangles: List[dict] = []
        self.source_shapes: List[dict] = []
        self.domain_bounds: Optional[tuple] = None
        self.show_cpml_overlay: bool = False
        self.current_surface_data: Optional[np.ndarray] = None
        self.current_surface_data_list: List[np.ndarray] = []
        self.current_surface_extent: Optional[List[float]] = None
        self.current_ax = None
        self.current_image = None
        self.current_axes: List = []
        self.current_images: List = []
        self.current_plot_labels: List[str] = []
        self._render_generation: int = 0
        self._resize_update_pending: bool = False

        self.selection_metadata_key = "selected_variables_heatmap"
        self.active_metadata_key = "active_heatmap_variable"
        self.domain_metadata_key = "active_heatmap_domain"
        self.frequency_display_metadata_key = "active_heatmap_frequency_display_mode"
        self.cpml_overlay_metadata_key = "show_cpml_overlay_heatmap"
        self._loaded_results_identity: Optional[str] = None

        # Initialize components (animation_controller will be set up in _init_ui)
        self.animation_controller: Optional[AnimationController] = None

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(6)

        controls.addWidget(QLabel("Field Variable:"))
        self.active_variable_selector = QComboBox()
        self.active_variable_selector.setEnabled(False)
        self.active_variable_selector.currentTextChanged.connect(
            self._on_active_variable_changed
        )
        controls.addWidget(self.active_variable_selector, 1)

        controls.addWidget(QLabel("Domain:"))
        self.domain_selector = QComboBox()
        self.domain_selector.addItems(["Time Domain", "Frequency Domain"])
        self.domain_selector.setEnabled(False)
        self.domain_selector.currentIndexChanged.connect(self._on_domain_changed)
        controls.addWidget(self.domain_selector)

        self.frequency_display_label = QLabel("Frequency View:")
        controls.addWidget(self.frequency_display_label)
        self.frequency_display_selector = QComboBox()
        self.frequency_display_selector.addItems(
            ["Magnitude", "Phase", "Real", "Imaginary"]
        )
        self.frequency_display_selector.setEnabled(False)
        self.frequency_display_selector.currentIndexChanged.connect(
            self._on_frequency_display_changed
        )
        controls.addWidget(self.frequency_display_selector)

        self.reference_button = QPushButton("Reference")
        self.reference_button.setCheckable(True)
        self.reference_button.setChecked(False)
        self.reference_button.toggled.connect(lambda _checked: self._toggle_reference_panel())
        controls.addWidget(self.reference_button)

        layout.addLayout(controls)

        animation_controls = QHBoxLayout()
        animation_controls.setContentsMargins(0, 0, 0, 0)
        animation_controls.setSpacing(6)

        animation_controls.addWidget(QLabel("Frame:"))
        self.frame_slider = QSlider(Qt.Horizontal)
        self.frame_slider.setEnabled(False)
        self.frame_slider.setMinimum(0)
        self.frame_slider.setMaximum(0)
        animation_controls.addWidget(self.frame_slider, 1)

        self.frame_label = QLabel("0/0")
        animation_controls.addWidget(self.frame_label)

        self.play_button = QPushButton("Play")
        self.play_button.setCheckable(True)
        self.play_button.setEnabled(False)
        animation_controls.addWidget(self.play_button)

        layout.addLayout(animation_controls)

        # Initialize animation controller with UI elements
        self.animation_controller = AnimationController(
            frame_slider=self.frame_slider,
            frame_label=self.frame_label,
            play_button=self.play_button,
        )
        self.animation_controller.set_on_frame_changed_callback(self._update_frame)
        self.frame_slider.valueChanged.connect(self.animation_controller.on_frame_slider_changed)
        self.play_button.toggled.connect(self.animation_controller.toggle_animation)

        self.splitter = QSplitter(Qt.Horizontal)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(False)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.viewport().installEventFilter(self)

        self.canvas_container = QWidget()
        self.canvas_layout = QVBoxLayout(self.canvas_container)
        self.canvas_layout.setContentsMargins(0, 0, 0, 0)

        self.placeholder_label = QLabel(
            "No heatmap results loaded.\nRun a simulation and open Heatmap View."
        )
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setWordWrap(True)
        self.placeholder_label.setMinimumSize(420, 140)
        self.placeholder_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.placeholder_label.setStyleSheet(
            """
            QLabel {
                font-size: 14pt;
                color: #666;
                padding: 40px;
            }
            """
        )
        self.canvas_layout.addWidget(self.placeholder_label)

        self.scroll_area.setWidget(self.canvas_container)
        self.splitter.addWidget(self.scroll_area)

        self.ref_panel_container = QWidget()
        self.ref_panel_layout = QVBoxLayout(self.ref_panel_container)
        self.ref_panel_layout.setContentsMargins(6, 6, 6, 6)

        self.variable_selector = VariableSelectorWidget(
            file_handler=self.file_handler,
            parent=self,
        )
        self.variable_selector.set_surface_only_mode(True)
        self.variable_selector.set_include_aggregates(False)
        self.variable_selector.selection_changed.connect(self._apply_variable_selection)
        self.variable_selector.version_selector.currentTextChanged.connect(
            self._on_result_version_changed
        )
        self.ref_panel_layout.addWidget(self.variable_selector)

        self.cpml_overlay_checkbox = QCheckBox("Show CPML overlay")
        self.cpml_overlay_checkbox.setChecked(False)
        self.cpml_overlay_checkbox.setEnabled(False)
        self.cpml_overlay_checkbox.toggled.connect(self._on_cpml_overlay_toggled)
        self.ref_panel_layout.addWidget(self.cpml_overlay_checkbox)

        self.ref_panel = QTextBrowser()
        self.ref_panel.setHtml(self._default_reference_html())
        self.ref_panel_layout.addWidget(self.ref_panel, 1)

        self.ref_panel_container.setMinimumWidth(220)
        self.ref_panel_container.setMaximumWidth(380)
        self.ref_panel_container.hide()
        self.splitter.addWidget(self.ref_panel_container)

        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        layout.addWidget(self.splitter)

        self.canvas_manager = CanvasManager(self.canvas_layout)
        self._sync_heatmap_mode_controls()

    @staticmethod
    def _default_reference_html() -> str:
        return (
            "<h3>Heatmap View</h3>"
            "<p>Select one or more surface measurements in the table.</p>"
            "<p>The dropdown switches the field plotted for every selected surface.</p>"
            "<p>Switch the domain between time and frequency, and choose how to display complex FFT values.</p>"
            "<p>Field labels use EM units: E-components in V/m and H-components in A/m."
            " (e.g., H<sub>z</sub> is magnetic field, not frequency in hertz).</p>"
        )

    @staticmethod
    def _field_display_label(field_name: Optional[str]) -> str:
        labels = {
            "EX": "Electric Field E_x (V/m)",
            "EY": "Electric Field E_y (V/m)",
            "EZ": "Electric Field E_z (V/m)",
            "HX": "Magnetic Field H_x (A/m)",
            "HY": "Magnetic Field H_y (A/m)",
            "HZ": "Magnetic Field H_z (A/m)",
        }

        key = (field_name or "").strip().upper()
        if key in labels:
            return labels[key]

        return f"{field_name or 'Field'} (simulation units)"

    def _toggle_reference_panel(self):
        if self.reference_button.isChecked():
            self._refresh_result_versions()
            self.ref_panel_container.show()
        else:
            self.ref_panel_container.hide()

    def _show_placeholder_message(self, message: str):
        self.placeholder_label.setText(message)

        viewport = self.scroll_area.viewport().size()
        target_w = max(420, viewport.width() - 8)
        target_h = max(180, viewport.height() - 8)

        self.canvas_container.resize(target_w, target_h)
        self.canvas_container.setMinimumSize(target_w, target_h)
        self.placeholder_label.show()

    def _refresh_result_versions(self):
        self.variable_selector.update_result_versions()
        self._set_version_selector(self.active_version_name)

    def _set_version_selector(self, version_name: str):
        selector = self.variable_selector.version_selector
        index = selector.findText(version_name)
        if index < 0:
            index = selector.findText("Current")

        blocker = QSignalBlocker(selector)
        selector.setCurrentIndex(index)
        del blocker

    def _resolve_snapshot_root(self, version_name: Optional[str] = None) -> Optional[Path]:
        if not self.project_root_path:
            return None

        if not version_name or version_name == "Current":
            return self.project_root_path

        if self.file_handler and getattr(self.file_handler, "archive_dir_path", None):
            archive_root = Path(self.file_handler.archive_dir_path)
        else:
            archive_root = self.project_root_path / "archive"

        return archive_root / version_name

    def _on_result_version_changed(self, version_name: str):
        if self._is_loading_results or not self.project_root_path:
            return
        if version_name == self.active_version_name:
            return

        snapshot_root = self._resolve_snapshot_root(version_name)
        if snapshot_root is None or not snapshot_root.exists():
            return

        self.load_results(self.project_root_path, archive_name=version_name)

    def _surface_variable_names_from_info(self, measurement_info: List) -> List[str]:
        variables: List[str] = []
        for mp_info in measurement_info:
            variables.append(mp_info.safe_name)
        return variables

    def _available_surface_fields(self) -> List[str]:
        fields: List[str] = []
        seen = set()
        for mp_info in self.surface_measurement_info:
            for field_name in mp_info.available_fields:
                if field_name not in seen:
                    seen.add(field_name)
                    fields.append(field_name)
        return fields

    @staticmethod
    def _split_variable_name(variable_name: Optional[str]):
        if not variable_name or "_" not in variable_name:
            return None, None
        return variable_name.split("_", 1)

    def _set_active_field_from_metadata(self, variable_name: Optional[str]):
        field_name, _surface_name = self._split_variable_name(variable_name)
        self.active_field = field_name

    def _ensure_active_field(self):
        available_fields = self._available_surface_fields()
        if self.active_field not in available_fields:
            self.active_field = available_fields[0] if available_fields else None

    def _sanitize_selected_variables(self, selected: Optional[List[str]]) -> List[str]:
        self.variable_selector.set_variable_sources([], self.surface_measurement_info)
        sanitized = self.variable_selector.sanitize_selected_variables(selected)
        return [name for name in sanitized if not name.endswith("_mean")]

    def _read_persisted_selection(self, metadata: Dict) -> Optional[List[str]]:
        persisted = metadata.get(self.selection_metadata_key)
        if isinstance(persisted, list):
            return persisted
        return None

    def _read_persisted_active_variable(self, metadata: Dict) -> Optional[str]:
        active_variable = metadata.get(self.active_metadata_key)
        if isinstance(active_variable, str) and active_variable:
            return active_variable
        return None

    def _read_persisted_cpml_overlay(self, metadata: Dict) -> Optional[bool]:
        value = metadata.get(self.cpml_overlay_metadata_key)
        if isinstance(value, bool):
            return value
        return None

    @staticmethod
    def _load_cpml_rectangles(project_root: Path, domain_bounds: Optional[tuple]) -> List[dict]:
        return GeometryOverlayManager.load_cpml_rectangles(project_root, domain_bounds)

    def _read_persisted_heatmap_domain(self, metadata: Dict) -> Optional[str]:
        value = metadata.get(self.domain_metadata_key)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"time", "frequency"}:
                return normalized
        return None

    def _read_persisted_frequency_display_mode(self, metadata: Dict) -> Optional[str]:
        value = metadata.get(self.frequency_display_metadata_key)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"magnitude", "phase", "real", "imaginary"}:
                return normalized
        return None

    def _current_domain(self) -> str:
        if hasattr(self, "domain_selector") and self.domain_selector.currentIndex() == 1:
            return "frequency"
        return "time"

    def _current_frequency_display_mode(self) -> str:
        if not hasattr(self, "frequency_display_selector"):
            return "magnitude"

        index = self.frequency_display_selector.currentIndex()
        modes = ["magnitude", "phase", "real", "imaginary"]
        if 0 <= index < len(modes):
            return modes[index]
        return "magnitude"

    def _set_domain_selector(self, domain: str):
        blocker = QSignalBlocker(self.domain_selector)
        self.domain_selector.setCurrentIndex(0 if domain == "time" else 1)
        del blocker

    def _set_frequency_display_selector(self, display_mode: str):
        modes = ["magnitude", "phase", "real", "imaginary"]
        display_mode = display_mode if display_mode in modes else "magnitude"
        blocker = QSignalBlocker(self.frequency_display_selector)
        self.frequency_display_selector.setCurrentIndex(modes.index(display_mode))
        del blocker

    def _sync_heatmap_mode_controls(self):
        domain = self.active_domain if self.active_domain in {"time", "frequency"} else "time"
        display_mode = (
            self.frequency_display_mode
            if self.frequency_display_mode in {"magnitude", "phase", "real", "imaginary"}
            else "magnitude"
        )

        self._set_domain_selector(domain)
        self._set_frequency_display_selector(display_mode)

        controls_enabled = bool(self.analyzer and self.active_field)
        self.domain_selector.setEnabled(controls_enabled)

        show_frequency_controls = domain == "frequency"
        self.frequency_display_label.setVisible(show_frequency_controls)
        self.frequency_display_selector.setEnabled(controls_enabled and show_frequency_controls)
        self.frequency_display_selector.setVisible(show_frequency_controls)

    def _format_frequency_value(self, frequency_hz: float) -> str:
        magnitude = abs(float(frequency_hz))
        if magnitude >= 1e9:
            return f"{frequency_hz / 1e9:.3f} GHz"
        if magnitude >= 1e6:
            return f"{frequency_hz / 1e6:.3f} MHz"
        if magnitude >= 1e3:
            return f"{frequency_hz / 1e3:.3f} kHz"
        return f"{frequency_hz:.3f} Hz"

    def _frame_descriptor(self, frame_index: int, frame_count: int) -> str:
        if self.active_domain == "frequency" and self.analyzer and self.analyzer.freq_axis is not None:
            freq_axis = np.asarray(self.analyzer.freq_axis)
            if 0 <= frame_index < freq_axis.shape[0]:
                return f"{frame_index + 1}/{frame_count} ({self._format_frequency_value(freq_axis[frame_index])})"
        return f"{frame_index + 1}/{frame_count}"

    def _heatmap_value_label(self) -> str:
        field_label = self._field_display_label(self.active_field)
        if self.active_domain != "frequency":
            return field_label

        display_mode = self.frequency_display_mode
        if display_mode == "magnitude":
            return f"Magnitude of {field_label}"
        if display_mode == "phase":
            return f"Phase of {field_label} (rad)"
        if display_mode == "real":
            return f"Real part of {field_label}"
        if display_mode == "imaginary":
            return f"Imaginary part of {field_label}"
        return field_label

    @staticmethod
    def _extract_display_frame(variable_data: np.ndarray, frame_index: int, domain: str, display_mode: str) -> np.ndarray:
        frame = variable_data[:, :, frame_index]
        if domain != "frequency":
            return np.asarray(frame)

        if display_mode == "phase":
            return np.angle(frame)
        if display_mode == "real":
            return np.real(frame)
        if display_mode == "imaginary":
            return np.imag(frame)
        return np.abs(frame)

    @staticmethod
    def _build_heatmap_color_norm(merged_values: np.ndarray, domain: str, display_mode: str):
        if domain == "frequency" and display_mode == "phase":
            return mcolors.Normalize(vmin=-np.pi, vmax=np.pi)

        data_min = float(np.min(merged_values))
        data_max = float(np.max(merged_values))
        if (
            not np.isfinite(data_min)
            or not np.isfinite(data_max)
            or data_max <= data_min
            or np.isclose(data_min, data_max)
        ):
            finite_values = merged_values[np.isfinite(merged_values)]
            reference = float(np.max(np.abs(finite_values))) if finite_values.size > 0 else 0.0
            if not np.isfinite(reference) or reference <= float(np.finfo(float).eps):
                return mcolors.Normalize(vmin=0.0, vmax=1.0)
            spread = reference * 0.1
            vmin_fb = data_min - spread if np.isfinite(data_min) else -spread
            vmax_fb = data_max + spread if np.isfinite(data_max) else spread
            if domain == "frequency" and display_mode == "magnitude":
                vmin_fb = max(0.0, vmin_fb)
            if not np.isfinite(vmin_fb) or not np.isfinite(vmax_fb) or vmax_fb <= vmin_fb:
                return mcolors.Normalize(vmin=0.0, vmax=max(1.0, reference))
            return mcolors.Normalize(vmin=vmin_fb, vmax=vmax_fb)

        positive_magnitudes = np.abs(merged_values)
        positive_magnitudes = positive_magnitudes[positive_magnitudes > 0.0]
        if positive_magnitudes.size == 0:
            if domain == "frequency" and display_mode == "magnitude":
                return mcolors.Normalize(vmin=0.0, vmax=data_max)
            return mcolors.Normalize(vmin=data_min, vmax=data_max)

        linthresh = max(
            float(np.percentile(positive_magnitudes, 5.0)),
            float(np.finfo(float).eps),
        )
        return mcolors.SymLogNorm(
            linthresh=linthresh,
            linscale=1.0,
            vmin=data_min,
            vmax=data_max,
            base=10,
        )

    def _update_animation_frame_label(self, frame_index: int, frame_count: int):
        if not self.animation_controller:
            return

        if self.active_domain == "frequency" and self.analyzer and self.analyzer.freq_axis is not None:
            freq_axis = np.asarray(self.analyzer.freq_axis)
            if 0 <= frame_index < freq_axis.shape[0]:
                self.animation_controller.frame_label.setText(
                    f"{frame_index + 1}/{frame_count} ({self._format_frequency_value(freq_axis[frame_index])})"
                )
                return

        self.animation_controller._set_frame_label(frame_index, frame_count)

    @staticmethod
    def _build_results_identity(snapshot_root: Path, version_name: str) -> str:
        try:
            resolved_root = snapshot_root.resolve()
        except Exception:
            resolved_root = snapshot_root
        return f"{resolved_root}|{version_name}"

    def _store_state(self):
        if not self.current_project_path:
            return

        metadata_path = self.current_project_path / "project_metadata.json"
        if not metadata_path.exists():
            return

        try:
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            metadata[self.selection_metadata_key] = list(self.selected_variables)
            metadata[self.active_metadata_key] = self.active_variable
            metadata[self.domain_metadata_key] = self.active_domain
            metadata[self.frequency_display_metadata_key] = self.frequency_display_mode
            metadata[self.cpml_overlay_metadata_key] = bool(self.show_cpml_overlay)

            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Saving Heatmap State Failed", str(e))

    def load_results(self, project_path: Path, archive_name: Optional[str] = None):
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
            if self._loaded_results_identity == requested_identity and self.current_figure is not None:
                self.current_project_path = snapshot_root
                self.active_version_name = selected_version
                if self.active_results_path is None:
                    self.active_results_path = snapshot_root / "Results"
                self._refresh_result_versions()
                if self.canvas_manager and self.canvas_manager.current_canvas is None:
                    self._display_figure(self.current_figure)
                return

            self._clear_current_plot()
            self._loaded_results_identity = None

            self.current_project_path = snapshot_root
            self.active_version_name = selected_version

            metadata = ResultsLoader.read_metadata(snapshot_root)
            if not metadata or "simulation_type" not in metadata:
                self._show_placeholder_message(
                    "No project metadata found for heatmap visualization."
                )
                return

            self.simulation_type = metadata.get("simulation_type", "").strip()
            self.polarization_mode = metadata.get("polarization_mode", "TE").strip()
            self.dimension = metadata.get("dimension", "2D").strip()
            cfg = metadata.get("solver_parameters", {})

            results_dir = snapshot_root / metadata.get("results_path", "Results")
            self.active_results_path = results_dir

            self.analyzer = Analyzer(
                results_dir,
                self.simulation_type,
                self.polarization_mode,
                self.dimension,
                cfg,
                selected_variables=None,
            )
            self.analyzer.load()
            self.domain_bounds = GeometryOverlayManager.load_domain_bounds(snapshot_root)
            self.geometry_rectangles = GeometryOverlayManager.load_geometry_rectangles(snapshot_root)
            self.measurement_surface_rectangles = (
                GeometryOverlayManager.load_measurement_surface_rectangles_from_results_metadata(results_dir)
            )
            self.cpml_rectangles = GeometryOverlayManager.load_cpml_rectangles(snapshot_root, self.domain_bounds)
            self.source_shapes = GeometryOverlayManager.load_source_shapes(snapshot_root)
            self.delta_x, self.num_cpml = GeometryOverlayManager.load_grid_params(snapshot_root)

            persisted_cpml_overlay = self._read_persisted_cpml_overlay(metadata)
            cpml_available = bool(self.cpml_rectangles)
            if persisted_cpml_overlay is None:
                self.show_cpml_overlay = cpml_available
            else:
                self.show_cpml_overlay = cpml_available and bool(persisted_cpml_overlay)

            persisted_domain = self._read_persisted_heatmap_domain(metadata)
            self.active_domain = persisted_domain or "time"

            persisted_frequency_display = self._read_persisted_frequency_display_mode(metadata)
            self.frequency_display_mode = persisted_frequency_display or "magnitude"

            cpml_blocker = QSignalBlocker(self.cpml_overlay_checkbox)
            self.cpml_overlay_checkbox.setEnabled(cpml_available)
            self.cpml_overlay_checkbox.setChecked(self.show_cpml_overlay)
            del cpml_blocker

            all_measurements = self.analyzer.get_measurement_point_info()
            self.surface_measurement_info = [
                mp_info
                for mp_info in all_measurements
                if str(getattr(mp_info, "point_type", "")).lower() == "surface"
            ]
            self.surface_variables = self._surface_variable_names_from_info(
                self.surface_measurement_info
            )

            if not self.surface_variables:
                self.variable_selector.set_variable_sources([], self.surface_measurement_info)
                self.variable_selector.populate([])
                self.active_variable_selector.clear()
                self.active_variable_selector.setEnabled(False)
                self._refresh_result_versions()
                self._show_placeholder_message(
                    "No measurement surfaces were found in this results set.\n"
                    "Add at least one surface measurement point and rerun the simulation."
                )
                return

            persisted_selection = self._read_persisted_selection(metadata)
            self.selected_variables = self._sanitize_selected_variables(
                persisted_selection
            )
            if not self.selected_variables:
                self.selected_variables = list(self.surface_variables)

            self.variable_selector.set_variable_sources([], self.surface_measurement_info)
            self.variable_selector.populate(self.selected_variables)

            persisted_active = self._read_persisted_active_variable(metadata)
            self._set_active_field_from_metadata(persisted_active)
            self._ensure_active_field()

            _persisted_field, persisted_surface = self._split_variable_name(persisted_active)
            if persisted_surface in self.selected_variables and self.active_field:
                self.active_variable = persisted_active
            elif self.selected_variables:
                self.active_variable = (
                    f"{self.active_field}_{self.selected_variables[0]}"
                    if self.active_field
                    else None
                )
            else:
                self.active_variable = None

            self._update_active_variable_selector()
            self._sync_heatmap_mode_controls()
            self._refresh_result_versions()
            self._store_state()
            self._render_active_heatmap()
            self._loaded_results_identity = requested_identity

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Loading Heatmap Results",
                f"Failed to load results:\n\n{str(e)}",
            )
        finally:
            self._is_loading_results = False

    def _update_active_variable_selector(self):
        blocker = QSignalBlocker(self.active_variable_selector)
        self.active_variable_selector.clear()
        available_fields = self._available_surface_fields()
        self.active_variable_selector.addItems(available_fields)

        if self.active_field in available_fields:
            self.active_variable_selector.setCurrentText(self.active_field)
        elif available_fields:
            self.active_field = available_fields[0]
            self.active_variable_selector.setCurrentText(self.active_field)
        else:
            self.active_field = None

        self.active_variable_selector.setEnabled(bool(available_fields))
        del blocker

    def _on_active_variable_changed(self, variable_name: str):
        if self._is_loading_results:
            return
        if variable_name == self.active_field:
            return

        self.active_field = variable_name or None
        self._store_state()
        self._render_active_heatmap()

    def _apply_variable_selection(self, selected: List[str]):
        if self._is_loading_results:
            return

        self.selected_variables = self._sanitize_selected_variables(selected)
        self.variable_selector.set_selected_variables(self.selected_variables)

        self._ensure_active_field()
        if self.selected_variables and self.active_field:
            self.active_variable = f"{self.active_field}_{self.selected_variables[0]}"
        else:
            self.active_variable = None

        self._update_active_variable_selector()
        self._store_state()
        self._render_active_heatmap()

    def _on_cpml_overlay_toggled(self, checked: bool):
        if self._is_loading_results:
            return

        self.show_cpml_overlay = bool(checked) and bool(self.cpml_rectangles)
        self._store_state()
        self._render_active_heatmap()

    def _on_domain_changed(self, _index: int):
        if self._is_loading_results:
            return

        domain = self._current_domain()
        if domain == self.active_domain:
            return

        self.active_domain = domain
        self._sync_heatmap_mode_controls()
        self._store_state()
        self._render_active_heatmap()

    def _on_frequency_display_changed(self, _index: int):
        if self._is_loading_results:
            return

        display_mode = self._current_frequency_display_mode()
        if display_mode == self.frequency_display_mode:
            return

        self.frequency_display_mode = display_mode
        self._sync_heatmap_mode_controls()
        self._store_state()
        if self.active_domain == "frequency":
            self._render_active_heatmap()

    @staticmethod
    def _normalize_surface_token(value: Optional[str]) -> str:
        if not value:
            return ""
        return "".join(ch for ch in str(value).lower() if ch.isalnum())

    def _lookup_surface_info(self, variable_name: str):
        token = self._normalize_surface_token(variable_name)
        for mp_info in self.surface_measurement_info:
            safe_name = str(getattr(mp_info, "safe_name", ""))
            display_name = str(getattr(mp_info, "name", ""))

            if safe_name == variable_name:
                return mp_info
            if token and (
                self._normalize_surface_token(safe_name) == token
                or self._normalize_surface_token(display_name) == token
            ):
                return mp_info
            if "_" in variable_name:
                _field_name, safe_name = variable_name.split("_", 1)
                if str(getattr(mp_info, "safe_name", "")) == safe_name:
                    return mp_info
        return None

    def _resolve_surface_probe_variable(self, field_name: str, surface_info) -> str:
        expected_key = f"{field_name}_{surface_info.safe_name}"
        if not self.analyzer or not self.analyzer.probe_data:
            return expected_key

        if expected_key in self.analyzer.probe_data:
            return expected_key

        field_token = self._normalize_surface_token(field_name)
        safe_token = self._normalize_surface_token(getattr(surface_info, "safe_name", ""))
        name_token = self._normalize_surface_token(getattr(surface_info, "name", ""))

        for probe_key in self.analyzer.probe_data.keys():
            if "_" not in probe_key:
                continue

            probe_field, probe_surface = probe_key.split("_", 1)
            if self._normalize_surface_token(probe_field) != field_token:
                continue

            probe_surface_token = self._normalize_surface_token(probe_surface)
            if probe_surface_token == safe_token or (
                name_token and probe_surface_token == name_token
            ):
                return probe_key

        return expected_key

    @staticmethod
    def _build_default_color_norm(merged_values: np.ndarray):
        lower_percentile, upper_percentile = HeatmapResultsWidget._DEFAULT_HEATMAP_PERCENTILES
        data_min = float(np.percentile(merged_values, lower_percentile))
        data_max = float(np.percentile(merged_values, upper_percentile))
        if (
            not np.isfinite(data_min)
            or not np.isfinite(data_max)
            or data_max <= data_min
            or np.isclose(data_min, data_max)
        ):
            return mcolors.Normalize(vmin=0.0, vmax=1.0)

        positive_magnitudes = np.abs(merged_values)
        positive_magnitudes = positive_magnitudes[positive_magnitudes > 0.0]
        if positive_magnitudes.size == 0:
            return mcolors.Normalize(vmin=data_min, vmax=data_max)

        linthresh = max(
            float(np.percentile(positive_magnitudes, 5.0)),
            float(np.finfo(float).eps),
        )
        return mcolors.SymLogNorm(
            linthresh=linthresh,
            linscale=1.0,
            vmin=data_min,
            vmax=data_max,
            base=10,
        )

    def _render_active_heatmap(self):
        self._render_generation += 1
        render_generation = self._render_generation
        self._clear_current_plot()

        self.active_domain = self._current_domain()
        if self.active_domain != "frequency":
            self.frequency_display_mode = self._current_frequency_display_mode()
        self._sync_heatmap_mode_controls()

        if not self.analyzer or not self.active_field:
            self._show_placeholder_message(
                "No heatmap field selected.\nUse the dropdown to choose Ex, Ey, or Hz."
            )
            self._disable_animation_controls()
            return

        data_source = self.analyzer.freq_data if self.active_domain == "frequency" else self.analyzer.probe_data
        if data_source is None:
            if self.active_domain == "frequency":
                self._show_placeholder_message("Frequency-domain surface data is unavailable in the analyzer.")
            else:
                self._show_placeholder_message("Surface data is unavailable in the analyzer.")
            self._disable_animation_controls()
            return

        plot_items = []
        for surface_variable in self.selected_variables:
            surface_info = self._lookup_surface_info(surface_variable)
            if surface_info is None:
                continue

            plot_variable = self._resolve_surface_probe_variable(
                self.active_field,
                surface_info,
            )
            variable_data = data_source.get(plot_variable)
            if variable_data is None or getattr(variable_data, "ndim", 0) != 3:
                continue

            plot_items.append((plot_variable, surface_info, variable_data))

        if not plot_items:
            self._show_placeholder_message(
                "Selected surface variables are unavailable in the loaded results."
            )
            self._disable_animation_controls()
            return

        frame_counts = [data.shape[2] for _, _, data in plot_items]
        if self.active_domain == "frequency" and self.analyzer.freq_axis is not None:
            frame_counts.append(len(self.analyzer.freq_axis))
        if not frame_counts or min(frame_counts) <= 0:
            self._show_placeholder_message(
                "Selected surface variables do not contain any renderable frames."
            )
            self._disable_animation_controls()
            return
        frame_count = min(frame_counts)
        self.frame_index = 0
        value_display_label = self._heatmap_value_label()

        fig = Figure(figsize=(9, 6), dpi=100)
        ax = fig.add_subplot(111)

        bad_color = "#00e5ff"
        cmap = plt.get_cmap(self._DEFAULT_HEATMAP_COLORMAP).copy()
        cmap.set_bad(color=bad_color)

        all_finite_values = []
        for _plot_variable, _surface_info, variable_data in plot_items:
            if self.active_domain == "frequency":
                if self.frequency_display_mode == "phase":
                    transformed = np.angle(variable_data)
                elif self.frequency_display_mode == "real":
                    transformed = np.real(variable_data)
                elif self.frequency_display_mode == "imaginary":
                    transformed = np.imag(variable_data)
                else:
                    transformed = np.abs(variable_data)
            else:
                transformed = np.asarray(variable_data)

            finite_values = transformed[np.isfinite(transformed)]
            if finite_values.size > 0:
                all_finite_values.append(finite_values)
        if not all_finite_values:
            self._show_placeholder_message(
                "Selected surface variables contain no finite values to display."
            )
            self._disable_animation_controls()
            return

        merged_values = np.concatenate(all_finite_values)
        color_norm = self._build_heatmap_color_norm(
            merged_values,
            self.active_domain,
            self.frequency_display_mode,
        )

        images: List = []
        current_frame_data: List[np.ndarray] = []
        plot_labels: List[str] = []
        has_meter_extent = False
        for plot_variable, surface_info, variable_data in plot_items:
            frame = self._extract_display_frame(
                variable_data,
                self.frame_index,
                self.active_domain,
                self.frequency_display_mode,
            )
            current_frame_data.append(variable_data)
            plot_labels.append(plot_variable)

            extent = None
            if surface_info and surface_info.metadata:
                grid_indices = surface_info.metadata.get("grid_indices")
                dx = self.delta_x
                if (
                    isinstance(grid_indices, dict)
                    and dx is not None
                    and dx > 0.0
                ):
                    x_idx = grid_indices.get("x")
                    y_idx = grid_indices.get("y")
                    if (
                        isinstance(x_idx, list) and len(x_idx) > 0
                        and isinstance(y_idx, list) and len(y_idx) > 0
                    ):
                        extent = [
                            (min(x_idx) - 0.5) * dx,
                            (max(x_idx) + 0.5) * dx,
                            (min(y_idx) - 0.5) * dx,
                            (max(y_idx) + 0.5) * dx,
                        ]

                if extent is None:
                    x0 = surface_info.metadata.get("x_start_meters")
                    x1 = surface_info.metadata.get("x_end_meters")
                    y0 = surface_info.metadata.get("y_start_meters")
                    y1 = surface_info.metadata.get("y_end_meters")
                    if all(v is not None for v in [x0, x1, y0, y1]):
                        x_min = min(float(x0), float(x1))
                        x_max = max(float(x0), float(x1))
                        y_min = min(float(y0), float(y1))
                        y_max = max(float(y0), float(y1))
                        extent = [x_min, x_max, y_min, y_max]

            if extent is None and self.domain_bounds is not None:
                x_min, x_max, y_min, y_max = self.domain_bounds
                extent = [x_min, x_max, y_min, y_max]

            frame_masked = np.ma.masked_invalid(frame.T)
            image = ax.imshow(
                frame_masked,
                origin="lower",
                extent=extent,
                aspect="auto",
                cmap=cmap,
                norm=color_norm,
            )
            images.append(image)

            if self.domain_bounds is not None and extent is not None:
                x_min, x_max, y_min, y_max = self.domain_bounds
                ax.set_xlim(x_min, x_max)
                ax.set_ylim(y_min, y_max)
            if extent is not None:
                has_meter_extent = True

        colorbar = fig.colorbar(
            images[-1],
            ax=ax,
            shrink=0.9,
            pad=0.03,
            fraction=0.05,
            label=value_display_label,
        )
        colorbar.ax.yaxis.labelpad = 10
        if not (self.active_domain == "frequency" and self.frequency_display_mode == "phase"):
            def format_scientific(x, pos):
                if x == 0:
                    return '0'
                s = f'{x:.0e}'
                # Remove leading zeros and + from exponent: e+03 -> e3, e-03 -> e-3
                import re
                return re.sub(r'e([+-]?)0*([1-9]\d*)', lambda m: f'e{m.group(1) if m.group(1) == "-" else ""}{m.group(2)}', s)
            colorbar.ax.yaxis.set_major_formatter(FuncFormatter(format_scientific))

        overlay_rectangles = self.geometry_rectangles + self.measurement_surface_rectangles
        if self.show_cpml_overlay:
            overlay_rectangles += self.cpml_rectangles

        for rect in overlay_rectangles:
            GeometryOverlayManager.add_geometry_patch(ax, rect)

        if self.show_cpml_overlay and self.cpml_rectangles:
            cpml_inner_bounds = GeometryOverlayManager.compute_cpml_inner_bounds(
                self.cpml_rectangles,
                self.domain_bounds,
            )
            if cpml_inner_bounds is not None:
                x0, x1, y0, y1 = cpml_inner_bounds
                cpml_rgb = tuple(v / 255.0 for v in CPML_OVERLAY_COLOR[:3])
                interior_border = MplRectangle(
                    (x0, y0),
                    x1 - x0,
                    y1 - y0,
                    linewidth=1.8,
                    edgecolor=(cpml_rgb[0], cpml_rgb[1], cpml_rgb[2], 0.85),
                    facecolor=(0.0, 0.0, 0.0, 0.0),
                    zorder=5,
                )
                ax.add_patch(interior_border)

        has_source_point, has_source_line = GeometryOverlayManager.add_source_overlays(
            ax, self.source_shapes, self.delta_x, self.num_cpml
        )

        legend_handles = []
        if has_source_point or has_source_line:
            legend_handles.append(
                Line2D(
                    [],
                    [],
                    color=SOURCE_LEGEND_COLOR,
                    marker="o",
                    linestyle="-",
                    markerfacecolor=SOURCE_LEGEND_COLOR,
                    markeredgecolor="black",
                    linewidth=2.0,
                    markersize=5,
                    label="Source",
                )
            )
        legend_handles.extend(GeometryOverlayManager.build_waveguide_legend_handles(self.geometry_rectangles))
        if self.show_cpml_overlay and self.cpml_rectangles:
            cpml_rgb = tuple(v / 255.0 for v in CPML_OVERLAY_COLOR[:3])
            legend_handles.append(
                Line2D(
                    [],
                    [],
                    color=(cpml_rgb[0], cpml_rgb[1], cpml_rgb[2], 0.8),
                    linewidth=1.8,
                    label="CPML",
                )
            )
        if legend_handles:
            ax.legend(handles=legend_handles, loc="upper right", framealpha=0.9)

        axis_in_meters = self.domain_bounds is not None or has_meter_extent
        ax.set_xlabel(
            "Horizontal Position, x (m)"
            if axis_in_meters
            else "Horizontal Grid Index (cell)"
        )
        ax.set_ylabel(
            "Vertical Position, y (m)"
            if axis_in_meters
            else "Vertical Grid Index (cell)"
        )
        ax.set_title(
            f"{self.simulation_type}: {value_display_label} across {len(plot_items)} surface(s) "
            f"({self._frame_descriptor(self.frame_index, frame_count)})"
        )

        # Keep a small right margin so colorbar label/ticks are not clipped.
        fig.tight_layout(rect=(0.0, 0.0, 0.96, 1.0))

        if render_generation != self._render_generation:
            plt.close(fig)
            return

        self.current_surface_data = current_frame_data[0]
        self.current_surface_data_list = current_frame_data
        self.current_surface_extent = None
        self.current_axes = [ax]
        self.current_images = images
        self.current_plot_labels = plot_labels
        self.current_ax = ax
        self.current_image = images[0]
        self._configure_animation_controls(frame_count)

        if not self._display_figure(fig, render_generation):
            plt.close(fig)
            return
        self.current_figure = fig
        self.active_variable = plot_items[0][0]
        self._update_frame(self.frame_index)

    def _configure_animation_controls(self, frame_count: int):
        if not self.animation_controller:
            return

        max_frame = max(0, frame_count - 1)
        self.animation_controller.frame_index = int(min(self.frame_index, max_frame))
        self.animation_controller.configure_for_data(self.current_surface_data_list)

    def _disable_animation_controls(self):
        if self.animation_controller:
            self.animation_controller.disable_controls()

    def _on_frame_slider_changed(self, frame_index: int):
        self.frame_index = int(frame_index)
        self._update_frame(self.frame_index)

    def _toggle_animation(self, playing: bool):
        if self.animation_controller:
            self.animation_controller.toggle_animation(playing)

    def _update_frame(self, frame_index: int):
        if not self.current_surface_data_list or not self.current_images or not self.current_axes:
            return

        frame_count = min(data.shape[2] for data in self.current_surface_data_list)
        if frame_count <= 0:
            return
        frame_index = max(0, min(frame_index, frame_count - 1))
        for index, variable_data in enumerate(self.current_surface_data_list):
            if index >= len(self.current_images):
                continue
            frame_data = self._extract_display_frame(
                variable_data,
                frame_index,
                self.active_domain,
                self.frequency_display_mode,
            )
            self.current_images[index].set_data(np.ma.masked_invalid(frame_data.T))

        if self.current_axes:
            value_display_label = self._heatmap_value_label()
            self.current_axes[0].set_title(
                f"{self.simulation_type}: {value_display_label} across {len(self.current_surface_data_list)} surface(s) "
                f"({self._frame_descriptor(frame_index, frame_count)})"
            )
        self._update_animation_frame_label(frame_index, frame_count)

        if self.canvas_manager and self.canvas_manager.current_canvas:
            self.canvas_manager.current_canvas.draw()

    def _display_figure(self, figure: Figure, render_generation: Optional[int] = None) -> bool:
        if render_generation is not None and render_generation != self._render_generation:
            return False

        self.canvas_manager.cleanup()

        if self.placeholder_label:
            self.placeholder_label.hide()

        canvas, toolbar = self.canvas_manager.create_canvas(figure, self)

        if render_generation is not None and render_generation != self._render_generation:
            self.canvas_manager.cleanup()
            return False

        self._resize_canvas_to_viewport(figure=figure, force_draw=True)
        self._schedule_resize_canvas_to_viewport()
        return True

    def _schedule_resize_canvas_to_viewport(self):
        if self._resize_update_pending:
            return

        self._resize_update_pending = True

        def _run_resize():
            self._resize_update_pending = False
            self._resize_canvas_to_viewport()

        QTimer.singleShot(0, _run_resize)

    def _resize_canvas_to_viewport(self, figure: Optional[Figure] = None, force_draw: bool = False):
        if not self.canvas_manager or not self.canvas_manager.current_canvas:
            return

        active_figure = figure or self.current_figure
        if active_figure is None:
            return

        toolbar_h = 0
        if self.canvas_manager.current_toolbar is not None:
            toolbar_h = self.canvas_manager.current_toolbar.sizeHint().height()

        viewport = self.scroll_area.viewport().size()
        target_w = max(1, viewport.width() - 8)
        target_h = max(1, viewport.height() - toolbar_h - 12)

        active_figure.set_size_inches(
            target_w / active_figure.dpi,
            target_h / active_figure.dpi,
            forward=True,
        )

        canvas = self.canvas_manager.current_canvas
        canvas.setMinimumSize(target_w, target_h)
        canvas.resize(target_w, target_h)
        self.canvas_container.resize(target_w, target_h + toolbar_h + 8)
        self.canvas_container.setMinimumSize(target_w, target_h + toolbar_h + 8)

        if force_draw:
            canvas.draw()
        else:
            canvas.draw_idle()

    def _clear_current_plot(self):
        if self.animation_controller:
            self.animation_controller.stop_animation()
        self.canvas_manager.cleanup()
        if self.current_figure is not None:
            try:
                plt.close(self.current_figure)
            except Exception:
                pass
            self.current_figure = None
        self.current_surface_data = None
        self.current_surface_extent = None
        self.current_ax = None
        self.current_image = None
        self.current_surface_data_list = []
        self.current_axes = []
        self.current_images = []
        self.current_plot_labels = []

    def cleanup_canvas(self):
        self._clear_current_plot()
        self._loaded_results_identity = None

    def invalidate_loaded_results_cache(self):
        """Mark cached load identity stale so the next load_results call reloads data."""
        self._loaded_results_identity = None

    def hideEvent(self, event):
        super().hideEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
        self._schedule_resize_canvas_to_viewport()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._schedule_resize_canvas_to_viewport()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.WindowStateChange:
            self._schedule_resize_canvas_to_viewport()

    def eventFilter(self, watched, event):
        if watched is self.scroll_area.viewport() and event.type() == QEvent.Resize:
            self._schedule_resize_canvas_to_viewport()
        return super().eventFilter(watched, event)

    def clear(self):
        self._clear_current_plot()
        self.project_root_path = None
        self.current_project_path = None
        self.active_results_path = None
        self.active_version_name = "Current"
        self._loaded_results_identity = None
        self.analyzer = None
        self.domain_bounds = None
        self.surface_measurement_info = []
        self.surface_variables = []
        self.selected_variables = []
        self.active_variable = None
        self.active_field = None
        self.geometry_rectangles = []
        self.measurement_surface_rectangles = []
        self.source_shapes = []
        self.cpml_rectangles = []
        self.delta_x = None
        self.num_cpml = None
        self.show_cpml_overlay = False
        self.active_domain = "time"
        self.frequency_display_mode = "magnitude"

        cpml_blocker = QSignalBlocker(self.cpml_overlay_checkbox)
        self.cpml_overlay_checkbox.setChecked(False)
        self.cpml_overlay_checkbox.setEnabled(False)
        del cpml_blocker

        self._disable_animation_controls()

        self.variable_selector.set_variable_sources([], [])
        self.variable_selector.populate([])
        self.variable_selector.version_selector.clear()
        self.variable_selector.version_selector.addItem("Current")
        self.variable_selector.version_selector.setEnabled(False)
        self.active_variable_selector.clear()
        self.active_variable_selector.setEnabled(False)
        self._sync_heatmap_mode_controls()
        self.ref_panel.setHtml(self._default_reference_html())

        self._show_placeholder_message(
            "No heatmap results loaded.\nRun a simulation and open Heatmap View."
        )
