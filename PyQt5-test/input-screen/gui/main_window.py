# ============================================================================
# File: gui/main_window.py
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QLabel,
    QMessageBox,
    QComboBox,
    QSplitter,
    QStackedWidget,
    QDialog,
    QPushButton,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
import os
from pathlib import Path

from gui.canvas import DrawingCanvas
from gui.rectangle_dialog import RectangleEditDialog
from gui.dialogs import  DomainDialog
from gui.advanced_params_dialog import AdvancedParametersDialog
from gui.welcome_dialog import WelcomeDialog
from gui.ribbon_widget import RibbonWidget
from gui.menu_handler import MenuHandler
from gui.simulation_manager import SimulationManager
from utils.file_handler import FileHandler
from gui.sidebar import ProjectTree, TreeContextMenu
from gui.sidebar.screen_models import ProblemDefinitionScreen, ResultScreen
from gui.progress_bar import SimulationProgressWidget
from gui.solver_output_dialog import SolverOutputDialog
from gui.visualizer import ResultsWidget, HeatmapResultsWidget


class EMWaveGUI(QMainWindow):
    """Main GUI application for Electromagnetic Wave Simulation"""

    def __init__(self):
        super().__init__()

        welcome = WelcomeDialog(self)
        if welcome.exec_() != QDialog.Accepted:
            import sys

            sys.exit(0)

        self.config = welcome.get_configuration()

        self.setWindowTitle(
            f"EM Simulation - {self.config.get('mode', 'TM')} "
            f"{self.config.get('view', '2D')} - {self.config.get('simulation_type', 'FDTD')}"
        )
        self.setGeometry(100, 100, 1400, 900)

        self.file_handler = FileHandler()
        self.menu_handler = MenuHandler(self)
        self.simulation_manager = SimulationManager(self)

        self.advanced_params = {
            "delta_t_coef": 1.0,
            "harmonics": 1.0,
            "num_flights": 2.0,
            "num_cpml": 20,
            #"buffer_wavelengths": 2.0,
            "eps_rel_bg": 2.25,
            "mu_rel_bg": 1.0,
            "rough_toggle": False,
            "rough_std": 1.5000000000000002e-08,
            "rough_acl": 2.000000000000001e-08,
            "ctype": 3,
            "tol_std": 20.0,
            "tol_acl": 20.0,
            "source_type": "Gaussian Pulse",
            "amplitude": 20.0,
            "frequency": 198400000000000.0,
            "gauss_pulse_deg": -6.0,
            "wave_packet_bw": 0.1
        }

        self.init_ui()

    def init_ui(self):
        self.menu_handler.create_menu_bar()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        domain = DomainDialog(self)

        # Horizontal splitter for sidebar + content
        splitter = QSplitter(Qt.Horizontal)

        # Sidebar (ProjectTree) on the left, spanning full height
        self.sidebar = ProjectTree()
        self.sidebar.setMinimumWidth(250)
        self.sidebar.setMaximumWidth(400)
        self.sidebar.screen_selected.connect(self.on_sidebar_screen_selected)

        # Context menu for sidebar
        self.sidebar.setContextMenuPolicy(Qt.CustomContextMenu)
        self.sidebar.customContextMenuRequested.connect(self.show_sidebar_context_menu)
        self.sidebar_context_menu = TreeContextMenu(self.sidebar)

        # Canvas
        self.canvas = DrawingCanvas()
        self.canvas.selection_changed.connect(self.update_status_coordinates)

        # Ribbon + Canvas container (shown for Project screens)
        self.canvas_container = QWidget()
        canvas_container_layout = QVBoxLayout(self.canvas_container)
        canvas_container_layout.setContentsMargins(0, 0, 0, 0)
        canvas_container_layout.setSpacing(0)
        self.create_ribbon(canvas_container_layout)
        canvas_container_layout.addWidget(self.canvas)

        # Interactive results viewer with matplotlib integration
        self.result_widgets = {}
        self.results_widget = None
        self.heatmap_widget = None

        self.results_container = QWidget()
        self.results_container_layout = QVBoxLayout(self.results_container)
        self.results_container_layout.setContentsMargins(0, 0, 0, 0)
        self.results_container_layout.setSpacing(0)

        self.result_stack = QStackedWidget()
        self.results_placeholder = QLabel(
            "Select a result screen from the project tree to view results."
        )
        self.results_placeholder.setAlignment(Qt.AlignCenter)
        self.results_placeholder.setStyleSheet("color: #666; font-size: 13px;")
        self.result_stack.addWidget(self.results_placeholder)
        self.results_container_layout.addWidget(self.result_stack)

        # Stacked widget to switch between canvas+ribbon and results
        self.content_stack = QStackedWidget()
        self.content_stack.addWidget(self.canvas_container)  # Index 0
        self.content_stack.addWidget(self.results_container)  # Index 1

        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.content_stack)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)
        layout.setStretchFactor(splitter, 1)

        # Progress bar
        self.progress_text = SimulationProgressWidget()
        self.progress_text.setFixedHeight(30)
        layout.addWidget(self.progress_text)

        # Row: results label on left, button on right
        progress_row = QWidget()
        progress_row.setStyleSheet("")
        progress_row_layout = QHBoxLayout(progress_row)
        progress_row_layout.setContentsMargins(10, 0, 10, 0)
        progress_row_layout.setSpacing(8)

        self.results_label = QLabel("")
        self.results_label.setStyleSheet("color: #000000; font-weight: bold; font-size: 13px;")
        progress_row_layout.addWidget(self.results_label, 1)

        self.solver_output_btn = QPushButton("Solver Output")
        self.solver_output_btn.setFixedHeight(22)
        self.solver_output_btn.setFixedWidth(120)
        self.solver_output_btn.setStyleSheet("""
            QPushButton {
                background: #1233dd; color: #ffffff;
                border: 0.5px solid #444; border-radius: 4px;
                font-weight: bold; font-size: 12px;
                padding: 0 10px;
            }
            QPushButton:hover { color: #ffffff; border-color: #5af; background: #112233; }
            QPushButton:pressed { background: #1a1a1a; }
        """)
        self.solver_output_btn.clicked.connect(self.open_solver_output)
        progress_row_layout.addWidget(self.solver_output_btn)

        layout.addWidget(progress_row)

        self.solver_output_dialog = SolverOutputDialog(self)
        self.progress_text.set_log_widget(self.solver_output_dialog.log_widget)

        # --- HIDDEN COMPATIBILITY WIDGETS ---
        # These are required by SimulationManager logic but not shown in UI
        self.exp_combo = QComboBox()
        self.exp_combo.addItems(
            ["Wave Impedance ", "Scattering Loss", "S-Parameters", "Custom Experiment"]
        )
        self.exp_combo.setCurrentText(
            self.config.get("simulation_type", "Custom Experiment")
        )
        self.exp_combo.currentTextChanged.connect(
            self.ribbon_widget.set_simulation_type
        )
        self.exp_combo.setVisible(False)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["TE Mode", "TM Mode"])
        self.mode_combo.currentTextChanged.connect(self.ribbon_widget.set_mode)
        self.mode_combo.setCurrentText( "TE Mode" if self.config.get("mode", "TE") == "TE" else "TM Mode")
        
        self.mode_combo.setVisible(False)
        self.ribbon_widget.set_mode(self.mode_combo.currentText())

        # In-memory screen management
        self.current_screen = None

        # Initialize with one Problem Definition and one Result screen
        problem_screen = ProblemDefinitionScreen("Problem Definition")
        chart_screen = ResultScreen("Chart", view_type="chart")
        heatmap_screen = ResultScreen("Heatmap", view_type="heatmap")
        self.sidebar.add_problem_screen(problem_screen)
        self.sidebar.add_result_screen(chart_screen)
        self.sidebar.add_result_screen(heatmap_screen)
        self.current_screen = problem_screen

        # Select Problem Definition in the sidebar (first item)
        self.sidebar.setCurrentItem(self.sidebar.topLevelItem(0))

        self.statusBar().showMessage("System Ready")

    def show_sidebar_context_menu(self, pos):
        item = self.sidebar.itemAt(pos)
        self.sidebar_context_menu.show_for(pos, item)

    def on_sidebar_screen_selected(self, screen):
        # Save current screen state before switching
        if self.current_screen is not None:
            self.save_current_screen_state()
        self.current_screen = screen
        self.load_screen_state(screen)

    def save_current_screen_state(self):
        if self.current_screen and hasattr(self.current_screen, "canvas_data"):
            self.current_screen.canvas_data = self.canvas.get_solver_data()

    def load_screen_state(self, screen):
        if isinstance(screen, ProblemDefinitionScreen):
            # Show canvas (with ribbon) for problem definition
            self.content_stack.setCurrentIndex(0)
            if screen.canvas_data and hasattr(self.canvas, "load_from_data"):
                self.canvas.load_from_data(screen.canvas_data)
        elif isinstance(screen, ResultScreen):
            # Show interactive results widget
            self.content_stack.setCurrentIndex(1)
            result_widget = self._ensure_result_widget(screen)
            self.result_stack.setCurrentWidget(result_widget)

            # Load results if available
            if hasattr(screen, "results_path") and screen.results_path:
                from pathlib import Path

                results_path = Path(screen.results_path)
                if results_path.exists():
                    result_widget.load_results(results_path)

    def _get_result_widget_for_screen(self, screen):
        if not isinstance(screen, ResultScreen):
            return None

        return self.result_widgets.get(screen)

    def _ensure_result_widget(self, screen):
        view_type = getattr(screen, "view_type", "chart")
        existing = self.result_widgets.get(screen)
        if existing is not None:
            return existing

        if view_type == "heatmap":
            widget = HeatmapResultsWidget(file_handler=self.file_handler)
            self.heatmap_widget = widget
        else:
            widget = ResultsWidget(file_handler=self.file_handler)
            self.results_widget = widget

        self.result_widgets[screen] = widget
        self.result_stack.addWidget(widget)
        return widget

    def preload_results_widgets(self, project_path, force_reload: bool = False) -> bool:
        """Preload all result widgets for a project when results files exist."""
        project_root = Path(project_path)
        metadata_path = project_root / "project_metadata.json"
        results_dir = project_root / "Results"
        if not metadata_path.exists() or not results_dir.exists():
            return False

        result_screens = self.sidebar.get_result_screens()
        for screen in result_screens:
            screen.results_path = str(project_root)
            result_widget = self._ensure_result_widget(screen)
            if force_reload and hasattr(result_widget, "invalidate_loaded_results_cache"):
                result_widget.invalidate_loaded_results_cache()
            result_widget.load_results(project_root)

        return bool(result_screens)

    def create_ribbon(self, parent_layout):
        self.ribbon_widget = RibbonWidget(self.config, self)
        self.ribbon_widget.setMaximumHeight(150)

        self.ribbon_widget.grid_changed.connect(self.on_grid_changed)
        self.ribbon_widget.domain_changed.connect(self.on_domain_changed)
        self.canvas.domain_loaded.connect(self.on_domain_loaded)
        self.ribbon_widget.drawing_mode_changed.connect(self.set_drawing_mode)
        self.ribbon_widget.run_clicked.connect(self.run_simulation)
        self.ribbon_widget.pause_clicked.connect(self.pause_simulation)
        self.ribbon_widget.resume_clicked.connect(self.resume_simulation)
        self.ribbon_widget.delete_last_clicked.connect(
            self.canvas.remove_last
        )
        self.ribbon_widget.clear_all_clicked.connect(self.canvas.clear_all)
        self.ribbon_widget.grid_density_changed.connect(self.canvas.set_grid_line_density)

        parent_layout.addWidget(self.ribbon_widget)

    def on_grid_changed(self, dx, dy):
        """dx and dy are in meters"""
        self.canvas.set_grid_spacing(dx, dy)
        dx_um = dx * 1e6  # Convert to µm for display
        dy_um = dy * 1e6
        self.statusBar().showMessage(f"Grid Updated: Δx={dx_um:.3f} µm, Δy={dy_um:.3f} µm")

    def on_domain_loaded(self, nx, ny, delta_x_um):
        self.ribbon_widget.nx_spin.blockSignals(True)
        self.ribbon_widget.ny_spin.blockSignals(True)
        self.ribbon_widget.delta_x_spin.blockSignals(True)
        self.ribbon_widget.nx_spin.setValue(nx)
        self.ribbon_widget.ny_spin.setValue(ny)
        self.ribbon_widget.delta_x_spin.setValue(delta_x_um)
        self.ribbon_widget.nx_spin.blockSignals(False)
        self.ribbon_widget.ny_spin.blockSignals(False)
        self.ribbon_widget.delta_x_spin.blockSignals(False)

    def on_domain_changed(self, nx, ny):
        self.canvas.set_domain(nx, ny)
        self.statusBar().showMessage(f"Domain: {nx} × {ny} cells")

    def set_drawing_mode(self, mode):
        self.canvas.set_mode(mode)
        self.statusBar().showMessage(f"Active Tool: {mode.upper()}")

    def update_status_coordinates(self, coords):
        """coords are in meters"""
        if coords:
            x_um = coords[0] * 1e6  # Convert to µm for display
            y_um = coords[1] * 1e6
            self.statusBar().showMessage(f"Object at: X={x_um:.3f} µm, Y={y_um:.3f} µm")

    def edit_material_properties(self):
        selected = self.canvas.get_last_rectangle()
        if not selected:
            QMessageBox.information(
                self, "Selection", "Select a rectangle to edit properties."
            )
            return

        dialog = RectangleEditDialog(selected, self.canvas, self)
        dialog.properties_updated.connect(self.handle_geometry_updates)

        if dialog.exec_() == QDialog.Accepted:
            props = dialog.get_properties()

            if props.get("delete_flag"):
                self.canvas.remove_specific_rectangle(selected)
                self.statusBar().showMessage("Object Deleted")
            else:
                selected.update(props)
                self.canvas.update()
                self.statusBar().showMessage(f"Properties saved for {props['name']}")

    def handle_geometry_updates(self, props):
        self.canvas.update()

    def run_simulation(self):
        self.simulation_manager.run_simulation()

    def pause_simulation(self):
        self.simulation_manager.pause_simulation()
        self.progress_text.append("Simulation Paused.")

    def resume_simulation(self):
        self.simulation_manager.resume_simulation()
        self.progress_text.append("Simulation Resumed.")

    def open_advanced_parameters(self):
        dialog = AdvancedParametersDialog(self)
        dialog.set_parameters(self.advanced_params)
        #signal connections
        dialog.global_roughness.connect(self.on_global_roughness)
        dialog.global_sources.connect(self.on_global_sources)

        if dialog.exec_():
            self.advanced_params = dialog.get_parameters()
            self.canvas.set_num_cpml(self.advanced_params.get('num_cpml', 20))
            self.statusBar().showMessage("Advanced Parameters Applied")

    def on_global_roughness(self, roughness):
        self.canvas.update_global_roughness(roughness)
    
    def on_global_sources(self, source_info):
        self.canvas.update_global_source_info(source_info)

    def open_solver_output(self):
        self.solver_output_dialog.show()
        self.solver_output_dialog.raise_()