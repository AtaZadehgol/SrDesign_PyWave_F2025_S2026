"""
Canvas and toolbar management for matplotlib figure display
"""

from PyQt5.QtWidgets import QSizePolicy
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from typing import Optional, Tuple


class CanvasManager:
    """Manages matplotlib canvas and toolbar lifecycle"""

    def __init__(self, canvas_layout):
        """
        Initialize canvas manager

        Args:
            canvas_layout: QVBoxLayout to add canvas/toolbar widgets to
        """
        self.canvas_layout = canvas_layout
        self.current_canvas: Optional[FigureCanvas] = None
        self.current_toolbar: Optional[NavigationToolbar] = None
        self.current_mpl_connection = None

    def create_canvas(
        self, figure: Figure, parent
    ) -> Tuple[FigureCanvas, NavigationToolbar]:
        """
        Create canvas and toolbar for a figure

        Args:
            figure: Matplotlib figure to display
            parent: Parent widget for toolbar

        Returns:
            Tuple of (canvas, toolbar)
        """
        # Cleanup previous canvas first
        self.cleanup()

        # Save and restore original figure DPI to prevent compounding.
        # FigureCanvasQTAgg.__init__ multiplies figure.dpi by the device
        # pixel ratio.  When the same Figure is reused across swaps the
        # DPI keeps doubling, which makes the canvas grow each time.
        original_dpi = getattr(figure, "_original_dpi", figure.dpi)
        if not hasattr(figure, "_original_dpi"):
            figure._original_dpi = original_dpi
        else:
            figure.dpi = original_dpi

        # Create new canvas and toolbar
        canvas = FigureCanvas(figure)
        toolbar = NavigationToolbar(canvas, parent)

        # Prevent growing minimum sizes across swaps
        canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        toolbar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Disable default coordinate display
        for ax in figure.get_axes():
            ax.format_coord = lambda x, y: ""

        # Add to layout
        self.canvas_layout.addWidget(toolbar)
        self.canvas_layout.addWidget(canvas)

        self.current_canvas = canvas
        self.current_toolbar = toolbar

        canvas.draw()

        return canvas, toolbar

    def connect_event(self, event_name: str, handler):
        """
        Connect matplotlib event handler

        Args:
            event_name: Event name (e.g., "motion_notify_event")
            handler: Event handler function
        """
        if self.current_canvas:
            self.current_mpl_connection = self.current_canvas.mpl_connect(
                event_name, handler
            )

    def cleanup(self):
        """Safely cleanup canvas and toolbar"""
        if self.current_canvas:
            # Disconnect matplotlib events
            if self.current_mpl_connection is not None:
                try:
                    self.current_canvas.mpl_disconnect(self.current_mpl_connection)
                except:
                    pass
                self.current_mpl_connection = None

            # Disconnect all matplotlib callbacks
            try:
                if hasattr(self.current_canvas, "callbacks"):
                    for event_name in list(
                        self.current_canvas.callbacks.callbacks.keys()
                    ):
                        for cid in list(
                            self.current_canvas.callbacks.callbacks[event_name].keys()
                        ):
                            try:
                                self.current_canvas.mpl_disconnect(cid)
                            except:
                                pass
            except:
                pass

            # Disable mouse tracking
            try:
                self.current_canvas.setMouseTracking(False)
            except:
                pass

            # Cleanup toolbar
            if self.current_toolbar:
                try:
                    self.current_toolbar.setMouseTracking(False)
                    self.current_toolbar.blockSignals(True)
                    self.current_toolbar.setEnabled(False)
                    self.current_toolbar.hide()
                    self.current_toolbar.setParent(None)
                    self.canvas_layout.removeWidget(self.current_toolbar)
                except:
                    pass

            # Cleanup canvas
            try:
                self.current_canvas.blockSignals(True)
                self.current_canvas.hide()
                self.current_canvas.setParent(None)
                self.canvas_layout.removeWidget(self.current_canvas)
            except:
                pass

            # Close figure
            figure_to_close = None
            try:
                figure_to_close = self.current_canvas.figure
            except:
                pass
            if figure_to_close is not None:
                try:
                    plt.close(figure_to_close)
                except:
                    pass

            # Delete widgets
            if self.current_toolbar:
                try:
                    self.current_toolbar.close()
                    self.current_toolbar.deleteLater()
                except:
                    pass

            if self.current_canvas:
                try:
                    self.current_canvas.close()
                    self.current_canvas.deleteLater()
                except:
                    pass

            self.current_canvas = None
            self.current_toolbar = None

        # Reset container minimum size to avoid size hint accumulation
        try:
            container = self.canvas_layout.parentWidget()
            if container is not None:
                container.setMinimumSize(0, 0)
                container.updateGeometry()
        except:
            pass
