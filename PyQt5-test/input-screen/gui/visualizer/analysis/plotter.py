"""
Domain-specific plotters that create matplotlib figures from
equation evaluations over field data.

TimeDomainPlotter: plots results vs time axis.
FrequencyDomainPlotter: plots results vs frequency axis.
"""

import numpy as np
from matplotlib.figure import Figure
from typing import Dict, Optional, Tuple

from .equation_engine import EquationEngine
from .templates import EquationTemplate


class TimeDomainPlotter:
    """Creates time-domain line plots from probe data and equations."""

    def __init__(self, probe_data: Dict[str, np.ndarray], dt: float):
        """
        Args:
            probe_data: Dict mapping variable names to time series arrays (1D or 2D).
            dt: Time step in seconds.
        """
        self.probe_data = probe_data
        self.dt = dt
        self.nt = _infer_time_length(probe_data)
        self.time_axis = np.arange(self.nt) * dt
        self.engine = EquationEngine(probe_data)

    def plot(
        self,
        expression: str,
        title: Optional[str] = None,
        y_label: str = "Value",
        y_unit: str = "",
    ) -> Figure:
        """
        Evaluate expression over time-domain data and create line plot.

        X-axis: time [s]. Y-axis: result of equation (real part).
        """
        result = self.engine.evaluate(expression)
        result = _regularize(result)

        x_axis, x_label, series = _prepare_plot_series(
            result, self.time_axis, self.dt, "time"
        )

        display_title = title or expression
        unit_str = f" [{y_unit}]" if y_unit else ""

        fig = Figure(figsize=(9, 4))
        ax = fig.add_subplot(111)
        if series.shape[0] == 1:
            ax.plot(x_axis, np.real(series[0]), label=display_title)
        else:
            for idx, row in enumerate(series):
                ax.plot(x_axis, np.real(row), label=f"{display_title}[{idx}]")
        ax.set_xlabel(x_label)
        ax.set_ylabel(f"{y_label}{unit_str}")
        ax.set_title(display_title)
        legend_cols = min(3, max(1, series.shape[0]))
        ax.legend(
            loc="upper center",
            bbox_to_anchor=(0.5, -0.18),
            ncol=legend_cols,
        )
        ax.grid(True, alpha=0.3)
        fig.subplots_adjust(bottom=0.30)
        return fig

    def plot_template(self, template: EquationTemplate) -> Figure:
        """Create plot from a template."""
        return self.plot(
            template.expression, template.name, template.y_label, template.y_unit
        )


