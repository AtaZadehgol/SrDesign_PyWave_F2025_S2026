# ============================================================================
# File: gui/advanced_params_dialog.py
"""
Advanced Parameter Dialog for EM Wave Visualization Tool
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QDoubleSpinBox, QComboBox, QGridLayout,
                             QTabWidget, QWidget, QGroupBox, QCheckBox, QSpinBox,
                             QAction, QMessageBox, QApplication, QFormLayout, QLineEdit)
from PyQt5.QtGui import QColor, QDoubleValidator
from PyQt5.QtCore import Qt, pyqtSignal

class AdvancedParametersDialog(QDialog):
    """Dialog for advanced simulation parameters"""

    #signals
    global_roughness = pyqtSignal(object)   # to main window so canvas can call it on each rectangle
    global_sources = pyqtSignal(object)     # to main window so canvas can call it on each source

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Simulation Parameters")
        self.setModal(True)
        self.resize(500, 600)

        layout = QVBoxLayout(self)

        # Create tab widget for organization
        tabs = QTabWidget()

        # === TAB 1: General Settings ===
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)

        general_group = QGroupBox("General Simulation Conditions")
        general_grid = QGridLayout()

        resolution_group = QGroupBox("Temporal Resolution")
        resolution_grid = QGridLayout()
        resolution_grid.addWidget(QLabel("Δt coefficient:"), 0, 0)
        self.delta_t_spin = QDoubleSpinBox()
        self.delta_t_spin.setRange(0.01, 1.0)
        self.delta_t_spin.setValue(1.0)
        self.delta_t_spin.setDecimals(2)
        self.delta_t_spin.setSingleStep(0.1)
        self.delta_t_spin.setToolTip("Δt is temporal resolution (seconds/step). Δt = coeff * Δx / (base phase velocity * sqrt(2))")
        resolution_grid.addWidget(self.delta_t_spin, 0, 1)

        resolution_group.setLayout(resolution_grid)
        general_layout.addWidget(resolution_group)

        general_grid.addWidget(QLabel("Harmonics:"), 0, 0)
        self.harmonics_spin = QDoubleSpinBox()
        self.harmonics_spin.setRange(0.001, 20)
        self.harmonics_spin.setValue(1.000)
        self.harmonics_spin.setDecimals(3)
        self.harmonics_spin.setToolTip("Number of harmonics above fundamental frequency to use")
        general_grid.addWidget(self.harmonics_spin, 0, 1)

        general_grid.addWidget(QLabel("Number of Flights:"), 2, 0)
        self.num_flights_spin = QDoubleSpinBox()
        self.num_flights_spin.setRange(0.01, 100.0)
        self.num_flights_spin.setValue(2.0)
        self.num_flights_spin.setDecimals(3)
        self.num_flights_spin.setToolTip("Number of flight times to simulate")
        general_grid.addWidget(self.num_flights_spin, 2, 1)

        general_group.setLayout(general_grid)
        general_layout.addWidget(general_group)
        general_layout.addStretch()

        tabs.addTab(general_tab, "General")

        # === TAB 2: Domain Conditions ===
        domain_tab = QWidget()
        domain_layout = QVBoxLayout(domain_tab)

        boundary_group = QGroupBox("Boundary Conditions")
        boundary_grid = QGridLayout()

        boundary_grid.addWidget(QLabel("CPML Layers:"), 0, 0)
        self.num_cpml_spin = QSpinBox()
        self.num_cpml_spin.setRange(0, 50)
        self.num_cpml_spin.setValue(20)
        self.num_cpml_spin.setToolTip("Number of CPML absorbing boundary layers")
        boundary_grid.addWidget(self.num_cpml_spin, 0, 1)

        #removed buffer wavelength option
        '''
        boundary_grid.addWidget(QLabel("Buffer Wavelength (λ):"), 2, 0)
        self.buffer_wavelengths_spin = QDoubleSpinBox()
        self.buffer_wavelengths_spin.setRange(0.01, 100.0)
        self.buffer_wavelengths_spin.setValue(2.0)
        self.buffer_wavelengths_spin.setDecimals(1)
        self.buffer_wavelengths_spin.setToolTip("Buffer between interior region and CPML")
        boundary_grid.addWidget(self.buffer_wavelengths_spin, 2, 1)
        '''

        boundary_group.setLayout(boundary_grid)
        domain_layout.addWidget(boundary_group)

        bg_group = QGroupBox("Background/Cladding Material")
        bg_grid = QGridLayout()

        bg_grid.addWidget(QLabel("Relative Permittivity:"), 0, 0)
        self.eps_rel_bg_spin = QDoubleSpinBox()
        self.eps_rel_bg_spin.setRange(1.0, 20.0)
        self.eps_rel_bg_spin.setValue(2.25)  # 1.5^2 default
        self.eps_rel_bg_spin.setDecimals(3)
        self.eps_rel_bg_spin.setToolTip("Background εᵣ (e.g., 2.25 for n=1.5)")
        bg_grid.addWidget(self.eps_rel_bg_spin, 0, 1)

        bg_grid.addWidget(QLabel("Relative Permeability:"), 1, 0)
        self.mu_rel_bg_spin = QDoubleSpinBox()
        self.mu_rel_bg_spin.setRange(0.1, 10.0)
        self.mu_rel_bg_spin.setValue(1.0)
        self.mu_rel_bg_spin.setDecimals(2)
        bg_grid.addWidget(self.mu_rel_bg_spin, 1, 1)

        bg_group.setLayout(bg_grid)
        domain_layout.addWidget(bg_group)
        domain_layout.addStretch()

        tabs.addTab(domain_tab, "Domain")

        # === TAB 3: Roughness ===
        roughness_tab = QWidget()
        roughness_layout = QVBoxLayout(roughness_tab)

        self.rough_toggle_check = QCheckBox("Global Sidewall Roughness")
        self.rough_toggle_check.setChecked(False)
        roughness_layout.addWidget(self.rough_toggle_check)

        self.roughness_params = QGroupBox("Roughness Parameters")
        rough_grid = QGridLayout()

        rough_grid.addWidget(QLabel("Std Deviation (nm):"), 0, 0)
        self.rough_std_spin = QDoubleSpinBox()
        self.rough_std_spin.setRange(1.0, 100.0)
        self.rough_std_spin.setValue(15.0)
        self.rough_std_spin.setDecimals(1)
        rough_grid.addWidget(self.rough_std_spin, 0, 1)

        rough_grid.addWidget(QLabel("Correlation Length (nm):"), 1, 0)
        self.rough_acl_spin = QDoubleSpinBox()
        self.rough_acl_spin.setRange(10.0, 1000.0)
        self.rough_acl_spin.setValue(200.0)
        self.rough_acl_spin.setDecimals(1)
        rough_grid.addWidget(self.rough_acl_spin, 1, 1)

        rough_grid.addWidget(QLabel("Correlation Type:"), 2, 0)
        self.ctype_combo = QComboBox()
        self.ctype_combo.addItems(['Direct (Bend)', 'Inverse (Pinch)', 'Uncorrelated (Both)'])
        self.ctype_combo.setCurrentIndex(3)  # Default to 3
        rough_grid.addWidget(self.ctype_combo, 2, 1)

        rough_grid.addWidget(QLabel("Std Dev Tolerance (%):"), 3, 0)
        self.tol_std_spin = QDoubleSpinBox()
        self.tol_std_spin.setRange(1.0, 50.0)
        self.tol_std_spin.setValue(20.0)
        rough_grid.addWidget(self.tol_std_spin, 3, 1)

        rough_grid.addWidget(QLabel("Corr Length Tolerance (%):"), 4, 0)
        self.tol_acl_spin = QDoubleSpinBox()
        self.tol_acl_spin.setRange(1.0, 50.0)
        self.tol_acl_spin.setValue(20.0)
        rough_grid.addWidget(self.tol_acl_spin, 4, 1)

        apply_rough_btn = QPushButton("Apply")
        apply_rough_btn.clicked.connect(self.update_roughness)
        apply_rough_btn.setDefault(False)
        rough_grid.addWidget(apply_rough_btn)

        self.roughness_params.setLayout(rough_grid)
        self.roughness_params.setEnabled(False)
        self.rough_toggle_check.toggled.connect(self.roughness_params.setEnabled)

        roughness_layout.addWidget(self.roughness_params)
        roughness_layout.addStretch()

        tabs.addTab(roughness_tab, "Roughness")

        # === TAB 4: Source Details ===
        source_tab = QWidget()
        glob_source_layout = QVBoxLayout(source_tab)

        self.source_toggle_check = QCheckBox("Global Source Details")
        self.source_toggle_check.setChecked(False)
        glob_source_layout.addWidget(self.source_toggle_check)

        self.source_params = QGroupBox("Source Parameters")
        source_layout = QVBoxLayout()

        source_group = QGroupBox("Source Specifications")
        sourcet_layout = QFormLayout()
        self.source_type_combo = QComboBox()
        self.source_type_combo.addItems(['Gaussian Pulse', 'Wave Packet', 'Time-Harmonic'])
        self.source_type_combo.setCurrentText('Gaussian Pulse')
        #self.source_type_combo.currentTextChanged.connect(self.update_live_preview)
        sourcet_layout.addRow("Type:", self.source_type_combo)

        self.sci_validator = QDoubleValidator(0.0, 1e18, 6, self)
        self.sci_validator.setNotation(QDoubleValidator.ScientificNotation)

        self.amplitude_input = self._text_input(sourcet_layout, "Amplitude (A/m):")

        source_group.setLayout(sourcet_layout)
        source_layout.addWidget(source_group)

        self.gaussian_group = QGroupBox("Gaussian Pulse Settings")
        gauss_grid = QGridLayout()

        #Gaussian Pulse Settings
        gauss_grid.addWidget(QLabel("Signal Strength (dB):"), 0, 0)
        self.gauss_pulse_deg_spin = QDoubleSpinBox()
        self.gauss_pulse_deg_spin.setRange(-20.0, -1.0)
        self.gauss_pulse_deg_spin.setValue(-6.0)
        self.gauss_pulse_deg_spin.setDecimals(1)
        self.gauss_pulse_deg_spin.setToolTip("Frequency domain signal strength (must be negative)")
        gauss_grid.addWidget(self.gauss_pulse_deg_spin, 0, 1)

        gauss_grid.addWidget(QLabel("Peak Time Coefficient:"), 1, 0)
        self.gp_tpk_coef_spin = QDoubleSpinBox()
        self.gp_tpk_coef_spin.setRange(-20.0, 20.0)
        self.gp_tpk_coef_spin.setValue(9.0)
        self.gp_tpk_coef_spin.setDecimals(1)
        self.gp_tpk_coef_spin.setToolTip("Gaussian Pulse Peak Time Coefficient - changes when peak time is")
        gauss_grid.addWidget(self.gp_tpk_coef_spin, 1, 1)

        gauss_grid.addWidget(QLabel("Peak Spread Coefficient:"), 2, 0)
        self.gp_tsp_coef_spin = QDoubleSpinBox()
        self.gp_tsp_coef_spin.setRange(-20.0, 20.0)
        self.gp_tsp_coef_spin.setValue(1.0)
        self.gp_tsp_coef_spin.setDecimals(1)
        self.gp_tsp_coef_spin.setToolTip("Gaussian Pulse Peak Spread Coefficient - changes peak spread")
        gauss_grid.addWidget(self.gp_tsp_coef_spin, 2, 1)

        self.gaussian_group.setLayout(gauss_grid)
        source_layout.addWidget(self.gaussian_group)

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
        self.wave_packet_bw_spin.setValue(0.1)
        self.wave_packet_bw_spin.setDecimals(2)
        wp_grid.addWidget(self.wave_packet_bw_spin, 1, 1)

        wp_grid.addWidget(QLabel("Peak Time Coefficient:"), 2, 0)
        self.wp_tpk_coef_spin = QDoubleSpinBox()
        self.wp_tpk_coef_spin.setRange(-20.0, 20.0)
        self.wp_tpk_coef_spin.setValue(9.0)
        self.wp_tpk_coef_spin.setDecimals(1)
        self.wp_tpk_coef_spin.setToolTip("Wave Packet Peak Time Coefficient - changes when peak time is")
        wp_grid.addWidget(self.wp_tpk_coef_spin, 2, 1)

        wp_grid.addWidget(QLabel("Peak Spread Coefficient:"), 3, 0)
        self.wp_tsp_coef_spin = QDoubleSpinBox()
        self.wp_tsp_coef_spin.setRange(-20.0, 20.0)
        self.wp_tsp_coef_spin.setValue(2.0)
        self.wp_tsp_coef_spin.setDecimals(1)
        self.wp_tsp_coef_spin.setToolTip("Wave Packet Peak Spread Coefficient - changes peak spread")
        wp_grid.addWidget(self.wp_tsp_coef_spin, 3, 1)

        self.wavepacket_group.setLayout(wp_grid)
        source_layout.addWidget(self.wavepacket_group)

        self.wavepacket_group.setEnabled(False)

        # - Time Harmonic Settings -
        self.timeharmonic_group = QGroupBox("Time-Harmonic Settings")
        th_grid = QGridLayout()

        th_grid.addWidget(QLabel("Frequency (Hz):"), 0, 0)
        self.th_frequency_input = self._text_input(th_grid, "Frequency (Hz):", 0)

        th_grid.addWidget(QLabel("Peak Time Coefficient:"), 1, 0)
        self.th_tpk_coef_spin = QDoubleSpinBox()
        self.th_tpk_coef_spin.setRange(-20.0, 20.0)
        self.th_tpk_coef_spin.setValue(9.0)
        self.th_tpk_coef_spin.setDecimals(1)
        self.th_tpk_coef_spin.setToolTip("Gaussian Pulse Peak Time Coefficient - changes when peak time is")
        th_grid.addWidget(self.th_tpk_coef_spin, 1, 1)

        th_grid.addWidget(QLabel("Peak Spread Coefficient:"), 2, 0)
        self.th_tsp_coef_spin = QDoubleSpinBox()
        self.th_tsp_coef_spin.setRange(-20.0, 20.0)
        self.th_tsp_coef_spin.setValue(1.0)
        self.th_tsp_coef_spin.setDecimals(1)
        self.th_tsp_coef_spin.setToolTip("Gaussian Pulse Peak Spread Coefficient - changes peak spread")
        th_grid.addWidget(self.th_tsp_coef_spin, 2, 1)

        self.timeharmonic_group.setLayout(th_grid)
        source_layout.addWidget(self.timeharmonic_group)

        self.timeharmonic_group.setEnabled(False)
        source_layout.addStretch()

        #Apply button
        apply_source_btn = QPushButton("Apply")
        apply_source_btn.clicked.connect(self.update_source)
        apply_source_btn.setDefault(False)
        source_layout.addWidget(apply_source_btn)

        self.source_params.setLayout(source_layout)
        self.source_params.setEnabled(False)
        self.source_toggle_check.toggled.connect(self.source_params.setEnabled)

        glob_source_layout.addWidget(self.source_params)
        glob_source_layout.addStretch()

        tabs.addTab(source_tab, "Source Details")

        layout.addWidget(tabs)

        # Buttons
        button_layout = QHBoxLayout()

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self.reset_defaults)
        button_layout.addWidget(reset_btn)

        button_layout.addStretch()

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        button_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)
        self.source_type_combo.currentTextChanged.connect(self.enable_source_specs)

    def _text_input(self, layout, label, n=0):
        line_edit = QLineEdit()
        line_edit.setValidator(self.sci_validator)
        #line_edit.textChanged.connect(self.update_live_preview)
        if isinstance(layout, QFormLayout):
            layout.addRow(label, line_edit)
        else:
            layout.addWidget(line_edit, n, 1)
        return line_edit

    def _safe_float(self, text, default):
        try:
            return float(text) if text.strip() else default
        except ValueError:
            return default

    def load_initial_source_values(self, amp=20.0, freq=198.4e12):
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

    def reset_defaults(self):
        """Reset all parameters to Brian's defaults"""
        self.delta_t_spin(1.0)
        self.harmonics_spin.setValue(1.000)
        self.num_flights_spin.setValue(2.0)
        self.num_cpml_spin.setValue(20)
        #self.buffer_wavelengths_spin.setValue(2.0)
        self.eps_rel_bg_spin.setValue(2.25)
        self.mu_rel_bg_spin.setValue(1.0)
        self.rough_toggle_check.setChecked(False)
        self.rough_std_spin.setValue(15.0)
        self.rough_acl_spin.setValue(20)
        self.ctype_combo.setCurrentIndex(3)
        self.tol_std_spin.setValue(20.0)
        self.tol_acl_spin.setValue(20.0)
        self.source_type_combo.currentText('Gaussian Pulse')
        self.load_initial_source_values(20.0, 198.4e12)
        self.gauss_pulse_deg_spin.setValue(-6.0)
        self.wave_packet_bw_spin.setValue(0.10)

    def update_roughness(self):
        """update all waveguide's roughness parameters"""
        
        reply = QMessageBox.question(
            self,
            'Global Roughness Update',
            'Are you sure you want to update all waveguide roughness? All individual waveguide roughness settings will be lost.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            roughness = {
                'rough_toggle': self.rough_toggle_check.isChecked(),
                'rough_std': self.rough_std_spin.value() * 1e-9,  # Convert nm to m
                'rough_acl': self.rough_acl_spin.value() * 1e-9,
                'ctype': self.ctype_combo.currentIndex() + 1,  # 1, 2, or 3
                'tol_std': self.tol_std_spin.value(),
                'tol_acl': self.tol_acl_spin.value(),
            }
            self.set_global_roughness(roughness)

        else:
            return


    def update_source(self):
        """update all source's sourcewave parameters"""
        
        reply = QMessageBox.question(
            self,
            'Global Roughness Update',
            'Are you sure you want to update all sources? All individual source settings will be lost.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            s_type = self.source_type_combo.currentText()
            sinfo = {
                's_type': s_type,
                'amplitude': self._safe_float(self.amplitude_input.text(), 20.0),
            }
            if s_type == 'Gaussian Pulse':
                sinfo['gauss_pulse_deg'] = self.gauss_pulse_deg_spin.value()
                sinfo['gp_tsp_coef'] = self.gp_tsp_coef_spin.value()
                sinfo['gp_tpk_coef'] = self.gp_tpk_coef_spin.value()
            elif s_type == 'Wave Packet':
                sinfo['frequency'] = self._safe_float(self.wp_frequency_input.text(), 198.4e12)
                sinfo['wave_packet_bw'] = self.wave_packet_bw_spin.value()
                sinfo['wp_tsp_coef'] = self.wp_tsp_coef_spin.value()
                sinfo['wp_tpk_coef'] = self.wp_tpk_coef_spin.value()
            else:
                sinfo['frequency'] = self._safe_float(self.wp_frequency_input.text(), 198.4e12)
                sinfo['gp_tsp_coef'] = self.th_tsp_coef_spin.value()
                sinfo['gp_tpk_coef'] = self.th_tpk_coef_spin.value()
            
            self.set_global_source_info(sinfo)
        
        else:
            return
        
    def set_global_roughness(self, roughness):
        self.global_roughness.emit(roughness)

    def set_global_source_info(self, source_info):
        self.global_sources.emit(source_info)

    def get_parameters(self):
        """Return all advanced parameters as dictionary"""
        return {
            'delta_t_coef': self.delta_t_spin.value(),
            'harmonics': self.harmonics_spin.value(),
            'num_flights': self.num_flights_spin.value(),
            'num_cpml': self.num_cpml_spin.value(),
            #'buffer_wavelengths': self.buffer_wavelengths_spin.value(),
            'eps_rel_bg': self.eps_rel_bg_spin.value(),
            'mu_rel_bg': self.mu_rel_bg_spin.value(),
            'rough_toggle': self.rough_toggle_check.isChecked(),
            'rough_std': self.rough_std_spin.value() * 1e-9,  # Convert nm to m
            'rough_acl': self.rough_acl_spin.value() * 1e-9,
            'ctype': self.ctype_combo.currentIndex() + 1,  # 1, 2, or 3
            'tol_std': self.tol_std_spin.value(),
            'tol_acl': self.tol_acl_spin.value(),
            'source_type': self.source_type_combo.currentText(),
            'amplitude': self._safe_float(self.amplitude_input.text(), 20.0),
            'frequency': self._safe_float(self.wp_frequency_input.text(), 198.4e12),
            'gauss_pulse_deg': self.gauss_pulse_deg_spin.value(),
            'wave_packet_bw': self.wave_packet_bw_spin.value()
        }

    def set_parameters(self, params):
        """Load parameters from dictionary"""
        self.delta_t_spin.setValue(params.get('delta_t_coef', 1.00))
        self.harmonics_spin.setValue(params.get('harmonics', 1.000))
        self.num_flights_spin.setValue(params.get('num_flights', 2.0))
        self.num_cpml_spin.setValue(params.get('num_cpml', 20))
        #self.buffer_wavelengths_spin.setValue(params.get('buffer_wavelengths', 2.0))
        self.eps_rel_bg_spin.setValue(params.get('eps_rel_bg', 2.25))
        self.mu_rel_bg_spin.setValue(params.get('mu_rel_bg', 1.0))
        self.rough_toggle_check.setChecked(params.get('rough_toggle', False))
        self.rough_std_spin.setValue(params.get('rough_std', 15) * 1e9)
        self.rough_acl_spin.setValue(params.get('rough_acl', 20) * 1e9)
        self.ctype_combo.setCurrentIndex(params.get('ctype', 3) - 1)
        self.tol_std_spin.setValue(params.get('tol_std', 20.0))
        self.tol_acl_spin.setValue(params.get('tol_acl', 20.0))
        self.source_type_combo.setCurrentText(params.get('source_type', 'Gaussian Pulse'))
        self.load_initial_source_values(params.get('amplitude', 20.0), params.get('frequency', 198.4e12))
        self.gauss_pulse_deg_spin.setValue(params.get('gauss_pulse_deg', -6.0))
        self.wave_packet_bw_spin.setValue(params.get('wave_packet_bw', 0.10))