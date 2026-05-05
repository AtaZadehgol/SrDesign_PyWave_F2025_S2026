from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QComboBox, QGroupBox, QColorDialog, QFormLayout, QDoubleSpinBox, QGridLayout,
    QTabWidget, QWidget, QRadioButton, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QPoint
from PyQt5.QtGui import QColor, QDoubleValidator
import copy

class SourceEditDialog(QDialog):
    """Edit dialog for source point properties via double-click or right-click"""
    
    # Signal to notify when properties are updated
    properties_updated = pyqtSignal(dict)
    shape_mode_changed = pyqtSignal(str)  # mode

    def __init__(self, source_data, delta_x, canvas=None, parent=None):
        super().__init__(parent)
        self.source_data = source_data
        self.delta_x = delta_x
        self.canvas = canvas  # Need canvas reference for live preview
        self.delete_flag = False  # deletion support
        self.setWindowTitle(f"Edit {source_data.get('name', 'Source')}")
        self.setModal(True)
        self.setMinimumWidth(450)

        self.original_data = copy.deepcopy(source_data)

        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)

        #create tabs for widget organization
        tabs = QTabWidget()

        # **** General Source Specifications ****
        source_group = QGroupBox("Source Specifications")
        source_layout = QFormLayout()
        self.source_type_combo = QComboBox()
        self.source_type_combo.addItems(['Gaussian Pulse', 'Wave Packet', 'Time-Harmonic'])
        self.source_type_combo.setCurrentText(self.source_data.get('source_type', 'Gaussian Pulse'))
        self.source_type_combo.currentTextChanged.connect(self.update_live_preview)
        source_layout.addRow("Type:", self.source_type_combo)
        
        self.sci_validator = QDoubleValidator(0.0, 1e18, 6, self)
        self.sci_validator.setNotation(QDoubleValidator.ScientificNotation)

        self.amplitude_input = self._text_input(source_layout, "Amplitude (A/m):")

        source_group.setLayout(source_layout)
        layout.addWidget(source_group)

        # ===== TAB 1: Geometry Info =====
        geometry_tab = QWidget()
        geometry_layout = QVBoxLayout(geometry_tab)

        # --- Shape Section (point or line) ---
        shape_group = QGroupBox("Source Shape")
        shape_layout = QHBoxLayout()
        shape_layout.setSpacing(2)

        self.saved_shape = self.source_data.get('shape', 'Point')
        
        self.point_btn = QRadioButton("Point")
        self.point_btn.setChecked(self.saved_shape == 'Point')
        self.point_btn.toggled.connect(lambda checked: self.on_shape_mode_changed('Point') if checked else None)
        shape_layout.addWidget(self.point_btn)
        
        self.line_btn = QRadioButton("Line")
        self.line_btn.setChecked(self.saved_shape == 'Line')
        self.line_btn.toggled.connect(lambda checked: self.on_shape_mode_changed('Line') if checked else None)
        shape_layout.addWidget(self.line_btn)

        shape_group.setLayout(shape_layout)
        geometry_layout.addWidget(shape_group)

        # --- Identification Section ---
        name_group = QGroupBox("Identification")
        name_layout = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setText(self.source_data.get('name', 'Source 1'))
        self.name_input.setPlaceholderText("Enter source point name...")
        self.name_input.textChanged.connect(self.update_live_preview)
        name_layout.addRow("Name:", self.name_input)
        name_group.setLayout(name_layout)
        geometry_layout.addWidget(name_group)

        # --- Position Section (Micrometers) ---
        
        # cell vs micrometer option
        unit_group = QGroupBox("Measurement Units")
        unit_layout = QHBoxLayout()
        unit_layout.setSpacing(2)

        self.saved_unit = 'Meters'
        
        # Get current position - ensure we convert meters to µm for UI display
        grid_x_um = self.source_data.get('grid_x', 0.0) * 1e6
        grid_y_um = self.source_data.get('grid_y', 0.0) * 1e6

        grid_x2_um = self.source_data.get('grid_x2', self.source_data.get('grid_x', 0.0)) * 1e6
        grid_y2_um = self.source_data.get('grid_y2', self.source_data.get('grid_y', 0.0)) * 1e6

        self.fixed_width = grid_x2_um - grid_x_um
        self.fixed_height = grid_y2_um - grid_y_um

        #important to know direction for this!
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

        # clarifiction
        self.pos_label = QLabel("** (x, y) are the coordinates of where your mouse first clicked **")
        self.pos_label.setStyleSheet("font-size: 12px; color: #999;")

        position_group.setLayout(position_layout)
        geometry_layout.addWidget(position_group)
        geometry_layout.addWidget(self.pos_label)

        # --- Line Endpoint Section (only visible for line sources) ---
        #TODO: fix?
        self.line_endpoint_group = QGroupBox("Line End Point (Micrometers)")
        line_endpoint_layout = QVBoxLayout()

        # - fixed size -
        self.size_group = QGroupBox()
        size_layout = QHBoxLayout()
        
        self.size_fixed = False
        self.size_toggle_check = QCheckBox('Fix Size')
        self.size_toggle_check.setChecked(self.size_fixed)
        self.size_toggle_check.toggled.connect(self.size_fixed_changed)
        line_endpoint_layout.addWidget(self.size_toggle_check)

        # - direction -
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
 
        self.line_endpoint_group.setVisible(self.saved_shape == 'Line')
        geometry_layout.addWidget(self.line_endpoint_group)

        # --- Appearance ---
        color_group = QGroupBox("Appearance")
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Color:"))
        current_color = self.source_data.get('color', QColor(255, 0, 0))
        if isinstance(current_color, tuple): current_color = QColor(*current_color)
        self.color_button = QPushButton()
        self.color_button.setFixedSize(60, 30)
        self.current_color = current_color
        self.update_color_button()
        self.color_button.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_button)
        color_layout.addStretch()
        color_group.setLayout(color_layout)
        geometry_layout.addWidget(color_group)

        tabs.addTab(geometry_tab, "Geometry")

        # ===== TAB 2: SOURCE DETAIL =====
        sourcewave_tab = QWidget()
        sourcewave_layout = QVBoxLayout(sourcewave_tab)
        
        # - Gaussian Settings -
        self.gaussian_group = QGroupBox("Gaussian Pulse Settings")
        gauss_grid = QGridLayout()
        
        gauss_grid.addWidget(QLabel("Signal Strength (dB):"), 0, 0)
        self.gauss_pulse_deg_spin = QDoubleSpinBox()
        self.gauss_pulse_deg_spin.setRange(-20.0, -1.0)
        self.gauss_pulse_deg_spin.setValue(self.source_data.get('gauss_pulse_deg', -6.0))
        self.gauss_pulse_deg_spin.setDecimals(1)
        self.gauss_pulse_deg_spin.setToolTip("Frequency domain signal strength (must be negative)")
        gauss_grid.addWidget(self.gauss_pulse_deg_spin, 0, 1)

        gauss_grid.addWidget(QLabel("Peak Time Coefficient:"), 1, 0)
        self.gp_tpk_coef_spin = QDoubleSpinBox()
        self.gp_tpk_coef_spin.setRange(-20.0, 20.0)
        self.gp_tpk_coef_spin.setValue(self.source_data.get('gp_tpk_coef', 9.0))
        self.gp_tpk_coef_spin.setDecimals(1)
        self.gp_tpk_coef_spin.setToolTip("Gaussian Pulse Peak Time Coefficient - changes when peak time is")
        gauss_grid.addWidget(self.gp_tpk_coef_spin, 1, 1)

        gauss_grid.addWidget(QLabel("Peak Spread Coefficient:"), 2, 0)
        self.gp_tsp_coef_spin = QDoubleSpinBox()
        self.gp_tsp_coef_spin.setRange(-20.0, 20.0)
        self.gp_tsp_coef_spin.setValue(self.source_data.get('gp_tsp_coef', 1.0))
        self.gp_tsp_coef_spin.setDecimals(1)
        self.gp_tsp_coef_spin.setToolTip("Gaussian Pulse Peak Spread Coefficient - changes peak spread")
        gauss_grid.addWidget(self.gp_tsp_coef_spin, 2, 1)
        
        self.gaussian_group.setLayout(gauss_grid)
        sourcewave_layout.addWidget(self.gaussian_group)

        self.gaussian_group.setEnabled(False)
        
        # - Wave Packet Settings -
        self.wavepacket_group = QGroupBox("Wave Packet Settings")
        wp_grid = QGridLayout()

        wp_grid.addWidget(QLabel("Frequency (Hz):"), 0, 0)
        self.wp_frequency_input = self._text_input(wp_grid, "Frequency (Hz):", 0)
        self.frequency_input = self.wp_frequency_input
        
        wp_grid.addWidget(QLabel("Bandwidth (%):"), 1, 0)
        self.wave_packet_bw_spin = QDoubleSpinBox()
        self.wave_packet_bw_spin.setRange(0.01, 1.0)
        self.wave_packet_bw_spin.setSingleStep(0.1)
        self.wave_packet_bw_spin.setValue(self.source_data.get('wave_packet_bw', 0.1))
        self.wave_packet_bw_spin.setDecimals(2)
        wp_grid.addWidget(self.wave_packet_bw_spin, 1, 1)

        wp_grid.addWidget(QLabel("Peak Time Coefficient:"), 2, 0)
        self.wp_tpk_coef_spin = QDoubleSpinBox()
        self.wp_tpk_coef_spin.setRange(-20.0, 20.0)
        self.wp_tpk_coef_spin.setValue(self.source_data.get('wp_tpk_coef', 9.0))
        self.wp_tpk_coef_spin.setDecimals(1)
        self.wp_tpk_coef_spin.setToolTip("Wave Packet Peak Time Coefficient - changes when peak time is")
        wp_grid.addWidget(self.wp_tpk_coef_spin, 2, 1)

        wp_grid.addWidget(QLabel("Peak Spread Coefficient:"), 3, 0)
        self.wp_tsp_coef_spin = QDoubleSpinBox()
        self.wp_tsp_coef_spin.setRange(-20.0, 20.0)
        self.wp_tsp_coef_spin.setValue(self.source_data.get('wp_tsp_coef', 2.0))
        self.wp_tsp_coef_spin.setDecimals(1)
        self.wp_tsp_coef_spin.setToolTip("Wave Packet Peak Spread Coefficient - changes peak spread")
        wp_grid.addWidget(self.wp_tsp_coef_spin, 3, 1)
        
        self.wavepacket_group.setLayout(wp_grid)
        sourcewave_layout.addWidget(self.wavepacket_group)

        self.wavepacket_group.setEnabled(False)

        # - Time Harmonic Settings -
        self.timeharmonic_group = QGroupBox("Time-Harmonic Settings")
        th_grid = QGridLayout()

        th_grid.addWidget(QLabel("Frequency (Hz):"), 0, 0)
        self.th_frequency_input = self._text_input(th_grid, "Frequency (Hz):", 0)
        
        th_grid.addWidget(QLabel("Peak Time Coefficient:"), 1, 0)
        self.th_tpk_coef_spin = QDoubleSpinBox()
        self.th_tpk_coef_spin.setRange(-20.0, 20.0)
        self.th_tpk_coef_spin.setValue(self.source_data.get('gp_tpk_coef', 9.0))
        self.th_tpk_coef_spin.setDecimals(1)
        self.th_tpk_coef_spin.setToolTip("Gaussian Pulse Peak Time Coefficient - changes when peak time is")
        th_grid.addWidget(self.th_tpk_coef_spin, 1, 1)

        th_grid.addWidget(QLabel("Peak Spread Coefficient:"), 2, 0)
        self.th_tsp_coef_spin = QDoubleSpinBox()
        self.th_tsp_coef_spin.setRange(-20.0, 20.0)
        self.th_tsp_coef_spin.setValue(self.source_data.get('gp_tsp_coef', 1.0))
        self.th_tsp_coef_spin.setDecimals(1)
        self.th_tsp_coef_spin.setToolTip("Gaussian Pulse Peak Spread Coefficient - changes peak spread")
        th_grid.addWidget(self.th_tsp_coef_spin, 2, 1)
        
        self.timeharmonic_group.setLayout(th_grid)
        sourcewave_layout.addWidget(self.timeharmonic_group)

        self.timeharmonic_group.setEnabled(False)

        sourcewave_layout.addStretch()
        
        tabs.addTab(sourcewave_tab, "Source Details")
        
        layout.addWidget(tabs)

        # --- Action Buttons ---
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        save_btn = self._create_btn("Save", "#2196F3", self.accept)
        delete_btn = self._create_btn("Delete Source Point", "#f44336", self.handle_delete)
        cancel_btn = self._create_btn("Cancel", "#6B6D72", self.reject)

        button_layout.addWidget(save_btn)
        button_layout.addWidget(delete_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        save_btn.clicked.connect(self.update_live_preview)
        self.source_type_combo.currentTextChanged.connect(self.enable_source_specs)
        self.load_initial_source_values()

    def _text_input(self, layout, label, n=0):
        line_edit = QLineEdit()
        line_edit.setValidator(self.sci_validator)
        line_edit.textChanged.connect(self.update_live_preview)
        if isinstance(layout, QFormLayout):
            layout.addRow(label, line_edit)
        else:
            layout.addWidget(line_edit, n, 1)
        return line_edit

    def _create_btn(self, text, color, slot):
        btn = QPushButton(text)
        btn.setStyleSheet(f"QPushButton {{ background-color: {color}; color: white; font-weight: bold; padding: 8px 15px; border-radius: 4px; }}")
        btn.clicked.connect(slot)
        return btn

    def update_live_preview(self):
        """Update the canvas in real-time as values change"""
        if not self.canvas:
            return
        
        self.source_data['shape'] = self.saved_shape

        self.update_fixed_dimensions()

        # CORRECT: Convert µm from UI back to meters for simulation data
        self.source_data['grid_x'] = self.x_spin.value() * 1e-6
        self.source_data['grid_y'] = self.y_spin.value() * 1e-6

        # update data endpoints ONLY IF line
        if self.saved_shape == 'Line':
            self.source_data['grid_x2'] = self.x2_spin.value() * 1e-6
            self.source_data['grid_y2'] = self.y2_spin.value() * 1e-6
        else:
            self.source_data['grid_x2'] = self.source_data['grid_x']
            self.source_data['grid_y2'] = self.source_data['grid_y']

        self.source_data['name'] = self.name_input.text().strip() or 'Source 1'
        self.source_data['source_type'] = self.source_type_combo.currentText()
        self.source_data['amplitude'] = self._safe_float(self.amplitude_input.text(), 20.0)
        self.source_data['frequency'] = self._safe_float(self.frequency_input.text(), 198.4e12)
        self.source_data['gauss_pulse_deg'] = self.gauss_pulse_deg_spin.value()
        self.source_data['gp_tsp_coef'] = self.gp_tsp_coef_spin.value()
        self.source_data['gp_tpk_coef'] = self.gp_tpk_coef_spin.value()
        self.source_data['wave_packet_bw'] = self.wave_packet_bw_spin.value()
        self.source_data['wp_tsp_coef'] = self.wp_tsp_coef_spin.value()
        self.source_data['wp_tpk_coef'] = self.wp_tpk_coef_spin.value()

        self.source_data['color'] = self.current_color
        
        self.canvas.update()

    def _safe_float(self, text, default):
        try:
            return float(text) if text.strip() else default
        except ValueError:
            return default

    def load_initial_source_values(self):
        amp = self.source_data.get('amplitude', 1.0)
        freq = self.source_data.get('frequency', 1.0)
        
        self.amplitude_input.setText(str(amp))
        self.wp_frequency_input.setText(str(freq))
        self.th_frequency_input.setText(str(freq))
        self.enable_source_specs()

    def enable_source_specs(self):
        s_type = self.source_type_combo.currentText()
        if (s_type == 'Wave Packet'):
            self.frequency_input = self.wp_frequency_input
        elif (s_type == 'Time-Harmonic'):
            self.frequency_input = self.th_frequency_input
            self.gp_tpk_coef_spin = self.th_tpk_coef_spin
            self.gp_tsp_coef_spin = self.th_tsp_coef_spin
        
        self.gaussian_group.setEnabled(s_type == 'Gaussian Pulse')
        self.wavepacket_group.setEnabled(s_type == 'Wave Packet')
        self.timeharmonic_group.setEnabled(s_type == 'Time-Harmonic')

    def update_color_button(self):
        self.color_button.setStyleSheet(f"background-color: {self.current_color.name()}; border: 2px solid #333; border-radius: 4px;")

    def choose_color(self):
        color = QColorDialog.getColor(self.current_color, self, "Choose Source Point Color")
        if color.isValid():
            self.current_color = color
            self.update_color_button()
            self.update_live_preview()

    def reject(self):
        self.source_data.clear()
        self.source_data.update(self.original_data)
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
            'name': self.name_input.text().strip() or 'Source 1',
            'shape': shape,
            'source_type': self.source_type_combo.currentText(),
            'amplitude': self._safe_float(self.amplitude_input.text(), 20.0),
            'color': self.current_color,
            'grid_x': self.x_spin.value() * 1e-6,
            'grid_y': self.y_spin.value() * 1e-6,
        }
        #add endpoints IF line
        if shape == 'Line':
            props['grid_x2'] = self.x2_spin.value() * 1e-6
            props['grid_y2'] = self.y2_spin.value() * 1e-6
        else:
            props['grid_x2'] = props['grid_x']
            props['grid_y2'] = props['grid_y']
        #add necessary params depending on source type
        if props['source_type'] == 'Gaussian Pulse':
            props['gauss_pulse_deg']= self.gauss_pulse_deg_spin.value()
            props['gp_tsp_coef'] = self.gp_tsp_coef_spin.value()
            props['gp_tpk_coef']=  self.gp_tpk_coef_spin.value()
        elif props['source_type'] == 'Wave Packet':
            props['frequency'] = self._safe_float(self.wp_frequency_input.text(), 198.4e12)
            props['wave_packet_bw'] = self.wave_packet_bw_spin.value()
            props['wp_tsp_coef'] = self.wp_tsp_coef_spin.value()
            props['wp_tpk_coef'] = self.wp_tpk_coef_spin.value()
        else:
            props['frequency'] = self._safe_float(self.th_frequency_input.text(), 198.4e12)
            props['gp_tsp_coef'] = self.th_tsp_coef_spin.value()
            props['gp_tpk_coef']=  self.th_tpk_coef_spin.value()
        
        if self.delete_flag:
            props["delete_flag"] = True
        return props

    def update_fixed_dimensions(self):
        if not self.size_toggle_check.isChecked():
            self.fixed_width = self.x2_spin.value() - self.x_spin.value()
            self.fixed_height = self.y2_spin.value() - self.y_spin.value()

    def on_shape_mode_changed(self, mode):
        """Update button states and emit signal"""
        #TODO: edit name depending on type? or forego line?
        self.point_btn.setChecked(mode == 'Point')
        self.line_btn.setChecked(mode == 'Line')
        self.saved_shape = mode
        self.line_endpoint_group.setVisible(mode == 'Line')
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
        self.size_fixed = not self.size_fixed
        self.x2_spin.setEnabled(not self.size_fixed)
        self.y2_spin.setEnabled(not self.size_fixed)
        self.direction_changed(self.direction)