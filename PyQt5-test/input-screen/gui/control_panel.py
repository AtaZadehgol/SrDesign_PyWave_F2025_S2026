# ============================================================================
# File: gui/control_panel.py
"""
Control panel for EM Wave Visualization Tool
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QLabel, 
                             QGroupBox, QComboBox, QTextEdit, QMessageBox)
from PyQt5.QtCore import pyqtSignal
from gui.dialogs import MaterialPropertiesDialog
from gui.canvas import DrawMode

class ControlPanel(QWidget):
    """Right side control panel"""
    
    run_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    resume_requested = pyqtSignal()
    
    def __init__(self, canvas):
        super().__init__()
        self.canvas = canvas
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # View mode group
        view_group = QGroupBox("View Mode")
        view_layout = QVBoxLayout()
        
        view_2d_btn = QPushButton("2D Grid View")
        view_2d_btn.setCheckable(True)
        view_2d_btn.setChecked(True)
        view_2d_btn.clicked.connect(lambda: self.set_view_mode('2d'))
        view_layout.addWidget(view_2d_btn)
        
        view_3d_btn = QPushButton("3D View")
        view_3d_btn.setCheckable(True)
        view_3d_btn.clicked.connect(lambda: self.set_view_mode('3d'))
        view_layout.addWidget(view_3d_btn)
        
        self.view_2d_btn = view_2d_btn
        self.view_3d_btn = view_3d_btn
        
        view_group.setLayout(view_layout)
        layout.addWidget(view_group)
        
        # Drawing mode group
        mode_group = QGroupBox("Drawing Mode")
        mode_layout = QVBoxLayout()
        
        self.rect_btn = QPushButton("Draw Rectangle")
        self.rect_btn.setCheckable(True)
        self.rect_btn.setChecked(True)
        self.rect_btn.clicked.connect(lambda: self.set_drawing_mode(DrawMode.RECTANGLE))
        mode_layout.addWidget(self.rect_btn)
        
        self.source_btn = QPushButton("Place Source")
        self.source_btn.setCheckable(True)
        self.source_btn.clicked.connect(lambda: self.set_drawing_mode(DrawMode.SOURCE))
        mode_layout.addWidget(self.source_btn)
        
        self.measure_btn = QPushButton("Place Measurement Point")
        self.measure_btn.setCheckable(True)
        self.measure_btn.clicked.connect(lambda: self.set_drawing_mode(DrawMode.MEASUREMENT))
        mode_layout.addWidget(self.measure_btn)
        
        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)
        
        # Edit controls
        edit_group = QGroupBox("Edit")
        edit_layout = QVBoxLayout()
        
        edit_props_btn = QPushButton("Edit Last Rectangle Properties")
        edit_props_btn.clicked.connect(self.edit_rectangle_properties)
        edit_layout.addWidget(edit_props_btn)
        
        remove_rect_btn = QPushButton("Remove Last Rectangle")
        remove_rect_btn.clicked.connect(self.canvas.remove_last_rectangle)
        edit_layout.addWidget(remove_rect_btn)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.canvas.clear_all)
        edit_layout.addWidget(clear_btn)
        
        edit_group.setLayout(edit_layout)
        layout.addWidget(edit_group)
        
        # Simulation controls
        sim_group = QGroupBox("Simulation")
        sim_layout = QVBoxLayout()
        
        self.exp_combo = QComboBox()
        self.exp_combo.addItems(['Waveguide Propagation', 'Resonance Analysis', 
                                 'S-Parameters', 'Custom Experiment'])
        sim_layout.addWidget(QLabel("Experiment Type:"))
        sim_layout.addWidget(self.exp_combo)
        
        run_btn = QPushButton("Run Simulation")
        run_btn.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        run_btn.clicked.connect(self.run_requested.emit)
        sim_layout.addWidget(run_btn)
        
        pause_btn = QPushButton("Pause Simulation")
        pause_btn.clicked.connect(self.pause_requested.emit)
        sim_layout.addWidget(pause_btn)
        
        resume_btn = QPushButton("Resume Simulation")
        resume_btn.clicked.connect(self.resume_requested.emit)
        sim_layout.addWidget(resume_btn)
        
        sim_group.setLayout(sim_layout)
        layout.addWidget(sim_group)
        
        # Status display
        status_group = QGroupBox("Status")
        status_layout = QVBoxLayout()
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(150)
        self.status_text.setText("Ready. Draw rectangles to define waveguide geometry.")
        status_layout.addWidget(self.status_text)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        layout.addStretch()
    
    def set_drawing_mode(self, mode):
        """Set drawing mode and update button states"""
        # Update button checked states
        self.rect_btn.setChecked(mode == DrawMode.RECTANGLE)
        self.source_btn.setChecked(mode == DrawMode.SOURCE)
        self.measure_btn.setChecked(mode == DrawMode.MEASUREMENT)
        
        # Update canvas mode
        self.canvas.set_mode(mode)
        
        # Log status
        mode_names = {
            DrawMode.RECTANGLE: 'Draw Rectangle',
            DrawMode.SOURCE: 'Place Source',
            DrawMode.MEASUREMENT: 'Place Measurement Point'
        }
        self.log_status(f"Mode: {mode_names.get(mode, mode.name)}")
    
    def set_view_mode(self, mode):
        """Switch between 2D and 3D view"""
        if mode == '2d':
            self.view_2d_btn.setChecked(True)
            self.view_3d_btn.setChecked(False)
            self.canvas.set_view_mode('2d')
            self.log_status("Switched to 2D Grid View")
        else:
            self.view_2d_btn.setChecked(False)
            self.view_3d_btn.setChecked(True)
            self.canvas.set_view_mode('3d')
            self.log_status("Switched to 3D View")
        
    def edit_rectangle_properties(self):
        """Open dialog to edit properties of last rectangle"""
        rect_data = self.canvas.get_last_rectangle()
        
        if not rect_data:
            QMessageBox.warning(self, "No Rectangle", "No rectangles to edit. Draw a rectangle first.")
            return
            
        dialog = MaterialPropertiesDialog(rect_data, self)
        
        if dialog.exec_():
            props = dialog.get_properties()
            self.canvas.update_last_rectangle(props)
            self.log_status(f"Updated properties: {props['material']}")
            
    def log_status(self, message):
        """Add message to status log"""
        self.status_text.append(message)
        
    def get_experiment_type(self):
        """Get selected experiment type"""
        return self.exp_combo.currentText()
        
    def set_experiment_type(self, exp_type):
        """Set experiment type"""
        self.exp_combo.setCurrentText(exp_type)
