# ============================================================================
# File: gui/ribbon_widget.py
# ============================================================================
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                             QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
                             QFrame, QGroupBox, QGridLayout)
from PyQt5.QtCore import Qt, pyqtSignal

class RibbonWidget(QWidget):
    """Ribbon toolbar widget for the main window"""
    
    # Signals
    grid_changed = pyqtSignal(float, float) # for micrometers
    domain_changed = pyqtSignal(int, int)   # nx, ny
    drawing_mode_changed = pyqtSignal(str)  # mode
    coordinate_changed = pyqtSignal()
    size_changed = pyqtSignal()
    material_changed = pyqtSignal(str)
    edit_material_clicked = pyqtSignal()
    run_clicked = pyqtSignal()
    pause_clicked = pyqtSignal()
    resume_clicked = pyqtSignal()
    delete_last_clicked = pyqtSignal()
    clear_all_clicked = pyqtSignal()
    grid_density_changed = pyqtSignal(int)
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.init_ui()
        
    def init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # ===== DRAWING MODE GROUP =====
        draw_group = self.create_ribbon_group("Drawing Mode")
        draw_layout = QVBoxLayout()
        draw_layout.setSpacing(3)
        
        self.rect_btn = QPushButton("Waveguide")
        self.rect_btn.setCheckable(True)
        self.rect_btn.setChecked(True)
        self.rect_btn.setMinimumWidth(80)
        self.rect_btn.clicked.connect(lambda: self.on_drawing_mode_changed('rectangle'))
        draw_layout.addWidget(self.rect_btn)
        
        self.source_btn = QPushButton("Source")
        self.source_btn.setCheckable(True)
        self.source_btn.setMinimumWidth(80)
        self.source_btn.clicked.connect(lambda: self.on_drawing_mode_changed('source'))
        draw_layout.addWidget(self.source_btn)
        
        self.measure_btn = QPushButton("Measure")
        self.measure_btn.setCheckable(True)
        self.measure_btn.setMinimumWidth(80)
        self.measure_btn.clicked.connect(lambda: self.on_drawing_mode_changed('measurement'))
        draw_layout.addWidget(self.measure_btn)
        
        draw_group.setLayout(draw_layout)
        layout.addWidget(draw_group)

        layout.addWidget(self.create_separator())

        # ===== GRID Domain Dimensions and Spacing SETTINGS GROUP =====
        domain_grid_group = self.create_ribbon_group("Grid Dimensions")
        domain_grid_layout = QGridLayout()
        domain_grid_layout.setHorizontalSpacing(5)
        domain_grid_layout.setVerticalSpacing(2)

        domain_grid_layout.addWidget(QLabel("nx (cells):"), 0, 0)
        self.nx_spin = QSpinBox()
        self.nx_spin.setRange(1, 1000)
        self.nx_spin.setValue(100) 
        self.nx_spin.setMinimumWidth(80)
        self.nx_spin.setToolTip("Number of domain cells in the interior region (x direction)")
        self.nx_spin.valueChanged.connect(self.on_grid_changed)
        domain_grid_layout.addWidget(self.nx_spin, 0, 1)


        domain_grid_layout.addWidget(QLabel("ny (cells):"), 1, 0)
        self.ny_spin = QSpinBox()
        self.ny_spin.setRange(1, 1000)
        self.ny_spin.setValue(100) 
        self.ny_spin.setMinimumWidth(80)
        self.ny_spin.setToolTip("Number of domain cells in the interior region (y direction)")
        self.ny_spin.valueChanged.connect(self.on_grid_changed)
        domain_grid_layout.addWidget(self.ny_spin, 1, 1)
        
        domain_grid_layout.addWidget(QLabel("Δx, Δy:"), 2, 0)
        self.delta_x_spin = QDoubleSpinBox()
        self.delta_x_spin.setRange(0.001, 100)
        self.delta_x_spin.setValue(0.05)       # Shows 0.05 µm to user (50 nm)
        self.delta_x_spin.setSingleStep(0.01)  # How much clicking the arrows changes the value
        self.delta_x_spin.setDecimals(3)       # Add this for precision
        self.delta_x_spin.setMinimumWidth(80)
        self.delta_x_spin.setSuffix(" µm")
        self.delta_x_spin.setToolTip("Spatial resolution (m/cell)")
        self.delta_x_spin.valueChanged.connect(self.on_grid_changed)
        domain_grid_layout.addWidget(self.delta_x_spin, 2, 1)

        domain_grid_group.setLayout(domain_grid_layout)
        layout.addWidget(domain_grid_group)

        #TODO: want delta t here or stay in advanced params?
        '''
        grid_layout.addWidget(QLabel("Δt coefficient:"), 1, 0)
        self.delta_t_spin = QDoubleSpinBox()
        self.delta_t_spin.setRange(0.01, 1.0)
        self.delta_t_spin.setValue(1)
        self.delta_t_spin.setDecimals(2)  # Add this for precision
        self.delta_t_spin.setMinimumWidth(80)
        self.delta_t_spin.valueChanged.connect(self.on_grid_changed)
        self.delta_t_spin.setToolTip("Δt is temporal resolution (seconds/step). Δt = coeff * Δx / (base phase velocity * sqrt(2))")
        grid_layout.addWidget(self.delta_t_spin, 1, 1)
        '''

        # ===== DISPLAY GROUP =====
        display_group = self.create_ribbon_group("Grid Display")
        display_layout = QGridLayout()
        display_layout.setHorizontalSpacing(5)
        display_layout.setVerticalSpacing(2)
        
        display_layout.addWidget(QLabel("Grid Lines:"), 0, 0)
        self.grid_density_combo = QComboBox()
        self.grid_density_combo.addItem("Full",    1)
        self.grid_density_combo.addItem("Half",    2)
        self.grid_density_combo.addItem("Quarter", 4)
        self.grid_density_combo.addItem("None",    0)
        self.grid_density_combo.setMinimumWidth(80)
        self.grid_density_combo.setToolTip("Controls how many grid lines are drawn - does not affect simulation resolution")
        self.grid_density_combo.currentIndexChanged.connect(self._on_grid_density_changed)
        display_layout.addWidget(self.grid_density_combo, 0, 1)

        display_group.setLayout(display_layout)
        layout.addWidget(display_group)

        layout.addWidget(self.create_separator())
        
        # ===== SIMULATION GROUP ===== (VERTICAL STACK)
        sim_group = self.create_ribbon_group("Simulation")
        sim_layout = QVBoxLayout()
        sim_layout.setSpacing(3)
        
        # Mode label
        self.mode_label = QLabel(f"{self.config['mode']} Mode")
        self.mode_label.setStyleSheet("""
            QLabel {
                background-color: #031273;
                border: 1px solid #E3F2FD;
                border-radius: 4px;
                padding: 5px;
                color: #E3F2FD;
                font-weight: bold;
            }
        """)
        self.mode_label.setAlignment(Qt.AlignCenter)
        sim_layout.addWidget(self.mode_label)
        
        # View label
        view_label = QLabel(f"{self.config['view']} View")
        view_label.setStyleSheet("""
            QLabel {
                background-color: #0504AA;
                border: 1px solid #E3F2FD;
                border-radius: 4px;
                padding: 5px;
                color: #E3F2FD;
                font-weight: bold;
            }
        """)
        view_label.setAlignment(Qt.AlignCenter)
        sim_layout.addWidget(view_label)
        
        # Simulation type label
        self.sim_type_label = QLabel(self.config['simulation_type'])
        self.sim_type_label.setStyleSheet("""
            QLabel {
                background-color: #2337C6;
                border: 1px solid #E3F2FD;
                border-radius: 4px;
                padding: 5px;
                color: #E3F2FD;
                font-weight: bold;
            }
        """)
        self.sim_type_label.setAlignment(Qt.AlignCenter)
        sim_layout.addWidget(self.sim_type_label)
        
        sim_group.setLayout(sim_layout)
        layout.addWidget(sim_group)
        
        # ===== ACTIONS GROUP =====
        actions_group = self.create_ribbon_group("Actions")
        actions_layout = QVBoxLayout()
        
        run_btn = QPushButton(" Start ")
        run_btn.setStyleSheet("background-color: #4169E1; color: white; font-weight: bold; padding: 5px;")
        run_btn.clicked.connect(lambda: self.run_clicked.emit())
        actions_layout.addWidget(run_btn)
        
        action_row = QHBoxLayout()
        pause_btn = QPushButton(" Pause")
        pause_btn.clicked.connect(lambda: self.pause_clicked.emit())
        action_row.addWidget(pause_btn)
        
        resume_btn = QPushButton(" Resume")
        resume_btn.clicked.connect(lambda: self.resume_clicked.emit())
        action_row.addWidget(resume_btn)
        
        actions_layout.addLayout(action_row)
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)
        
        # ===== EDIT GROUP =====
        edit_group = self.create_ribbon_group("Edit")
        edit_layout = QVBoxLayout()
        
        delete_btn = QPushButton("Delete Last")
        delete_btn.clicked.connect(lambda: self.delete_last_clicked.emit())
        edit_layout.addWidget(delete_btn)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(lambda: self.clear_all_clicked.emit())
        edit_layout.addWidget(clear_btn)
        
        edit_group.setLayout(edit_layout)
        layout.addWidget(edit_group)
        
        layout.addStretch()
        
    def create_ribbon_group(self, title):
        """Create a styled group box for ribbon"""
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #bbb;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                background: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                color: #333;
            }
        """)
        return group
        
    def create_separator(self):
        """Create vertical separator line"""
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("color: #ccc;")
        return separator
        
    #TODO: remove dy?
    def on_grid_changed(self):
        """Convert micrometers from UI to meters for internal storage"""
        dx_um = self.delta_x_spin.value()  # User sees µm
        #dy_um = self.delta_y_spin.value()
        
        dx_m = dx_um * 1e-6  # Convert to meters
        #dy_m = dy_um * 1e-6
        dy_m = dx_m # square cells
        
        self.grid_changed.emit(dx_m, dy_m)  # Emit meters to canvas
        self.domain_changed.emit(self.nx_spin.value(), self.ny_spin.value())
        
    def on_drawing_mode_changed(self, mode):
        """Update button states and emit signal"""
        self.rect_btn.setChecked(mode == 'rectangle')
        self.source_btn.setChecked(mode == 'source')
        self.measure_btn.setChecked(mode == 'measurement')

        self.drawing_mode_changed.emit(mode)
        
    def _on_grid_density_changed(self, _index):
        density = self.grid_density_combo.currentData()
        self.grid_density_changed.emit(density)
    
    def set_simulation_type(self, sim_type: str):
        self.sim_type_label.setText(sim_type)
    
    def set_mode(self, mode: str):
        self.mode_label.setText(f"{mode}")