class FrequencyDomainPlotter:
    """Creates frequency-domain plots from FFT'd probe data."""

    def __init__(
        self,
        freq_data: Dict[str, np.ndarray],
        freq_axis: np.ndarray,
    ):
        """
        Args:
            freq_data: Dict mapping variable names to complex FFT arrays (1D or 2D).
            freq_axis: Frequency axis array [Hz].
        """
        self.freq_data = freq_data
        self.freq_axis = freq_axis
        self.engine = EquationEngine(freq_data)

    def plot(
        self,
        expression: str,
        title: Optional[str] = None,
        y_label: str = "Value",
        y_unit: str = "",
        display_mode: str = "real_imag",
    ) -> Figure:
        """
        Evaluate expression over frequency-domain data.

        If the result is complex, creates a 2-panel plot whose panels depend on
        ``display_mode``:
          - ``"real_imag"``  — Re{…} (top) + Im{…} (bottom)  [default]
          - ``"mag_phase"``  — |…| (top)  + ∠… in degrees (bottom)
        If the result is real, creates a single-panel plot regardless of mode.
        """
        result = self.engine.evaluate(expression)
        result = _regularize(result)

        x_axis, x_label, series = _prepare_plot_series(
            result, self.freq_axis, 1.0, "frequency"
        )

        display_title = title or expression
        unit_str = f" [{y_unit}]" if y_unit else ""

        is_real = np.allclose(np.nan_to_num(np.imag(series)), 0)

        if is_real:
            fig = Figure(figsize=(9, 4))
            ax = fig.add_subplot(111)
            if series.shape[0] == 1:
                ax.plot(x_axis, np.real(series[0]), label=display_title)
            else:
                for idx, row in enumerate(series):
                    ax.plot(x_axis, np.real(row), label=f"{display_title}[{idx}]")
            ax.set_xlabel(x_label)
            ax.set_ylabel(f"{y_label}{unit_str}")
            ax.set_title(display_title)
            legend_cols = min(3, max(1, series.shape[0]))
            ax.legend(
                loc="upper center",
                bbox_to_anchor=(0.5, -0.18),
                ncol=legend_cols,
            )
            ax.grid(True, alpha=0.3)
            fig.subplots_adjust(bottom=0.30)
        else:
            fig = Figure(figsize=(9, 7))
            ax0 = fig.add_subplot(2, 1, 1)
            ax1 = fig.add_subplot(2, 1, 2, sharex=ax0)
            axs = [ax0, ax1]
            legend_cols = min(3, max(1, series.shape[0]))

            if display_mode == "mag_phase":
                for idx, row in enumerate(series):
                    label = f"|{display_title}|[{idx}]" if series.shape[0] > 1 else f"|{display_title}|"
                    axs[0].plot(x_axis, np.abs(row), label=label)
                axs[0].set_ylabel(f"|{y_label}|{unit_str}")
                axs[0].legend(
                    loc="upper center",
                    bbox_to_anchor=(0.5, -0.22),
                    ncol=legend_cols,
                )
                axs[0].grid(True, alpha=0.3)

                for idx, row in enumerate(series):
                    label = f"∠{display_title}[{idx}]" if series.shape[0] > 1 else f"∠{display_title}"
                    axs[1].plot(x_axis, np.angle(row, deg=True), label=label)
                axs[1].set_xlabel(x_label)
                axs[1].set_ylabel(f"∠{y_label} [deg]")
                axs[1].legend(
                    loc="upper center",
                    bbox_to_anchor=(0.5, -0.32),
                    ncol=legend_cols,
                )
                axs[1].grid(True, alpha=0.3)
            else:
                # default: "real_imag"
                for idx, row in enumerate(series):
                    label = f"Re{{{display_title}}}[{idx}]" if series.shape[0] > 1 else f"Re{{{display_title}}}"
                    axs[0].plot(x_axis, np.real(row), label=label)
                axs[0].set_ylabel(f"Re{{{y_label}}}{unit_str}")
                axs[0].legend(
                    loc="upper center",
                    bbox_to_anchor=(0.5, -0.22),
                    ncol=legend_cols,
                )
                axs[0].grid(True, alpha=0.3)

                for idx, row in enumerate(series):
                    label = f"Im{{{display_title}}}[{idx}]" if series.shape[0] > 1 else f"Im{{{display_title}}}"
                    axs[1].plot(x_axis, np.imag(row), label=label)
                axs[1].set_xlabel(x_label)
                axs[1].set_ylabel(f"Im{{{y_label}}}{unit_str}")
                axs[1].legend(
                    loc="upper center",
                    bbox_to_anchor=(0.5, -0.32),
                    ncol=legend_cols,
                )
                axs[1].grid(True, alpha=0.3)

            fig.suptitle(display_title)
            fig.subplots_adjust(bottom=0.28, top=0.92, hspace=0.72)

        return fig

    def plot_template(self, template: EquationTemplate) -> Figure:
        """Create plot from a template."""
        return self.plot(
            template.expression, template.name, template.y_label, template.y_unit
        )


def _regularize(arr: np.ndarray) -> np.ndarray:
    """Replace inf values with nan for clean plotting."""
    return np.where(np.isinf(arr), np.nan, arr)


def _prepare_plot_series(
    result: np.ndarray,
    base_axis: np.ndarray,
    spacing: float,
    domain: str,
) -> Tuple[np.ndarray, str, np.ndarray]:
    """Normalize equation output into [num_series, num_samples] for plotting."""
    arr = np.asarray(result)

    if arr.ndim == 1:
        series = arr.reshape(1, -1)
    elif arr.ndim >= 2:
        # Treat final axis as sample/time axis and flatten spatial dims.
        sample_count = arr.shape[-1]
        series = arr.reshape(-1, sample_count)
    else:
        raise ValueError(
            "Expression must evaluate to an array for plotting."
        )

    x_axis, x_label = _resolve_axis(base_axis, series.shape[1], spacing, domain)
    return x_axis, x_label, series


def _infer_time_length(data: Dict[str, np.ndarray]) -> int:
    """Infer timestep count from mixed 1D/2D arrays."""
    arrays = [np.asarray(arr) for arr in data.values()]
    if not arrays:
        return 0

    # Prefer longest 1D series, else longest axis among all arrays.
    one_d_lengths = [arr.shape[0] for arr in arrays if arr.ndim == 1]
    if one_d_lengths:
        return max(one_d_lengths)

    return max(max(arr.shape) for arr in arrays)


def _resolve_axis(
    base_axis: np.ndarray,
    result_length: int,
    spacing: float,
    domain: str,
) -> Tuple[np.ndarray, str]:
    """Resolve an x-axis that matches result length, including slices."""
    if result_length == base_axis.shape[0]:
        if domain == "time":
            return base_axis, "Time, t [s]"
        return base_axis, "Frequency, f [Hz]"

    # For sliced results we only know local sample positions.
    if domain == "time":
        return np.arange(result_length) * spacing, "Time, t [s] (local slice)"
    return np.arange(result_length), "Frequency Bin Index (local slice)"
