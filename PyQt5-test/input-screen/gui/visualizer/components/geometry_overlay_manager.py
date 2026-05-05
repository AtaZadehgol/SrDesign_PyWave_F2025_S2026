"""Geometry and overlay management for heatmap rendering."""

import json
from pathlib import Path
from typing import List, Optional, Tuple

from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle as MplRectangle


# Default colors for overlays
CPML_OVERLAY_COLOR = [125, 165, 250, 255]
SOURCE_LEGEND_COLOR = "#e53935"


class GeometryOverlayManager:
    """Manages loading and rendering of geometry and overlay elements for heatmaps."""

    @staticmethod
    def load_geometry_rectangles(project_root: Path) -> List[dict]:
        """Load geometry rectangles directly from the project config.

        Args:
            project_root: Path to project root directory

        Returns:
            List of geometry rectangle definitions
        """
        return GeometryOverlayManager.load_geometry_rectangles_from_config(project_root)

    @staticmethod
    def load_geometry_rectangles_from_config(project_root: Path) -> List[dict]:
        """Load geometry rectangle list directly from simulation_config.json.

        Args:
            project_root: Path to project root directory

        Returns:
            List of geometry rectangle definitions
        """
        config_path = project_root / "simulation_config.json"
        if not config_path.exists():
            return []

        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except Exception:
            return []

        geometry = config.get("geometry", {})
        rectangles = geometry.get("rectangles", [])
        if isinstance(rectangles, list):
            normalized_rectangles = []
            for rect in rectangles:
                if isinstance(rect, dict):
                    copied = dict(rect)
                    # Canvas export stores y as a top-edge anchor.
                    copied["_y_anchor"] = "top"
                    normalized_rectangles.append(copied)
            return normalized_rectangles
        return []

    @staticmethod
    def load_domain_bounds(project_root: Path) -> Optional[tuple]:
        """Read simulation editor domain bounds from simulation_config.json.

        Args:
            project_root: Path to project root directory

        Returns:
            Tuple of (x_min, x_max, y_min, y_max) or None if not found
        """
        config_path = project_root / "simulation_config.json"
        if not config_path.exists():
            return None

        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except Exception:
            return None

        geometry = config.get("geometry", {})
        grid_dimensions = geometry.get("grid_dimensions", {})
        domain_width = grid_dimensions.get("domain_width")
        domain_height = grid_dimensions.get("domain_height")

        try:
            width = float(domain_width)
            height = float(domain_height)
        except (TypeError, ValueError):
            return None

        if width <= 0.0 or height <= 0.0:
            return None

        return (0.0, width, 0.0, height)

    @staticmethod
    def load_grid_params(project_root: Path) -> tuple:
        """Read delta_x and num_cpml from simulation_config.json.

        Args:
            project_root: Path to project root directory

        Returns:
            Tuple of (delta_x, num_cpml) where each is the value or None if
            not found.  delta_x is in meters.
        """
        config_path = project_root / "simulation_config.json"
        if not config_path.exists():
            return (None, None)

        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except Exception:
            return (None, None)

        geometry = config.get("geometry", {})
        grid_spacing = geometry.get("grid_spacing", {})
        advanced = config.get("advanced_parameters", {})

        delta_x = grid_spacing.get("delta_x")
        num_cpml = advanced.get("num_cpml")

        try:
            dx = float(delta_x)
            dx = dx if dx > 0.0 else None
        except (TypeError, ValueError):
            dx = None

        try:
            nc = int(num_cpml)
            nc = nc if nc >= 0 else None
        except (TypeError, ValueError):
            nc = None

        return (dx, nc)

    @staticmethod
    def load_source_shapes(project_root: Path) -> List[dict]:
        """Load source point/line definitions from simulation_config.json.

        Args:
            project_root: Path to project root directory

        Returns:
            List of source shape definitions
        """
        config_path = project_root / "simulation_config.json"
        if not config_path.exists():
            return []

        try:
            with open(config_path, "r") as f:
                config = json.load(f)
        except Exception:
            return []

        sources = config.get("sources", [])
        if isinstance(sources, list):
            return [src for src in sources if isinstance(src, dict)]
        return []

    @staticmethod
    def load_cpml_rectangles(
        project_root: Path,
        domain_bounds: Optional[tuple],
    ) -> List[dict]:
        """Load CPML border overlay rectangles from simulation config or metadata.

        Args:
            project_root: Path to project root directory
            domain_bounds: Tuple of (x_min, x_max, y_min, y_max) or None

        Returns:
            List of CPML rectangle definitions
        """
        if domain_bounds is None:
            return []

        cpml_cells = None
        dx = None
        dy = None

        config_path = project_root / "simulation_config.json"
        if config_path.exists():
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
            except Exception:
                config = {}

            advanced = config.get("advanced_parameters", {}) if isinstance(config, dict) else {}
            geometry = config.get("geometry", {}) if isinstance(config, dict) else {}
            grid_spacing = geometry.get("grid_spacing", {}) if isinstance(geometry, dict) else {}

            cpml_cells = advanced.get("num_cpml") if isinstance(advanced, dict) else None
            dx = grid_spacing.get("delta_x") if isinstance(grid_spacing, dict) else None
            dy = grid_spacing.get("delta_y") if isinstance(grid_spacing, dict) else None

        if cpml_cells is None:
            metadata_path = project_root / "project_metadata.json"
            if metadata_path.exists():
                try:
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                except Exception:
                    metadata = {}

                cpml = metadata.get("cpml", {}) if isinstance(metadata, dict) else {}
                cpml_cells = cpml.get("num_cpml") if isinstance(cpml, dict) else None

        try:
            cpml_cells = int(cpml_cells)
            dx = float(dx)
            dy = float(dy)
        except (TypeError, ValueError):
            return []

        if cpml_cells <= 0 or dx <= 0.0 or dy <= 0.0:
            return []

        x_min, x_max, y_min, y_max = domain_bounds
        domain_width = x_max - x_min
        domain_height = y_max - y_min
        cpml_width = cpml_cells * dx
        cpml_height = cpml_cells * dy

        if cpml_width <= 0.0 or cpml_height <= 0.0:
            return []
        if cpml_width * 2.0 >= domain_width or cpml_height * 2.0 >= domain_height:
            return []

        interior_x_min = x_min + cpml_width
        interior_x_max = x_max - cpml_width
        interior_y_min = y_min + cpml_height
        interior_y_max = y_max - cpml_height

        return [
            {
                "name": "CPML Left",
                "position": {"x": x_min, "y": y_min},
                "dimensions": {"width": cpml_width, "height": domain_height},
                "color": CPML_OVERLAY_COLOR,
                "_overlay_face_alpha": 0.25,
                "_overlay_edge_alpha": 0.0,
                "_overlay_linewidth": 1.5,
            },
            {
                "name": "CPML Right",
                "position": {"x": interior_x_max, "y": y_min},
                "dimensions": {"width": cpml_width, "height": domain_height},
                "color": CPML_OVERLAY_COLOR,
                "_overlay_face_alpha": 0.25,
                "_overlay_edge_alpha": 0.0,
                "_overlay_linewidth": 1.5,
            },
            {
                "name": "CPML Bottom",
                "position": {"x": interior_x_min, "y": y_min},
                "dimensions": {"width": interior_x_max - interior_x_min, "height": cpml_height},
                "color": CPML_OVERLAY_COLOR,
                "_overlay_face_alpha": 0.25,
                "_overlay_edge_alpha": 0.0,
                "_overlay_linewidth": 1.5,
            },
            {
                "name": "CPML Top",
                "position": {"x": interior_x_min, "y": interior_y_max},
                "dimensions": {"width": interior_x_max - interior_x_min, "height": cpml_height},
                "color": CPML_OVERLAY_COLOR,
                "_overlay_face_alpha": 0.25,
                "_overlay_edge_alpha": 0.0,
                "_overlay_linewidth": 1.5,
            },
        ]

    @staticmethod
    def compute_cpml_inner_bounds(
        cpml_rectangles: List[dict],
        domain_bounds: Optional[tuple],
    ) -> Optional[tuple]:
        """Compute the interior (non-CPML) bounds from CPML strips and domain bounds.

        Args:
            cpml_rectangles: List of CPML rectangle definitions
            domain_bounds: Tuple of (x_min, x_max, y_min, y_max) or None

        Returns:
            Tuple of interior bounds or None
        """
        if not cpml_rectangles or domain_bounds is None:
            return None

        x_min, x_max, y_min, y_max = domain_bounds
        left_width = 0.0
        right_width = 0.0
        bottom_height = 0.0
        top_height = 0.0

        for rect in cpml_rectangles:
            name = str(rect.get("name", "")).strip().lower()
            dimensions = rect.get("dimensions", {})
            if not isinstance(dimensions, dict):
                continue

            try:
                width = float(dimensions.get("width", 0.0))
                height = float(dimensions.get("height", 0.0))
            except (TypeError, ValueError):
                continue

            if name == "cpml left":
                left_width = width
            elif name == "cpml right":
                right_width = width
            elif name == "cpml bottom":
                bottom_height = height
            elif name == "cpml top":
                top_height = height

        interior_x_min = x_min + left_width
        interior_x_max = x_max - right_width
        interior_y_min = y_min + bottom_height
        interior_y_max = y_max - top_height

        if interior_x_max <= interior_x_min or interior_y_max <= interior_y_min:
            return None

        return (interior_x_min, interior_x_max, interior_y_min, interior_y_max)

    @staticmethod
    def load_geometry_rectangles_from_results_metadata(
        results_dir: Optional[Path],
    ) -> List[dict]:
        """Parse geometry overlays from metadata_*.json files in Results/.

        Args:
            results_dir: Path to Results directory

        Returns:
            List of geometry rectangles from metadata files
        """
        if results_dir is None:
            return []

        overlays: List[dict] = []
        for metadata_path in sorted(Path(results_dir).glob("metadata_*.json")):
            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
            except Exception:
                continue

            overlay = GeometryOverlayManager.build_overlay_from_metadata(metadata)
            if overlay is not None:
                overlays.append(overlay)

        return overlays

    @staticmethod
    def load_measurement_surface_rectangles_from_results_metadata(
        results_dir: Optional[Path],
    ) -> List[dict]:
        """Parse measurement-surface overlays from metadata_*.json files in Results/.

        Args:
            results_dir: Path to Results directory

        Returns:
            List of measurement surface rectangles from metadata files
        """
        if results_dir is None:
            return []

        overlays: List[dict] = []
        for metadata_path in sorted(Path(results_dir).glob("metadata_*.json")):
            try:
                with open(metadata_path, "r") as f:
                    metadata = json.load(f)
            except Exception:
                continue

            overlay = GeometryOverlayManager.build_overlay_from_metadata(
                metadata, include_measurement=True
            )
            if overlay is not None:
                overlays.append(overlay)

        return overlays

    @staticmethod
    def build_overlay_from_metadata(
        metadata: dict,
        include_measurement: bool = False,
    ) -> Optional[dict]:
        """Convert a metadata entry into rectangle overlay format when possible.

        Args:
            metadata: Metadata dictionary
            include_measurement: Whether to include measurement overlays

        Returns:
            Overlay rectangle dictionary or None
        """
        if not isinstance(metadata, dict):
            return None

        name = str(metadata.get("name", "")).strip()
        if not include_measurement and name.lower().startswith("measurement"):
            return None

        position = metadata.get("position", {})
        dimensions = metadata.get("dimensions", {})
        x = position.get("x") if isinstance(position, dict) else None
        y = position.get("y") if isinstance(position, dict) else None
        width = dimensions.get("width") if isinstance(dimensions, dict) else None
        height = dimensions.get("height") if isinstance(dimensions, dict) else None

        if None in (x, y, width, height):
            x = metadata.get("x_meters", metadata.get("x"))
            y = metadata.get("y_meters", metadata.get("y"))
            width = metadata.get("width_meters", metadata.get("width"))
            height = metadata.get("height_meters", metadata.get("height"))

        if None in (x, y, width, height):
            x0 = metadata.get("x_start_meters")
            x1 = metadata.get("x_end_meters")
            y0 = metadata.get("y_start_meters")
            y1 = metadata.get("y_end_meters")
            if None in (x0, x1, y0, y1):
                return None
            x = min(float(x0), float(x1))
            y = min(float(y0), float(y1))
            width = abs(float(x1) - float(x0))
            height = abs(float(y1) - float(y0))

        try:
            x = float(x)
            y = float(y)
            width = float(width)
            height = float(height)
        except (TypeError, ValueError):
            return None

        if width <= 0.0 or height <= 0.0:
            return None

        return {
            "position": {"x": x, "y": y},
            "dimensions": {"width": width, "height": height},
            "color": metadata.get("color", [255, 255, 255, 120]),
            "name": name,
        }

    @staticmethod
    def add_geometry_patch(ax, rect: dict):
        """Add a geometry rectangle patch to matplotlib axes.

        Args:
            ax: Matplotlib axes
            rect: Rectangle definition
        """
        geometry = GeometryOverlayManager.extract_rect_plot_geometry(rect)
        if geometry is None:
            return

        x, y, width, height = geometry
        rgb = GeometryOverlayManager.extract_rect_rgb(rect)
        edge_alpha = float(rect.get("_overlay_edge_alpha", 0.95))
        face_alpha = float(rect.get("_overlay_face_alpha", 0.03))
        linewidth = float(rect.get("_overlay_linewidth", 1.8))

        patch = MplRectangle(
            (x, y),
            width,
            height,
            linewidth=linewidth,
            edgecolor=(rgb[0], rgb[1], rgb[2], edge_alpha),
            facecolor=(rgb[0], rgb[1], rgb[2], face_alpha),
            zorder=4,
        )
        ax.add_patch(patch)

    @staticmethod
    def extract_rect_plot_geometry(rect: dict) -> Optional[tuple]:
        """Resolve rectangle geometry in plot coordinates (meters).

        Args:
            rect: Rectangle definition

        Returns:
            Tuple of (x, y, width, height) or None if invalid
        """
        position = rect.get("position", {})
        dimensions = rect.get("dimensions", {})
        x = position.get("x") if isinstance(position, dict) else None
        y = position.get("y") if isinstance(position, dict) else None
        width = dimensions.get("width") if isinstance(dimensions, dict) else None
        height = dimensions.get("height") if isinstance(dimensions, dict) else None

        if None in (x, y, width, height):
            x = rect.get("x", rect.get("grid_x"))
            y = rect.get("y", rect.get("grid_y"))
            width = rect.get("width", rect.get("grid_width"))
            height = rect.get("height", rect.get("grid_height"))

        if None in (x, y, width, height):
            x0 = rect.get("x_start_meters")
            x1 = rect.get("x_end_meters")
            y0 = rect.get("y_start_meters")
            y1 = rect.get("y_end_meters")
            if None not in (x0, x1, y0, y1):
                x = min(float(x0), float(x1))
                y = min(float(y0), float(y1))
                width = abs(float(x1) - float(x0))
                height = abs(float(y1) - float(y0))

        if None in (x, y, width, height):
            return None

        try:
            x = float(x)
            y = float(y)
            width = float(width)
            height = float(height)
        except (TypeError, ValueError):
            return None

        if width <= 0.0 or height <= 0.0:
            return None

        if rect.get("_y_anchor") == "top":
            y = y - height

        return (x, y, width, height)

    @staticmethod
    def extract_rect_rgb(rect: dict) -> Tuple[float, float, float]:
        """Extract normalized RGB color from rectangle definition.

        Args:
            rect: Rectangle definition

        Returns:
            Tuple of (r, g, b) normalized to 0-1 range
        """
        raw_color = rect.get("color", [255, 255, 255, 120])
        if not isinstance(raw_color, (list, tuple)) or len(raw_color) < 3:
            raw_color = [255, 255, 255, 120]
        return tuple(max(0, min(255, int(v))) / 255.0 for v in raw_color[:3])

    @staticmethod
    def build_waveguide_legend_handles(rectangles: List[dict]) -> List[Line2D]:
        """Create one legend handle per unique waveguide rectangle.

        Args:
            rectangles: List of rectangle definitions

        Returns:
            List of matplotlib Line2D legend handles
        """
        handles: List[Line2D] = []
        seen = set()
        unnamed_count = 0

        for rect in rectangles:
            geometry = GeometryOverlayManager.extract_rect_plot_geometry(rect)
            if geometry is None:
                continue

            rgb = GeometryOverlayManager.extract_rect_rgb(rect)
            x, y, width, height = geometry
            key = (
                round(x, 15),
                round(y, 15),
                round(width, 15),
                round(height, 15),
                round(rgb[0], 4),
                round(rgb[1], 4),
                round(rgb[2], 4),
            )
            if key in seen:
                continue
            seen.add(key)

            name = str(rect.get("name", "")).strip()

            if not name:
                unnamed_count += 1
                name = f"Waveguide {unnamed_count}"

            handles.append(
                Line2D(
                    [],
                    [],
                    color=(rgb[0], rgb[1], rgb[2], 0.95),
                    linewidth=1.8,
                    label=name,
                )
            )

        return handles

    @staticmethod
    def add_source_overlays(
        ax,
        source_shapes: List[dict],
        delta_x: Optional[float] = None,
        num_cpml: Optional[int] = None,
    ) -> Tuple[bool, bool]:
        """Draw source points/lines on top of heatmap.

        Args:
            ax: Matplotlib axes
            source_shapes: List of source shape definitions
            delta_x: Grid cell size in meters.  When provided together with
                num_cpml the source coordinates are snapped to the nearest grid
                cell centre so they match the field data exactly.
            num_cpml: Number of CPML cells on each side of the domain.

        Returns:
            Tuple of (has_point, has_line) booleans
        """
        has_point = False
        has_line = False

        snap = delta_x is not None and num_cpml is not None and delta_x > 0.0

        def _snap(coord: float) -> float:
            """Snap a full-domain metre coordinate to grid-cell centre."""
            cell = int((coord - num_cpml * delta_x) / delta_x)
            return (cell + num_cpml) * delta_x

        for source in source_shapes:
            try:
                x0 = float(source.get("x"))
                y0 = float(source.get("y"))
            except (TypeError, ValueError):
                continue

            if snap:
                x0 = _snap(x0)
                y0 = _snap(y0)

            rgb = (229 / 255.0, 57 / 255.0, 53 / 255.0)

            shape = str(source.get("shape", "Point")).lower()
            xend = source.get("xend")
            yend = source.get("yend")

            is_line = (
                shape == "line"
                or (xend is not None and yend is not None)
            )

            if is_line:
                has_line = True
                try:
                    x1 = float(xend if xend is not None else x0)
                    y1 = float(yend if yend is not None else y0)
                except (TypeError, ValueError):
                    x1, y1 = x0, y0

                if snap:
                    x1 = _snap(x1)
                    y1 = _snap(y1)

                ax.plot(
                    [x0, x1],
                    [y0, y1],
                    color=rgb,
                    linewidth=2.0,
                    zorder=6,
                    alpha=0.95,
                )
                ax.scatter([x0, x1], [y0, y1], s=36, c=[rgb], edgecolors="black", zorder=7)
            else:
                has_point = True
                ax.scatter([x0], [y0], s=56, c=[rgb], edgecolors="black", zorder=7)

        return has_point, has_line
