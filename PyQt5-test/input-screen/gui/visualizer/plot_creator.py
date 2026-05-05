"""
Abstract base class for plot creation strategies
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple, Optional
from matplotlib.figure import Figure


class PlotCreator(ABC):
    """
    Abstract strategy for creating visualization plots from simulation results
    """

    def __init__(
        self,
        project_path: Path,
        results_dir: Optional[Path] = None,
        default_export_path: Optional[Path] = None,
    ):
        """
        Initialize plot creator

        Args:
            project_path: Path to project directory (containing project_metadata.json)
            default_export_path: Default path for exporting plots
        """
        self.project_path = Path(project_path)
        self.results_path = Path(results_dir) if results_dir else self.project_path / "Results"
        self.default_export_path = default_export_path or self.results_path
        self.results = {}
        self.metadata = None
        self.simulation_config = None

    @abstractmethod
    def load_results(self):
        """
        Load specific result files needed for this plot type.
        Subclasses must implement this to load their required files.
        """
        pass

    @abstractmethod
    def create_plots(self) -> List[Tuple[str, Figure]]:
        """
        Create matplotlib figures for visualization

        Returns:
            List of (title, figure) tuples for display in ResultsWidget
        """
        pass

    def export(self, figure: Figure, filename: str, dpi: int = 150):
        """
        Export a figure to file

        Args:
            figure: Matplotlib figure to export
            filename: Output filename
            dpi: Resolution for export
        """
        output_path = self.default_export_path / filename
        figure.savefig(output_path, dpi=dpi, bbox_inches="tight")
        print(f"Exported plot to {output_path}")
