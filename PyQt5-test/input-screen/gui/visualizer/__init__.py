"""
Visualizer package for interactive results display
"""

from .results_widget import ResultsWidget
from .plot_creator import PlotCreator
from .wave_impedance_strategy import DynamicAnalysisStrategy, WaveImpedanceStrategy
from .canvas_manager import CanvasManager
from .event_handlers import EventHandler
from .results_loader import ResultsLoader
from .heatmap_results_widget import HeatmapResultsWidget
from .chart_pane import ChartPaneWidget
from .components.dialogs import PlotHistoryDialog, TemplateDialog
from .components.toolbar import ResultsToolbar
from .components.reference_panel import (
    VariableSelectorWidget,
    build_reference_html,
    default_reference_html,
)

__all__ = [
    "ResultsWidget",
    "PlotCreator",
    "DynamicAnalysisStrategy",
    "WaveImpedanceStrategy",
    "CanvasManager",
    "EventHandler",
    "ResultsLoader",
    "HeatmapResultsWidget",
    "ChartPaneWidget",
    "PlotHistoryDialog",
    "TemplateDialog",
    "ResultsToolbar",
    "VariableSelectorWidget",
    "build_reference_html",
    "default_reference_html",
]
