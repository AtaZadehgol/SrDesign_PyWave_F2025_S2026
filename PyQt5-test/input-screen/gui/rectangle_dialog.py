from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit, QCheckBox,
    QComboBox, QGroupBox, QColorDialog, QFormLayout, QDoubleSpinBox, QGridLayout
)
from PyQt5.QtCore import (Qt, pyqtSignal, QRect)
from PyQt5.QtGui import QColor, QDoubleValidator
import copy


class RectangleEditDialog(QDialog):
    """Quick edit dialog for rectangle properties via double-click or right-click"""
    
    # Signal to notify when material updates
    properties_updated = pyqtSignal(dict)

    def __init__(self, rect_data, delta_x, canvas=None, parent=None):
        super().__init__(parent)
        self.rect_data = rect_data
        self.delta_x = delta_x
        self.current_color = self.rect_data.get('color', QColor(200, 200, 255))
        self.canvas = canvas  # Need canvas reference for live preview
        self.delete_flag = False

        self.original_data = copy.deepcopy(rect_data)
        
        self.setWindowTitle(f"Edit {rect_data.get('name', 'Rectangle')}")
        self.setModal(True)
        self.setMinimumWidth(500)

        # Material Presets: (permittivity, permeability, conductivity)
        self.material_presets = {
            'Air': (1.0, 1.0, 0.0),
            'Copper': (1.0, 1.0, 5.8e7),
            'FR-4': (4.5, 1.0, 0.0),
            'Silicon': (11.7, 1.0, 0.0),
            'Teflon': (2.1, 1.0, 0.0)
        }

        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)

        # --- Identification Section ---
        name_group = QGroupBox("Identification")
        name_layout = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setText(self.rect_data.get('name', 'W_1'))
        self.name_input.setPlaceholderText("Enter wavgeuide name...")
        self.name_input.textChanged.connect(self.update_live_preview)
        name_layout.addRow("Name:", self.name_input)
        name_group.setLayout(name_layout)
        layout.addWidget(name_group)

        # --- Geometry Section ---
        geometry_group = QGroupBox("Geometry (Micrometers)")
        geometry_layout = QGridLayout()
        
        # Helper to setup spinboxes with 0.05 step and meters->um conversion
        step = self.delta_x * 1e6
        def setup_spin(val_meters, suffix=" µm"):
            spin = QDoubleSpinBox()
            spin.setSuffix(suffix)
            spin.setDecimals(3)
            spin.setSingleStep(step) # Precise 0.05um steps
            spin.setRange(0, 1000000)
            spin.setValue(val_meters * 1e6)
            spin.valueChanged.connect(self.update_live_preview)
            return spin

        self.pos_label = QLabel("** (x, y) are the top left coordinates of waveguide **")
        self.pos_label.setStyleSheet("font-size: 12px; color: #999;")

        self.x_spin = setup_spin(self.rect_data.get('grid_x', 0))
        self.y_spin = setup_spin(self.rect_data.get('grid_y', 0))
        self.width_spin = setup_spin(self.rect_data.get('grid_width', 10e-6))
        self.height_spin = setup_spin(self.rect_data.get('grid_height', 10e-6))

        # Add to layout 
        geometry_layout.addWidget(QLabel("X:"), 0, 0)
        geometry_layout.addWidget(self.x_spin, 0, 1)
        geometry_layout.addWidget(QLabel("Y:"), 0, 2)
        geometry_layout.addWidget(self.y_spin, 0, 3)
        geometry_layout.addWidget(QLabel("Width:"), 1, 0)
        geometry_layout.addWidget(self.width_spin, 1, 1)
        geometry_layout.addWidget(QLabel("Height:"), 1, 2)
        geometry_layout.addWidget(self.height_spin, 1, 3)

        geometry_group.setLayout(geometry_layout)
        layout.addWidget(geometry_group)
        layout.addWidget(self.pos_label)

        geometry_cell_group = QGroupBox("Geometry (Cells)")
        geometry_cell_layout = QGridLayout()

        # --- Materials Section ---
        material_group = QGroupBox("Material Properties")
        mat_layout = QFormLayout()

        self.material_combo = QComboBox()
        self.material_combo.addItems(['Air', 'Copper', 'FR-4', 'Silicon', 'Teflon', 'Custom'])
        self.material_combo.setCurrentText(self.rect_data.get('material', 'Silicon'))
        self.material_combo.currentTextChanged.connect(self.update_material_fields)
        
        self.sci_validator = QDoubleValidator(0.0, 1e18, 6, self)
        self.sci_validator.setNotation(QDoubleValidator.ScientificNotation)

        self.eps_input = self._create_mat_input(mat_layout, "Permittivity εr:")
        self.mu_input = self._create_mat_input(mat_layout, "Permeability μr:")
        self.sigma_input = self._create_mat_input(mat_layout, "Conductivity σ (S/m):")

        mat_layout.addRow("Material Preset:", self.material_combo)
        material_group.setLayout(mat_layout)
        layout.addWidget(material_group)

        # --- Roughness Section ---
        roughness_group = QGroupBox("Roughness")
        roughness_layout = QVBoxLayout()

        self.rough_warn_label = QLabel("** width should be at least 20x the size of delta x for roughness to be meaningful / find a profile **")
        self.rough_warn_label.setStyleSheet("font-size: 12px; color: #999;")

        roughness_layout.addWidget(self.rough_warn_label)
        self.rough_toggle_check = QCheckBox("Enable Sidewall Roughness")
        self.rough_toggle_check.setChecked(self.rect_data.get('rough_toggle',False))
        roughness_layout.addWidget(self.rough_toggle_check)
        
        self.roughness_params = QGroupBox("Roughness Parameters")
        rough_grid = QGridLayout()
        
        rough_grid.addWidget(QLabel("Std Deviation (nm):"), 0, 0)
        self.rough_std_spin = QDoubleSpinBox()
        self.rough_std_spin.setRange(0.01, 100.0)
        self.rough_std_spin.setValue(self.rect_data.get('rough_std', 15.0) / 1e-9)
        self.rough_std_spin.setDecimals(2)
        rough_grid.addWidget(self.rough_std_spin, 0, 1)
        
        rough_grid.addWidget(QLabel("Correlation Length (nm):"), 1, 0)
        self.rough_acl_spin = QDoubleSpinBox()
        self.rough_acl_spin.setRange(1.0, 2000.0)
        self.rough_acl_spin.setValue(self.rect_data.get('rough_acl', 700.0) / 1e-9)
        self.rough_acl_spin.setDecimals(2)
        rough_grid.addWidget(self.rough_acl_spin, 1, 1)
        
        rough_grid.addWidget(QLabel("Correlation Type:"), 2, 0)
        self.ctype_combo = QComboBox()
        self.ctype_combo.addItems(['Direct (Bend)', 'Inverse (Pinch)', 'Uncorrelated (Both)'])
        self.ctype_combo.setCurrentIndex(self.rect_data.get('ctype', 3) -1)  # Default to 3
        rough_grid.addWidget(self.ctype_combo, 2, 1)
        
        rough_grid.addWidget(QLabel("Std Dev Tolerance (%):"), 3, 0)
        self.tol_std_spin = QDoubleSpinBox()
        self.tol_std_spin.setRange(1.0, 100.0)
        self.tol_std_spin.setValue(self.rect_data.get('tol_std', 10.0))
        rough_grid.addWidget(self.tol_std_spin, 3, 1)
        
        rough_grid.addWidget(QLabel("Corr Length Tolerance (%):"), 4, 0)
        self.tol_acl_spin = QDoubleSpinBox()
        self.tol_acl_spin.setRange(1.0, 100.0)
        self.tol_acl_spin.setValue(self.rect_data.get('tol_acl', 10.0))
        rough_grid.addWidget(self.tol_acl_spin, 4, 1)
        
        self.roughness_params.setLayout(rough_grid)
        self.rough_toggle_check.toggled.connect(self.roughness_params.setEnabled)
        self.rough_toggle_check.toggled.connect(self.update_live_preview)
        self.roughness_params.setEnabled(self.rect_data.get('rough_toggle', False))
        
        roughness_layout.addWidget(self.roughness_params)
        roughness_layout.addStretch()
        roughness_group.setLayout(roughness_layout)
        layout.addWidget(roughness_group)

        self.load_initial_material_values()

        # --- Appearance Section ---
        color_group = QGroupBox("Appearance")
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Color:"))
        
        current_color = self.rect_data.get('color', QColor(100, 200, 255, 100))
        if isinstance(current_color, tuple): current_color = QColor(*current_color)
        
        self.color_button = QPushButton()
        self.color_button.setFixedSize(60, 30)
        self.current_color = current_color
        self.update_color_button()
        self.color_button.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_button)
        color_layout.addStretch()
        color_group.setLayout(color_layout)
        layout.addWidget(color_group)

        # --- Action Buttons ---
        button_layout = QHBoxLayout()
        save_btn = self._create_action_button("Save", "#2196F3", self.accept)
        delete_btn = self._create_action_button("Delete", "#f44336", self.handle_delete)
        cancel_btn = self._create_action_button("Cancel", "#6B6D72", self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(save_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

    def _create_mat_input(self, layout, label):
        line_edit = QLineEdit()
        line_edit.setValidator(self.sci_validator)
        line_edit.textChanged.connect(self.update_live_preview)
        layout.addRow(label, line_edit)
        return line_edit

    def _create_action_button(self, text, color, slot):
        btn = QPushButton(text)
        btn.setStyleSheet(f"QPushButton {{ background-color: {color}; color: white; font-weight: bold; padding: 8px 15px; border-radius: 4px; }}")
        btn.clicked.connect(slot)
        return btn

    def update_live_preview(self):
        """Update the rectangle data with current dialog values"""
        # Guard against signals firing during widget construction
        if not hasattr(self, 'rough_toggle_check') or not isinstance(self.rough_toggle_check, QCheckBox):
            return
            
        if not self.canvas: 
            return
        
        # Correctly convert µm from UI back to meters for PyWave internal data
        self.rect_data['grid_x'] = self.x_spin.value() * 1e-6
        self.rect_data['grid_y'] = self.y_spin.value() * 1e-6
        self.rect_data['grid_width'] = self.width_spin.value() * 1e-6
        self.rect_data['grid_height'] = self.height_spin.value() * 1e-6
        
        self.rect_data['name'] = self.name_input.text().strip() or 'W_1'
        self.rect_data['material'] = self.material_combo.currentText()
        self.rect_data['color'] = self.current_color
        
        self.rect_data['permittivity'] = self._safe_float(self.eps_input.text(), 1.0)
        self.rect_data['permeability'] = self._safe_float(self.mu_input.text(), 1.0)
        self.rect_data['conductivity'] = self._safe_float(self.sigma_input.text(), 0.0)

        self.rect_data['rough_toggle'] = self.rough_toggle_check.isChecked()

        self.rect_data['rough_std'] = self.rough_std_spin.value() *1e-9
        self.rect_data['rough_acl'] = self.rough_acl_spin.value() *1e-9
        self.rect_data['ctype'] = self.ctype_combo.currentIndex() + 1
        self.rect_data['tol_std'] = self.tol_std_spin.value()
        self.rect_data['tol_acl'] = self.tol_acl_spin.value()
        
        self.canvas.update()

    def _safe_float(self, text, default):
        try:
            return float(text) if text.strip() else default
        except ValueError:
            return default

    def load_initial_material_values(self):
        mat = self.rect_data.get('material', 'Air')
        if mat in self.material_presets:
            eps, mu, sig = self.material_presets[mat]
        else:
            eps = self.rect_data.get('permittivity', 1.0)
            mu = self.rect_data.get('permeability', 1.0)
            sig = self.rect_data.get('conductivity', 0.0)
        
        self.eps_input.setText(str(eps))
        self.mu_input.setText(str(mu))
        self.sigma_input.setText(str(sig))

    def update_material_fields(self, material):
        if material in self.material_presets:
            eps, mu, sig = self.material_presets[material]
            self.eps_input.setText(str(eps))
            self.mu_input.setText(str(mu))
            self.sigma_input.setText(str(sig))
        self.update_live_preview()


    def update_color_button(self):
        self.color_button.setStyleSheet(f"background-color: {self.current_color.name()}; border: 1px solid #333;")

    def choose_color(self):
        color = QColorDialog.getColor(self.current_color, self, "Choose Color")
        if color.isValid():
            self.current_color = color
            self.update_color_button()
            self.update_live_preview()

    def reject(self):
        self.rect_data.clear()
        self.rect_data.update(self.original_data)
        if self.canvas:
            self.canvas.update()
        super().reject()

    def handle_delete(self):
        self.delete_flag = True
        self.accept()

    def accept(self):
        props = self.get_properties()
        self.properties_updated.emit(props)
        super().accept()

    def get_properties(self):
        props = {
            'name': self.name_input.text().strip() or 'W_1',
            'material': self.material_combo.currentText(),
            'color': self.current_color,
            'permittivity': self._safe_float(self.eps_input.text(), 1.0),
            'permeability': self._safe_float(self.mu_input.text(), 1.0),
            'conductivity': self._safe_float(self.sigma_input.text(), 0.0),
            'rough_toggle': self.rough_toggle_check.isChecked(),
            'rough_std': self.rough_std_spin.value() * 1e-9,
            'rough_acl': self.rough_acl_spin.value() * 1e-9,
            'ctype': self.ctype_combo.currentIndex() + 1,
            'tol_std': self.tol_std_spin.value(),
            'tol_acl': self.tol_acl_spin.value(),
            'grid_x': self.x_spin.value() * 1e-6,
            'grid_y': self.y_spin.value() * 1e-6,
            'grid_width': self.width_spin.value() * 1e-6,
            'grid_height': self.height_spin.value() * 1e-6,
        }
        if self.delete_flag: props["delete_flag"] = True
        return props