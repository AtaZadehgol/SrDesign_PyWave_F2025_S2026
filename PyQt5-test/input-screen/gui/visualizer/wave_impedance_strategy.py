"""
Dynamic analysis visualization strategy.

Replaces the old WaveImpedanceStrategy with a flexible, equation-driven
analysis system backed by the analysis.Analyzer.
"""

import json
from pathlib import Path
from typing import List, Tuple, Optional
from matplotlib.figure import Figure

from .plot_creator import PlotCreator
from .analysis.analyzer import Analyzer


class DynamicAnalysisStrategy(PlotCreator):
    """
    Universal visualization strategy using the shared analysis engine.
    Works for any simulation type/mode combination that has registered
    field file mappings and equation templates.
    """

    def __init__(
        self,
        project_path: Path,
        results_dir: Optional[Path] = None,
        custom_equations: Optional[list] = None,
        default_export_path: Optional[Path] = None,
        selected_variables: Optional[List[str]] = None,
    ):
        """
        Args:
            project_path: Path to project directory containing
                project_metadata.json and Results/.
            custom_equations: Optional list of dicts, each with keys:
                "expression", "domain" ("time"/"frequency"),
                and optionally "title", "y_label", "y_unit".
            default_export_path: Path for exported plots.
        """
        super().__init__(project_path, results_dir=results_dir, default_export_path=default_export_path)
        self.analyzer: Optional[Analyzer] = None
        self.custom_equations = custom_equations or []
        self.selected_variables = selected_variables

    def load_results(self):
        """Load results using the shared Analyzer."""
        with open(self.project_path / "project_metadata.json", "r") as f:
            metadata = json.load(f)

        self.metadata = metadata
        sim_type = metadata.get("simulation_type", "Wave Impedance").strip()
        pol_mode = metadata.get("polarization_mode", "TE").strip()
        dimension = metadata.get("dimension", "2D").strip()
        cfg = metadata.get("solver_parameters", {})

        self.analyzer = Analyzer(
            self.results_path,
            sim_type,
            pol_mode,
            dimension,
            cfg,
            selected_variables=self.selected_variables,
        )
        self.analyzer.load()

    def set_selected_variables(self, selected_variables: Optional[List[str]]):
        """Update variable subset used for equation plotting and templates."""
        self.selected_variables = selected_variables
        self.load_results()

    def create_plots(self) -> List[Tuple[str, Figure]]:
        """Create template plots plus any custom equation plots."""
        if not self.analyzer:
            self.load_results()

        # Generate all default template plots and track their domains
        templates = self.analyzer.get_templates()
        plots = []
        self.plot_domains = []
        for template in templates:
            valid, _reason = self.analyzer.validate_expression(template.expression)
            if not valid:
                continue
            fig = self.analyzer.plot_template(template)
            plots.append((template.name, fig))
            self.plot_domains.append(template.domain)

        # Append any user-specified custom equations
        for eq in self.custom_equations:
            fig = self.analyzer.plot_equation(
                eq["expression"],
                eq.get("domain", "time"),
                eq.get("title"),
                eq.get("y_label"),
                eq.get("y_unit", ""),
            )
            plots.append((eq.get("title", eq["expression"]), fig))
            self.plot_domains.append(eq.get("domain", "time"))

        return plots


# Backward-compatible alias
WaveImpedanceStrategy = DynamicAnalysisStrategy
