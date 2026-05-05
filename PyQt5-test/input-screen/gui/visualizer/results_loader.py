"""
Results loading and strategy selection
"""

import json
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QWidget
from pathlib import Path
from typing import List, Optional

from .plot_creator import PlotCreator
from .wave_impedance_strategy import DynamicAnalysisStrategy, WaveImpedanceStrategy


class ResultsLoader:
    """Handles loading results and selecting visualization strategies"""

    @staticmethod
    def read_metadata(project_or_results_path: Path) -> Optional[dict]:
        """
        Read project_metadata.json from project directory

        Args:
            project_or_results_path: Path to project directory or Results subdirectory

        Returns:
            Dictionary with metadata, or None if not found
        """
        project_path = Path(project_or_results_path)

        if project_path.name == "Results":
            project_path = project_path.parent

        metadata_file_path = project_path / "project_metadata.json"
        if metadata_file_path.exists():
            with open(metadata_file_path, "r") as f:
                return json.load(f)
        else:
            return None

    @staticmethod
    def open_load_dialog(parent: QWidget) -> Optional[Path]:
        """
        Open file dialog to select a project directory.

        Args:
            parent: Parent widget for dialogs

        Returns:
            Path to the selected project directory, or None if cancelled

        Raises:
            FileNotFoundError: If the selected directory has no project_metadata.json
        """
        selected_dir = QFileDialog.getExistingDirectory(
            parent,
            "Select Project Directory (containing project_metadata.json and Results/)",
            "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks,
        )

        if not selected_dir:
            return None

        project_path = Path(selected_dir)

        metadata = ResultsLoader.read_metadata(project_path)
        if not metadata:
            raise FileNotFoundError(
                f"No project_metadata.json found in {project_path}. Please select a valid project directory."
            )

        return project_path

    @staticmethod
    def create_strategy(
        project_path: Path,
        simulation_type: str,
        results_dir: Optional[Path] = None,
        selected_variables: Optional[List[str]] = None,
    ) -> Optional[PlotCreator]:
        """
        Create appropriate visualization strategy for simulation type

        Args:
            project_path: Path to results directory
            simulation_type: Type of simulation

        Returns:
            PlotCreator strategy instance or None if type not recognized
        """
        # Use the shared dynamic analyzer for all simulation types.
        return DynamicAnalysisStrategy(
            project_path,
            results_dir=results_dir,
            selected_variables=selected_variables,
        )

    @staticmethod
    def load_results(
        project_path: Path,
        simulation_type: str,
        parent: QWidget = None,
        results_dir: Optional[Path] = None,
        selected_variables: Optional[List[str]] = None,
    ) -> Optional[PlotCreator]:
        """
        Load results and create plot creator strategy

        Args:
            project_path: Path to project directory
            simulation_type: Type of simulation
            parent: Parent widget for error dialogs

        Returns:
            PlotCreator instance with loaded results or None on error
        """
        try:
            plot_creator = ResultsLoader.create_strategy(
                project_path,
                simulation_type,
                results_dir=results_dir,
                selected_variables=selected_variables,
            )

            if not plot_creator:
                raise Exception(f"Unknown simulation type: {simulation_type}")

            plot_creator.load_results()

            return plot_creator

        except Exception as e:
            if parent:
                QMessageBox.critical(
                    parent,
                    "Error Loading Results",
                    f"Failed to load results from {project_path}:\n\n{str(e)}",
                )
            return None
