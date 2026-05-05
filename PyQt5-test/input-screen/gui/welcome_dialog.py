# ============================================================================
# File: gui/welcome_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QComboBox, QGroupBox, QRadioButton,
                             QButtonGroup, QTextEdit, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap

class WelcomeDialog(QDialog):
    """Welcome screen shown on application startup"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Electromagnetic Wave Simulation - Welcome")
        self.setModal(True)
        self.setMinimumSize(800, 700)
        
        # Store user selections
        self.simulation_type = None
        self.mode = None
        self.view_type = None
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # ===== HEADER SECTION =====
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2196F3, stop:1 #051650);
                border-radius: 10px;
                padding: 20px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        
        title_label = QLabel("Electromagnetic Wave Simulation")
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: white;")
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)
        
        subtitle_label = QLabel("A Univeristy of Idaho Senior Undergraduate Capstone Project Under Professor Ata Zadehgol \n Developed By Amanda Board, Carla Kolze, and Austin Walker")
        subtitle_font = QFont()
        subtitle_font.setPointSize(12)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setStyleSheet("color: #E3F2FD;")
        subtitle_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(subtitle_label)
        
        layout.addWidget(header_frame)
        
        # ===== PROJECT DESCRIPTION =====
        desc_label = QLabel(
            "This tool provides a Python-based interface for electromagnetic wave simulation "
            "using FDTD (Finite-Difference Time-Domain) methods. Design waveguides, set material "
            "properties, and analyze wave propagation in various configurations."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #555; padding: 10px;")
        layout.addWidget(desc_label)
        
        # ===== SIMULATION CONFIGURATION =====
        config_group = QGroupBox("Configure Your Simulation")
        config_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #2196F3;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                color: #051650;
            }
        """)
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(15)
        
        # Simulation Type Selection
        sim_type_layout = QVBoxLayout()
        sim_type_label = QLabel("Simulation Type:")
        sim_type_label.setStyleSheet("font-weight: bold; color: #333;")
        sim_type_layout.addWidget(sim_type_label)
        
        self.sim_type_combo = QComboBox()
        self.sim_type_combo.addItems([
            'Wave Impedance',
            'Scattering Loss',
            'S-Parameters (Coming Soon)',
            'Custom Experiment (Coming Soon)'
        ])
        self.sim_type_combo.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 12px;
            }
        """)
        self.sim_type_combo.currentTextChanged.connect(self.on_selection_changed)
        sim_type_layout.addWidget(self.sim_type_combo)
        config_layout.addLayout(sim_type_layout)
        
        # View Type Selection (2D/3D)
        view_layout = QVBoxLayout()
        view_label = QLabel("Dimensionality:")
        view_label.setStyleSheet("font-weight: bold; color: #333;")
        view_layout.addWidget(view_label)
        
        view_button_layout = QHBoxLayout()
        self.view_button_group = QButtonGroup(self)
        
        self.view_2d_radio = QRadioButton("2D Simulation")
        self.view_2d_radio.setChecked(True)
        self.view_2d_radio.setStyleSheet("font-size: 11px;")
        self.view_2d_radio.toggled.connect(self.on_selection_changed)
        self.view_button_group.addButton(self.view_2d_radio)
        view_button_layout.addWidget(self.view_2d_radio)
        
        self.view_3d_radio = QRadioButton("3D Simulation (Coming Soon)")
        self.view_3d_radio.setEnabled(True)
        self.view_3d_radio.setStyleSheet("font-size: 11px; color: #999;")
        self.view_3d_radio.toggled.connect(self.on_selection_changed)
        self.view_button_group.addButton(self.view_3d_radio)
        view_button_layout.addWidget(self.view_3d_radio)
        
        view_layout.addLayout(view_button_layout)
        config_layout.addLayout(view_layout)

        # Mode Selection (TE/TM)
        mode_layout = QVBoxLayout()
        mode_label = QLabel("Polarization Mode:")
        mode_label.setStyleSheet("font-weight: bold; color: #333;")
        mode_layout.addWidget(mode_label)
        
        mode_button_layout = QHBoxLayout()
        self.mode_button_group = QButtonGroup(self)
        
        self.te_radio = QRadioButton("TE Mode (Ez = 0)")
        self.te_radio.setChecked(True)
        self.te_radio.setStyleSheet("font-size: 11px;")
        self.te_radio.toggled.connect(self.on_selection_changed)
        self.mode_button_group.addButton(self.te_radio)
        mode_button_layout.addWidget(self.te_radio)
        
        self.tm_radio = QRadioButton("TM Mode (Ey = 0)")
        self.tm_radio.setStyleSheet("font-size: 11px;")
        self.tm_radio.toggled.connect(self.on_selection_changed)
        self.mode_button_group.addButton(self.tm_radio)
        mode_button_layout.addWidget(self.tm_radio)
        
        mode_layout.addLayout(mode_button_layout)
        config_layout.addLayout(mode_layout)

        layout.addWidget(config_group)
        
        # ===== CURRENT SELECTION DISPLAY =====
        self.selection_label = QLabel()
        self.selection_label.setStyleSheet("""
            QLabel {
                background-color: #E3F2FD;
                border: 1px solid #00072D;
                border-radius: 5px;
                padding: 10px;
                color: #051650;
                font-weight: bold;
            }
        """)
        self.selection_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.selection_label)
        
        # ===== BUTTONS =====
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.start_button = QPushButton("Start Simulation Design")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #051650;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 30px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #00072D;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.start_button.clicked.connect(self.accept)
        button_layout.addWidget(self.start_button)
        
        cancel_button = QPushButton("Exit")
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 12px 30px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
        # NOW update selection display after all widgets are created
        self.update_selection_display()
        # Check initial state
        self.on_selection_changed()
        
    def on_selection_changed(self):
        """Update UI when selections change"""
        sim_text = self.sim_type_combo.currentText()
        
        # Disable start button for "Coming Soon" features
        is_available = "Coming Soon" not in sim_text and self.view_2d_radio.isChecked()
        self.start_button.setEnabled(is_available)

        self.update_selection_display()
        
    def update_selection_display(self):
        """Update the selection summary label"""
        sim_type = self.sim_type_combo.currentText()
        mode = "TE Mode" if self.te_radio.isChecked() else "TM Mode"
        view = "2D" if self.view_2d_radio.isChecked() else "3D"
        self.te_radio.setEnabled(view == "2D")
        self.tm_radio.setEnabled(view == "2D")
        
        if self.start_button.isEnabled():
            status = "Ready to Start"
            if view == "2D":
                self.selection_label.setText(f"{status} | {sim_type} | {mode} | {view}")
            else:
                self.selection_label.setText(f"{status} | {sim_type} | {view}")
        else:
            status = "Configuration Not Available Yet"
            self.selection_label.setText(f"{status} | 2D | Wave Impedance | Scattering Loss currently supported")
            
    def get_configuration(self):
        """Return the selected configuration"""
        return {
            'simulation_type': self.sim_type_combo.currentText() ,
            'view': '2D' if self.view_2d_radio.isChecked() else '3D',
            'mode': 'TE' if self.te_radio.isChecked() else 'TM'  #TODO: only send mode if 2D?
        }