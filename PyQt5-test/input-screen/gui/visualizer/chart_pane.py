"""Reusable chart pane for the results visualizer."""

from typing import List, Optional, Tuple

from PyQt5.QtCore import QEvent, Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from .canvas_manager import CanvasManager
from .event_handlers import EventHandler
from .components.dialogs import PlotHistoryDialog


class ChartPaneWidget(QWidget):
    """A single equation bar and chart area."""

    activated = pyqtSignal(object)
    plot_requested = pyqtSignal(object)
    templates_requested = pyqtSignal(object)
    history_requested = pyqtSignal(object)
    move_up_requested = pyqtSignal(object)
    move_down_requested = pyqtSignal(object)
    close_requested = pyqtSignal(object)

    def __init__(self, parent=None, max_plot_history: int = 10):
        super().__init__(parent)

        self.current_figure: Optional[Figure] = None
        self.current_title: str = ""
        self.plots: List[Tuple[str, Figure]] = []
        self.plot_domains: List[str] = []
        self.current_plot_index: int = -1
        self._event_handler: Optional[EventHandler] = None
        self.max_plot_history = max(1, int(max_plot_history))

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setObjectName("chartPane")
        self.setStyleSheet(
            "#chartPane {"
            "border: 1px solid #b8b8b8;"
            "border-radius: 6px;"
            "background: #ffffff;"
            "}"
        )

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)

        control_row = QHBoxLayout()
        control_row.setContentsMargins(0, 0, 0, 0)
        control_row.setSpacing(6)

        self.equation_label = QLabel("Equation:")
        control_row.addWidget(self.equation_label)

        self.equation_input = QLineEdit()
        self.equation_input.setMinimumWidth(220)
        self.equation_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        self.equation_input.textEdited.connect(lambda _text: self.activated.emit(self))
        self.equation_input.returnPressed.connect(lambda: self._emit_plot_requested())
        control_row.addWidget(self.equation_input)

        self.domain_selector = QComboBox()
        self.domain_selector.addItems(["Time Domain", "Frequency Domain"])
        self.domain_selector.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        control_row.addWidget(self.domain_selector)

        self.freq_mode_selector = QComboBox()
        self.freq_mode_selector.addItems(["Re + Im", "Mag + Phase"])
        self.freq_mode_selector.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.freq_mode_selector.hide()  # hidden until Frequency Domain is selected
        control_row.addWidget(self.freq_mode_selector)

        # Connect domain change AFTER freq_mode_selector is created to avoid
        # accessing a not-yet-initialised attribute when addItems fires the signal.
        self.domain_selector.currentIndexChanged.connect(self._on_domain_changed)

        self.templates_btn = QPushButton("Templates")
        self.templates_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.templates_btn.clicked.connect(self._emit_templates_requested)
        control_row.addWidget(self.templates_btn)

        self.history_btn = QPushButton("History")
        self.history_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.history_btn.clicked.connect(self._emit_history_requested)
        self.history_btn.setEnabled(False)
        control_row.addWidget(self.history_btn)

        self.plot_btn = QPushButton("Plot")
        self.plot_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.plot_btn.clicked.connect(self._emit_plot_requested)
        control_row.addWidget(self.plot_btn)

        # Visual separator between plotting controls and pane reordering controls.
        control_row.addSpacing(10)

        self.move_up_btn = QPushButton("Up")
        self.move_up_btn.setToolTip("Move this chart pane up")
        self.move_up_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.move_up_btn.clicked.connect(lambda: self.move_up_requested.emit(self))
        self.move_up_btn.hide()
        control_row.addWidget(self.move_up_btn)

        self.move_down_btn = QPushButton("Down")
        self.move_down_btn.setToolTip("Move this chart pane down")
        self.move_down_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.move_down_btn.clicked.connect(lambda: self.move_down_requested.emit(self))
        self.move_down_btn.hide()
        control_row.addWidget(self.move_down_btn)

        self.close_btn = QPushButton("\u2715")
        self.close_btn.setToolTip("Close this chart pane")
        self.close_btn.setAccessibleName("Close chart pane")
        self.close_btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.close_btn.setStyleSheet(
            "QPushButton { color: #666; font-weight: bold; padding: 2px 6px; }"
            "QPushButton:hover { background-color: #e53935; color: white; border-radius: 3px; }"
        )
        self.close_btn.clicked.connect(lambda: self.close_requested.emit(self))

        control_row.addStretch(1)
        control_row.addWidget(self.close_btn)
        root_layout.addLayout(control_row)

        self.canvas_scroll = QScrollArea()
        self.canvas_scroll.setWidgetResizable(True)
        self.canvas_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.canvas_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.canvas_scroll.viewport().installEventFilter(self)

        self.canvas_container = QWidget()
        self.canvas_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.canvas_layout = QVBoxLayout(self.canvas_container)
        self.canvas_layout.setContentsMargins(0, 0, 0, 0)
        self.canvas_scroll.setWidget(self.canvas_container)
        root_layout.addWidget(self.canvas_scroll, 1)

        self.placeholder_label = QLabel(
            "No results loaded.\nRun a simulation to see results here."
        )
        self.placeholder_label.setAlignment(Qt.AlignCenter)
        self.placeholder_label.setWordWrap(True)
        self.placeholder_label.setMinimumSize(360, 140)
        self.placeholder_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        self.placeholder_label.setStyleSheet(
            """
            QLabel {
                font-size: 13pt;
                color: #666;
                padding: 32px;
            }
        """
        )
        self.canvas_layout.addWidget(self.placeholder_label)

        self.canvas_manager = CanvasManager(self.canvas_layout)
        self.set_controls_enabled(False)

    def _emit_plot_requested(self):
        self.activated.emit(self)
        self.plot_requested.emit(self)

    def _emit_templates_requested(self):
        self.activated.emit(self)
        self.templates_requested.emit(self)

    def _emit_history_requested(self):
        self.activated.emit(self)
        self.history_requested.emit(self)

    def _on_domain_changed(self, _index: int):
        is_freq = self.current_domain() == "frequency"
        self.freq_mode_selector.setVisible(is_freq)
        self.activated.emit(self)

    def set_controls_enabled(self, enabled: bool):
        self.equation_input.setEnabled(enabled)
        self.domain_selector.setEnabled(enabled)
        self.freq_mode_selector.setEnabled(enabled)
        self.templates_btn.setEnabled(enabled)
        self.history_btn.setEnabled(enabled and bool(self.plots))
        self.plot_btn.setEnabled(enabled)

    def set_reorder_controls_enabled(self, up_enabled: bool, down_enabled: bool):
        self.move_up_btn.setEnabled(up_enabled)
        self.move_down_btn.setEnabled(down_enabled)

    def set_reorder_controls_visible(self, visible: bool):
        self.move_up_btn.setVisible(visible)
        self.move_down_btn.setVisible(visible)

    def set_reorder_direction(self, stacked: bool):
        self.move_up_btn.setText("Prev")
        self.move_up_btn.setToolTip("Move this chart pane to the previous position")
        self.move_down_btn.setText("Next")
        self.move_down_btn.setToolTip("Move this chart pane to the next position")

    def set_equation_text(self, text: str):
        self.equation_input.setText(text)

    def set_domain(self, domain: str):
        self.domain_selector.setCurrentIndex(0 if domain == "time" else 1)
        self.freq_mode_selector.setVisible(domain == "frequency")

    def current_domain(self) -> str:
        return "time" if self.domain_selector.currentIndex() == 0 else "frequency"

    def current_freq_mode(self) -> str:
        return "mag_phase" if self.freq_mode_selector.currentIndex() == 1 else "real_imag"

    def show_placeholder_message(self, message: str):
        self.clear_figure()
        self.placeholder_label.setText(message)
        self.placeholder_label.show()

    def clear_history(self):
        for _title, figure in self.plots:
            try:
                figure.clf()
            except Exception:
                pass
        self.plots.clear()
        self.plot_domains.clear()
        self.current_plot_index = -1
        try:
            self.history_btn.setEnabled(False)
        except RuntimeError:
            pass

    def add_plot(self, title: str, figure: Figure, domain: str):
        if len(self.plots) >= self.max_plot_history:
            _old_title, old_figure = self.plots.pop(0)
            if self.plot_domains:
                self.plot_domains.pop(0)
            try:
                plt.close(old_figure)
            except Exception:
                pass
            if self.current_plot_index >= 0:
                self.current_plot_index = max(-1, self.current_plot_index - 1)

        self.plots.append((title, figure))
        self.plot_domains.append(domain)
        self.current_plot_index = len(self.plots) - 1
        self.history_btn.setEnabled(True)
        self.show_figure(figure, title)

    def show_history_plot(self, index: int):
        if index < 0 or index >= len(self.plots):
            return

        self.current_plot_index = index
        title, figure = self.plots[index]
        self.show_figure(figure, title)
        if index < len(self.plot_domains):
            self.set_domain(self.plot_domains[index])

    def open_history_dialog(self):
        if not self.plots:
            return None

        return PlotHistoryDialog(self.plots, self.plot_domains, self.current_plot_index, self)

    def show_figure(self, figure: Figure, title: str = ""):
        self.current_figure = figure
        self.current_title = title

        self.canvas_manager.cleanup()
        self.placeholder_label.hide()

        canvas, toolbar = self.canvas_manager.create_canvas(figure, self)

        self._fit_canvas_to_viewport()
        canvas.draw()

        self._event_handler = EventHandler(toolbar, canvas)
        self.canvas_manager.connect_event(
            "motion_notify_event", self._event_handler.on_mouse_move
        )

    def refresh_plot_size(self):
        if self.current_figure is None:
            return

        self._fit_canvas_to_viewport()
        if self.canvas_manager.current_canvas is not None:
            self.canvas_manager.current_canvas.draw_idle()

    def _fit_canvas_to_viewport(self):
        if self.current_figure is None or self.canvas_manager.current_canvas is None:
            return

        canvas = self.canvas_manager.current_canvas
        toolbar = self.canvas_manager.current_toolbar

        toolbar_h = toolbar.sizeHint().height() if toolbar is not None else 0

        viewport = self.canvas_scroll.viewport().size()
        viewport_w = max(1, viewport.width() - 8)
        viewport_h = max(1, viewport.height() - toolbar_h - 12)

        target_w = viewport_w
        target_h = viewport_h
        self.current_figure.set_size_inches(
            target_w / self.current_figure.dpi,
            target_h / self.current_figure.dpi,
            forward=True,
        )

        canvas.setMinimumSize(target_w, target_h)
        canvas.resize(target_w, target_h)
        self.canvas_container.resize(target_w, target_h + toolbar_h + 8)
        self.canvas_container.setMinimumSize(target_w, target_h + toolbar_h + 8)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_canvas_to_viewport()
        if self.canvas_manager.current_canvas is not None:
            self.canvas_manager.current_canvas.draw_idle()

    def eventFilter(self, watched, event):
        if watched is self.canvas_scroll.viewport() and event.type() == QEvent.Resize:
            self._fit_canvas_to_viewport()
            if self.canvas_manager.current_canvas is not None:
                self.canvas_manager.current_canvas.draw_idle()
        return super().eventFilter(watched, event)

    def showEvent(self, event):
        super().showEvent(event)
        self._fit_canvas_to_viewport()
        if self.canvas_manager.current_canvas is not None:
            self.canvas_manager.current_canvas.draw_idle()

    def clear_figure(self):
        self.canvas_manager.cleanup()
        self.current_figure = None
        self.current_title = ""
        self.placeholder_label.show()

    def cleanup(self):
        self.clear_figure()
