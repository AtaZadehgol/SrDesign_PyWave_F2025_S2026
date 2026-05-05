"""UI subcomponents for the visualizer package."""

from .dialogs import PlotHistoryDialog, TemplateDialog
from .toolbar import ResultsToolbar
from .reference_panel import (
   VariableSelectorWidget,
   build_reference_html,
   default_reference_html,
)

__all__ = [
    "PlotHistoryDialog",
    "TemplateDialog",
    "ResultsToolbar",
    "VariableSelectorWidget",
    "build_reference_html",
    "default_reference_html",
]
