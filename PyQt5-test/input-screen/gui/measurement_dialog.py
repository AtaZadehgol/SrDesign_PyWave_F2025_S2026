from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QGroupBox, QColorDialog, QFormLayout, QDoubleSpinBox, QGridLayout,
    QTabWidget, QWidget, QRadioButton, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QColor, QDoubleValidator
import copy

class MeasurementEditDialog(QDialog):
    """Edit dialog for measurement point properties via double-click or right-click"""
    
    # Signal to notify when properties are updated
    properties_updated = pyqtSignal(dict)
    shape_mode_changed = pyqtSignal(str)  # mode

    def __init__(self, measurement_data, delta_x, canvas=None, parent=None):
        super().__init__(parent)
        self.measurement_data = measurement_data
        self.delta_x = delta_x
        self.canvas = canvas  # Need canvas reference for live preview
        self.delete_flag = False  # deletion support
        self.setWindowTitle(f"Edit {measurement_data.get('name', 'Measurement Point')}")
        self.setModal(True)
        self.setMinimumWidth(450)

        self.original_data = copy.deepcopy(measurement_data)

        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)

        # --- Shape Section (point or line) ---
        shape_group = QGroupBox("Measurement Shape")
        shape_layout = QHBoxLayout()
        shape_layout.setSpacing(2)

        self.saved_shape = self.measurement_data.get('shape', 'Point')
        
        self.point_btn = QRadioButton("Point")
        self.point_btn.setChecked(self.saved_shape == 'Point')
        self.point_btn.toggled.connect(lambda checked: self.on_shape_mode_changed('Point') if checked else None)
        shape_layout.addWidget(self.point_btn)
        
        self.line_btn = QRadioButton("Line")
        self.line_btn.setChecked(self.saved_shape == 'Line')
        self.line_btn.toggled.connect(lambda checked: self.on_shape_mode_changed('Line') if checked else None)
        shape_layout.addWidget(self.line_btn)

        self.surface_btn = QRadioButton("Surface")
        self.surface_btn.setChecked(self.saved_shape == 'Surface')
        self.surface_btn.toggled.connect(lambda checked: self.on_shape_mode_changed('Surface') if checked else None)
        shape_layout.addWidget(self.surface_btn)

        shape_group.setLayout(shape_layout)
        layout.addWidget(shape_group)

        # --- Identification Section ---
        name_group = QGroupBox("Identification")
        name_layout = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setText(self.measurement_data.get('name', 'Measurement Point 1'))
        self.name_input.setPlaceholderText("Enter measurement point name...")
        self.name_input.textChanged.connect(self.update_live_preview)
        name_layout.addRow("Name:", self.name_input)
        name_group.setLayout(name_layout)
        layout.addWidget(name_group)

        # --- Position Section (Micrometers) ---
        # Get current position - ensure we convert meters to µm for UI display
        grid_x_um = self.measurement_data.get('grid_x', 0.0) * 1e6
        grid_y_um = self.measurement_data.get('grid_y', 0.0) * 1e6

        grid_x2_um = self.measurement_data.get('grid_x2', self.measurement_data.get('grid_x', 0.0)) * 1e6
        grid_y2_um = self.measurement_data.get('grid_y2', self.measurement_data.get('grid_y', 0.0)) * 1e6

        self.fixed_width = grid_x2_um - grid_x_um
        self.fixed_height = grid_y2_um - grid_y_um

        #important to know direction for this - only relevant if they select 'Line'
        self.direction = 'Diagonal'

        if grid_x_um != grid_x2_um:
            self.direction = 'Horizontal'
        if grid_y_um != grid_y2_um:
            if self.direction == 'Horizontal':  #x and y coords differ
                self.direction = 'Diagonal'
            else:
                self.direction = 'Vertical'     #just y coords differ

        position_group = QGroupBox("Position (Micrometers)")
        position_layout = QGridLayout()
        step = self.delta_x * 1e6

        # X coordinate
        position_layout.addWidget(QLabel("X:"), 0, 0)
        self.x_spin = QDoubleSpinBox()
        self.x2_spin = QDoubleSpinBox()  # declare this now
        self.x_spin.setRange(0, 100000)  
        self.x_spin.setSingleStep(step)  # Stepping by 0.05 µm
        self.x_spin.setDecimals(3)
        self.x_spin.setSuffix(" µm")
        self.x_spin.setValue(grid_x_um)
        self.x_spin.setMinimumWidth(120)
        self.x_spin.valueChanged.connect(self.position_changed)
        position_layout.addWidget(self.x_spin, 0, 1)

        # Y coordinate
        position_layout.addWidget(QLabel("Y:"), 0, 2)
        self.y_spin = QDoubleSpinBox()
        self.y2_spin = QDoubleSpinBox()  # declare now
        self.y_spin.setRange(0, 100000)
        self.y_spin.setSingleStep(step)  # Stepping by 0.05 µm
        self.y_spin.setDecimals(3)
        self.y_spin.setSuffix(" µm")
        self.y_spin.setValue(grid_y_um)
        self.y_spin.setMinimumWidth(120)
        self.y_spin.valueChanged.connect(self.position_changed)
        position_layout.addWidget(self.y_spin, 0, 3)

        self.pos_label = QLabel("** (x, y) are the coordinates of where your mouse first clicked **")
        self.pos_label.setStyleSheet("font-size: 12px; color: #999;")

        position_group.setLayout(position_layout)
        layout.addWidget(position_group)
        layout.addWidget(self.pos_label)

        # --- Line Endpoint Section (only visible for line measurements) ---
        self.line_endpoint_group = QGroupBox("Measurement End Point (Micrometers)")
        line_endpoint_layout = QVBoxLayout()

        # - fixed size, for lines and surfaces -
        self.size_group = QGroupBox()
        size_layout = QHBoxLayout()
        
        self.size_fixed = False
        self.size_toggle_check = QCheckBox('Fix Size')
        self.size_toggle_check.setChecked(self.size_fixed)
        self.size_toggle_check.toggled.connect(self.size_fixed_changed)
        line_endpoint_layout.addWidget(self.size_toggle_check)

        # - direction, for lines only -
        self.dir_group = QGroupBox()
        dir_layout = QHBoxLayout()

        self.horiz_btn = QRadioButton("Horizontal")
        self.horiz_btn.setChecked(self.direction == 'Horizontal')
        self.horiz_btn.toggled.connect(lambda checked: self.direction_changed('Horizontal') if checked else None)
        dir_layout.addWidget(self.horiz_btn)

        self.vert_btn = QRadioButton("Vertical")
        self.vert_btn.setChecked(self.direction == 'Vertical')
        self.vert_btn.toggled.connect(lambda checked: self.direction_changed('Vertical') if checked else None)
        dir_layout.addWidget(self.vert_btn)

        self.diag_btn = QRadioButton("Diagonal")
        self.diag_btn.setChecked(self.direction == 'Diagonal')
        self.diag_btn.toggled.connect(lambda checked: self.direction_changed('Diagonal') if checked else None)
        dir_layout.addWidget(self.diag_btn)

        self.dir_group.setLayout(dir_layout)
        line_endpoint_layout.addWidget(self.dir_group) 

        # - coords -
        self.endpoint_coords = QGroupBox()
        endpoint_layout = QGridLayout()
 
        endpoint_layout.addWidget(QLabel("X2:"), 1, 0)
        #self.x2_spin = QDoubleSpinBox()
        self.x2_spin.setRange(0, 100000)
        self.x2_spin.setSingleStep(step)
        self.x2_spin.setDecimals(3)
        self.x2_spin.setSuffix(" µm")
        self.x2_spin.setValue(grid_x2_um)
        self.x2_spin.setMinimumWidth(120)
        self.x2_spin.setEnabled(self.direction == 'Horizontal' or self.direction == 'Diagonal')
        self.x2_spin.valueChanged.connect(self.update_live_preview)
        endpoint_layout.addWidget(self.x2_spin, 1, 1)
 
        endpoint_layout.addWidget(QLabel("Y2:"), 1, 2)
        #self.y2_spin = QDoubleSpinBox()
        self.y2_spin.setRange(0, 100000)
        self.y2_spin.setSingleStep(step)
        self.y2_spin.setDecimals(3)
        self.y2_spin.setSuffix(" µm")
        self.y2_spin.setValue(grid_y2_um)
        self.y2_spin.setMinimumWidth(120)
        self.y2_spin.setEnabled(self.direction == 'Vertical' or self.direction == 'Diagonal')
        self.y2_spin.valueChanged.connect(self.update_live_preview)
        endpoint_layout.addWidget(self.y2_spin, 1, 3)

        self.endpoint_coords.setLayout(endpoint_layout)
        line_endpoint_layout.addWidget(self.endpoint_coords)
        self.line_endpoint_group.setLayout(line_endpoint_layout)
 
        #self.line_endpoint_group.setVisible(self.saved_shape == 'Line' or self.saved_shape == 'Surface')
        layout.addWidget(self.line_endpoint_group)

        # --- Appearance ---
        color_group = QGroupBox("Appearance")
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Color:"))
        current_color = self.measurement_data.get('color', QColor(255, 0, 0))
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
        button_layout.addStretch()

        save_btn = self._create_btn("Save", "#2196F3", self.accept)
        delete_btn = self._create_btn("Delete Measurement Point", "#f44336", self.handle_delete)
        cancel_btn = self._create_btn("Cancel", "#6B6D72", self.reject)

        button_layout.addWidget(save_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self.on_shape_mode_changed(self.saved_shape)
        save_btn.clicked.connect(self.update_live_preview)

    def _create_btn(self, text, color, slot):
        btn = QPushButton(text)
        btn.setStyleSheet(f"QPushButton {{ background-color: {color}; color: white; font-weight: bold; padding: 8px 15px; border-radius: 4px; }}")
        btn.clicked.connect(slot)
        return btn

    def update_live_preview(self):
        """Update the canvas in real-time as values change"""
        if not self.canvas:
            return
        
        self.measurement_data['shape'] = self.saved_shape

        self.update_fixed_dimensions()

        # CORRECT: Convert µm from UI back to meters for simulation data
        self.measurement_data['grid_x'] = self.x_spin.value() * 1e-6
        self.measurement_data['grid_y'] = self.y_spin.value() * 1e-6

        # update data endpoints ONLY IF not a point
        if self.saved_shape != 'Point':
            self.measurement_data['grid_x2'] = self.x2_spin.value() * 1e-6
            self.measurement_data['grid_y2'] = self.y2_spin.value() * 1e-6
        else:
            self.measurement_data['grid_x2'] = self.measurement_data['grid_x']
            self.measurement_data['grid_y2'] = self.measurement_data['grid_y']

        self.measurement_data['name'] = self.name_input.text().strip() or 'Measurement Point 1'

        self.measurement_data['color'] = self.current_color
        
        self.canvas.update()


    def update_color_button(self):
        self.color_button.setStyleSheet(f"background-color: {self.current_color.name()}; border: 2px solid #333; border-radius: 4px;")

    def choose_color(self):
        color = QColorDialog.getColor(self.current_color, self, "Choose Measurement Point Color")
        if color.isValid():
            self.current_color = color
            self.update_color_button()
            self.update_live_preview()

    def reject(self):
        self.measurement_data.clear()
        self.measurement_data.update(self.original_data)
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
        shape = self.saved_shape
        props = {
            'name': self.name_input.text().strip() or 'Measurement Point 1',
            'shape': shape,
            'color': self.current_color,
            'grid_x': self.x_spin.value() * 1e-6,
            'grid_y': self.y_spin.value() * 1e-6,
        }
        #add endpoints IF not point
        if shape != 'Point':
            props['grid_x2'] = self.x2_spin.value() * 1e-6
            props['grid_y2'] = self.y2_spin.value() * 1e-6
        else:
            props['grid_x2'] = props['grid_x']
            props['grid_y2'] = props['grid_y']

        
        if self.delete_flag:
            props["delete_flag"] = True
        return props
    
    def update_fixed_dimensions(self):
        if not self.size_toggle_check.isChecked():
            self.fixed_width = self.x2_spin.value() - self.x_spin.value()
            self.fixed_height = self.y2_spin.value() - self.y_spin.value()

    def on_shape_mode_changed(self, mode):
        """Update button states and emit signal"""
        self.point_btn.setChecked(mode == 'Point')
        self.line_btn.setChecked(mode == 'Line')
        self.saved_shape = mode
        self.line_endpoint_group.setVisible(mode == 'Line' or mode == 'Surface')
        self.dir_group.setVisible(mode == 'Line')
        self.direction_changed(self.direction)
        self.update_live_preview()
        self.shape_mode_changed.emit(mode)

    def position_changed(self):
        if self.size_fixed:
            #changing coordinates makes the others shift too
            if self.saved_shape == 'Line' or 'Surface':
                new_x = self.x_spin.value() + self.fixed_width
                new_y = self.y_spin.value() + self.fixed_height

                self.x2_spin.blockSignals(True)
                self.y2_spin.blockSignals(True)
                self.x2_spin.setValue(new_x)
                self.y2_spin.setValue(new_y)
                self.x2_spin.blockSignals(False)
                self.y2_spin.blockSignals(False)
        else:
            if self.direction == 'Vertical':
                self.x2_spin.setValue(self.x_spin.value())
            if self.direction == 'Horizontal':
                self.y2_spin.setValue(self.y_spin.value())
        
        self.update_live_preview()
    
    def direction_changed(self, direction):
        self.direction = direction
        if ((not self.size_fixed) and self.saved_shape == 'Line'):
            self.x2_spin.setEnabled(direction == 'Horizontal' or direction == 'Diagonal')
            self.y2_spin.setEnabled(direction == 'Vertical' or direction == 'Diagonal')

    def size_fixed_changed(self):
        self.size_fixed = self.size_toggle_check.isChecked()
        self.x2_spin.setEnabled(not self.size_fixed)
        self.y2_spin.setEnabled(not self.size_fixed)
        if ((not self.size_fixed) and self.saved_shape == 'Line'):
            self.direction_changed(self.direction)