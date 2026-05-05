# ============================================================================
# File: gui/dialogs.py
"""
Dialog windows for EM Wave Visualization Tool
"""
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QDoubleSpinBox, QComboBox, QGridLayout,
                             QTabWidget, QWidget, QGroupBox, QCheckBox, QSpinBox,
                             QAction, QMessageBox, QApplication, QFormLayout, QLineEdit)
from PyQt5.QtGui import QColor, QDoubleValidator
from pathvalidate import sanitize_filename
from datetime import datetime


class MaterialPropertiesDialog(QDialog):
    """Dialog for editing material properties of selected rectangle"""

    def __init__(self, rect_data, parent=None):
        super().__init__(parent)
        self.rect_data = rect_data
        self.setWindowTitle("Material Properties")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        grid = QGridLayout()

        # Material name
        grid.addWidget(QLabel("Material:"), 0, 0)
        self.material_combo = QComboBox()
        self.material_combo.addItems(['Air', 'Copper', 'FR-4', 'Silicon', 'Teflon', 'Custom'])
        self.material_combo.setCurrentText(self.rect_data['material'])
        self.material_combo.currentTextChanged.connect(self.material_changed)
        grid.addWidget(self.material_combo, 0, 1)

        # Permittivity
        grid.addWidget(QLabel("Relative Permittivity (εr):"), 1, 0)
        self.permittivity_spin = QDoubleSpinBox()
        self.permittivity_spin.setRange(1.0, 100.0)
        self.permittivity_spin.setDecimals(2)
        self.permittivity_spin.setValue(self.rect_data['permittivity'])
        grid.addWidget(self.permittivity_spin, 1, 1)

        # Permeability
        grid.addWidget(QLabel("Relative Permeability (μr):"), 2, 0)
        self.permeability_spin = QDoubleSpinBox()
        self.permeability_spin.setRange(1.0, 100.0)
        self.permeability_spin.setDecimals(2)
        self.permeability_spin.setValue(self.rect_data['permeability'])
        grid.addWidget(self.permeability_spin, 2, 1)

        # Conductivity
        grid.addWidget(QLabel("Conductivity (S/m):"), 3, 0)
        self.conductivity_spin = QDoubleSpinBox()
        self.conductivity_spin.setRange(0.0, 1e8)
        self.conductivity_spin.setDecimals(2)
        self.conductivity_spin.setValue(self.rect_data['conductivity'])
        grid.addWidget(self.conductivity_spin, 3, 1)

        layout.addLayout(grid)

        # Buttons
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

class DomainDialog(QDialog):
    """Dialog for editing fdtd domain cell specifications"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Domain Layout")
        self.setModal(True)
        self.resize(500, 600)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        grid = QGridLayout()

        layout.addLayout(grid)
        self.setLayout(layout)

    def material_changed(self, material):
        """Update properties when predefined material is selected"""
        presets = {
            'Air': (1.0, 1.0, 0.0),
            'Copper': (1.0, 1.0, 5.8e7),
            'FR-4': (4.5, 1.0, 0.0),
            'Silicon': (11.7, 1.0, 0.0),
            'Teflon': (2.1, 1.0, 0.0)
        }

        if material in presets:
            perm, permea, cond = presets[material]
            self.permittivity_spin.setValue(perm)
            self.permeability_spin.setValue(permea)
            self.conductivity_spin.setValue(cond)

    def get_properties(self):
        """Return updated properties"""
        return {
            'material': self.material_combo.currentText(),
            'permittivity': self.permittivity_spin.value(),
            'permeability': self.permeability_spin.value(),
            'conductivity': self.conductivity_spin.value()
        }


class ArchiveDialog(QDialog):
    """Dialog for archiving project with user-specified name"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.archive_name = None
        self.setWindowTitle("Archive Project")
        self.setModal(True)
        self.resize(400, 200)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Enter archive name:"))
        self.archive_name_input = QLineEdit()
        layout.addWidget(self.archive_name_input)

        button_layout = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.validate_and_accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

    def validate_and_accept(self):
        """Validate archive name before accepting"""
        archive_name = self.archive_name_input.text().strip()

        if not archive_name:
            archive_name = f"archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        sanitized_name = sanitize_filename(archive_name)

        if not sanitized_name:
            QMessageBox.warning(
                self,
                "Invalid Name",
                f"'{archive_name}' contains only invalid characters for a directory name."
            )
            return

        # Inform user if name was modified
        if sanitized_name != archive_name:
            QMessageBox.information(
                self,
                "Invalid Characters Removed",
                f"Archive name contains invalid characters.\n"
                f"Original: {archive_name}\n"
                f"Sanitized: {sanitized_name}"
            )

        self.archive_name = sanitized_name
        self.accept()

    def get_archive_name(self):
        """Return the validated archive name"""
        return self.archive_name

