"""Reference panel subpackage for results widget decomposition."""

from .variable_selector import VariableSelectorWidget
from .help_content import build_reference_html, default_reference_html

__all__ = [
    "VariableSelectorWidget",
    "build_reference_html",
    "default_reference_html",
]
