"""
Event handlers for results widget interactions
"""

import numpy as np
from PyQt5.QtWidgets import QToolTip


class EventHandler:
    """Handles matplotlib and Qt events"""

    def __init__(self, toolbar, canvas=None):
        """
        Initialize event handler

        Args:
            toolbar: NavigationToolbar2QT instance for displaying messages
            canvas: FigureCanvas widget (used for tooltip tracking on Linux)
        """
        self.toolbar = toolbar
        self.canvas = canvas

    def on_mouse_move(self, event):
        """Display data point at cursor position on hover"""
        if not self.toolbar:
            return

        try:
            if event.inaxes:
                x_cursor = event.xdata
                if x_cursor is None:
                    return

                # Find the closest data point on the x-axis
                message_parts = []
                lines = event.inaxes.get_lines()

                if lines:
                    for line in lines:
                        xdata = line.get_xdata()
                        ydata = line.get_ydata()

                        if len(xdata) > 0 and len(ydata) > 0:
                            # Find the closest x-value in the data
                            idx = np.argmin(np.abs(np.asarray(xdata) - x_cursor))
                            x_data = xdata[idx]
                            y_data = ydata[idx]

                            # Get line label if available
                            label = line.get_label()
                            if label and not label.startswith("_"):
                                message_parts.append(
                                    f"{label}: x={x_data:.6e}, y={y_data:.6e}"
                                )
                            else:
                                message_parts.append(f"x={x_data:.6e}, y={y_data:.6e}")

                # Display data points as a tooltip near the cursor
                if message_parts and getattr(event, "guiEvent", None) is not None:
                    # Hide first so Qt repositions the tooltip on Linux/X11
                    QToolTip.hideText()
                    pos = event.guiEvent.globalPos()
                    text = " | ".join(message_parts)
                    if self.canvas is not None:
                        QToolTip.showText(pos, text, self.canvas)
                    else:
                        QToolTip.showText(pos, text)
            else:
                QToolTip.hideText()

        except RuntimeError:
            # Toolbar was deleted, ignore
            pass
        except Exception:
            pass
