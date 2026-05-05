# ============================================================================
# File: gui/menu_handler.py
"""
Menu bar creation and all menu action handlers.
Handles file operations, imports, help, and application lifecycle.
"""

from PyQt5.QtWidgets import QAction, QFileDialog, QMessageBox
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
import os
import sys


class MenuHandler:
    """Handles all menu bar operations for the main window"""

    def __init__(self, main_window):
        self.main_window = main_window
        self.file_handler = main_window.file_handler

    def create_menu_bar(self):
        """Create the complete menu bar with all menus and actions"""
        menubar = self.main_window.menuBar()

        # File Menu
        file_menu = menubar.addMenu("File")

        new_action = QAction("New Project (Restart)", self.main_window)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.restart_application)
        file_menu.addAction(new_action)

        save_restart_action = QAction("Save and Restart", self.main_window)
        save_restart_action.setShortcut("Ctrl+Shift+S")
        save_restart_action.triggered.connect(self.save_and_restart)
        file_menu.addAction(save_restart_action)

        file_menu.addSeparator()

        save_action = QAction("Save Project", self.main_window)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)

        save_config_action = QAction("Save Config", self.main_window)
        save_config_action.triggered.connect(self.save_config)
        file_menu.addAction(save_config_action)

        save_as_action = QAction("Save As", self.main_window)
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)

        load_action = QAction("Load Project", self.main_window)
        load_action.setShortcut("Ctrl+O")
        load_action.triggered.connect(self.load_project)
        file_menu.addAction(load_action)

        file_menu.addSeparator()

        export_action = QAction("Export to Solver", self.main_window)
        export_action.triggered.connect(self.export_to_solver)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self.main_window)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.main_window.close)
        file_menu.addAction(exit_action)

        # Simulation Parameters Menu
        settings_menu = menubar.addMenu("Simulation Parameters")

        advanced_action = QAction("Advanced Parameters...", self.main_window)
        advanced_action.setShortcut("Ctrl+P")
        advanced_action.triggered.connect(self.main_window.open_advanced_parameters)
        settings_menu.addAction(advanced_action)

        # Help Menu
        help_menu = menubar.addMenu("Help")

        user_guide_action = QAction("User Guide", self.main_window)
        user_guide_action.setShortcut("F1")
        user_guide_action.triggered.connect(self.open_help)
        help_menu.addAction(user_guide_action)

        video_links_action = QAction("Video Links", self.main_window)
        video_links_action.triggered.connect(self.open_video_links)
        help_menu.addAction(video_links_action)
        
    # ========================================================================
    # File Menu Actions
    # ========================================================================

    def restart_application(self):
        """Restart application and return to welcome screen"""
        reply = QMessageBox.question(
            self.main_window,
            "Restart Application",
            "Are you sure you want to restart? All unsaved changes will be lost.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:
            QApplication.quit()
            os.execl(sys.executable, sys.executable, *sys.argv)

    def save_and_restart(self):
        """Save current project then restart"""
        project_dir = self.file_handler.save_project_dialog()
        if project_dir:
            data = self.main_window.canvas.get_solver_data()
            data["simulation_type"] = self.main_window.exp_combo.currentText()
            data["polarization_mode"] = ("TE" if "TE" in self.main_window.mode_combo.currentText() else "TM")
            data['advanced_parameters'] = self.main_window.advanced_params

            if self.file_handler.save_project(project_dir, data):
                self.main_window.statusBar().showMessage(f"Project saved to {project_dir}")
                # Now restart
                QApplication.quit()
                os.execl(sys.executable, sys.executable, *sys.argv)

    def save_project(self):
        """Save project to JSON file"""
        project_dir = self.main_window.simulation_manager.current_project_dir
        if project_dir is None:
            project_dir = self.file_handler.save_project_dialog()

        self._save_project_to_dir(project_dir)

    def save_project_as(self):
        """Save project to a new location"""
        project_dir = self.file_handler.save_project_dialog()
        self._save_project_to_dir(project_dir)

    def _build_project_payload(self):
        """Collect the current UI state into the project payload."""
        data = self.main_window.canvas.get_solver_data()
        data["simulation_type"] = self.main_window.exp_combo.currentText()
        data["polarization_mode"] = ("TE" if "TE" in self.main_window.mode_combo.currentText() else "TM")
        data["advanced_parameters"] = self.main_window.advanced_params
        return data

    def _save_project_to_dir(self, project_dir):
        """Persist project data if a destination was selected."""
        if not project_dir:
            return False

        data = self._build_project_payload()
        if self.file_handler.save_project(project_dir, data):
            self.main_window.simulation_manager.current_project_dir = project_dir
            self.main_window.statusBar().showMessage(f"Project saved to {project_dir}")
            return True

        return False

    def save_config(self):
        """Save current simulation configuration to JSON (without geometry)"""

        reply = QMessageBox.question(
            self.main_window,
            "Configuration Only",
            "This configuration save does not include results.\n\n"
            "When you run a simulation, the configuration file will be "
            "recreated in the specified location before the run executes.\n\n"
            "Results will only be associated with simulation runs.\n\n"
            "Do you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )

        filename = self.file_handler.save_config_dialog()

        if reply == QMessageBox.Yes and filename is not None:
            data = self.main_window.canvas.get_solver_data()
            data["simulation_type"] = self.main_window.exp_combo.currentText()
            data["polarization_mode"] = (
                "TE" if "TE" in self.main_window.mode_combo.currentText() else "TM"
            )
            if self.file_handler.save_config(filename, data):
                self.main_window.statusBar().showMessage(
                    f"Configuration saved to {filename}"
                )

    def load_project(self):
        """Load project from JSON file"""
        filename = self.file_handler.load_project_dialog()
        if filename:
            data = self.file_handler.load_project(filename)
            if data:
                self.main_window.canvas.load_from_data(data)
                if "simulation_type" in data:
                    self.main_window.exp_combo.setCurrentText(data["simulation_type"])
                if "polarization_mode" in data:
                    mode = data.get("polarization_mode", "TE")
                    self.main_window.mode_combo.blockSignals(True)
                    self.main_window.mode_combo.setCurrentText(
                        "TE Mode" if mode == "TE" else "TM Mode"
                    )
                    self.main_window.mode_combo.blockSignals(False)
                    
                # sync ribbon explicitly
                self.main_window.ribbon_widget.set_mode(self.main_window.mode_combo.currentText())
                
                if "grid_spacing" in data:
                    self.main_window.ribbon_widget.delta_x_spin.setValue(
                        data["grid_spacing"].get("delta_x", 10)
                    )
                    self.main_window.ribbon_widget.delta_y_spin.setValue(
                        data["grid_spacing"].get("delta_y", 10)
                    )
                if 'advanced_parameters' in data:
                    self.main_window.advanced_params = data['advanced_parameters']
                    self.main_window.canvas.set_num_cpml(data['advanced_parameters'].get('num_cpml', 20))
                self.main_window.statusBar().showMessage(f"Project loaded from {filename}")

                # Wire up results if the project directory has them
                project_dir = os.path.dirname(filename)
                self.main_window.simulation_manager.current_project_dir = project_dir
                metadata_path = os.path.join(project_dir, "project_metadata.json")
                results_dir = os.path.join(project_dir, "Results")
                if os.path.isfile(metadata_path) and os.path.isdir(results_dir):
                    self.main_window.preload_results_widgets(project_dir)

                self.main_window.statusBar().showMessage(
                    f"Project loaded from {filename}"
                )

    def export_to_solver(self):
        """Export current project data to solver format"""
        data = self.main_window.canvas.get_solver_data()
        data["simulation_type"] = self.main_window.exp_combo.currentText()
        data["polarization_mode"] = ("TE" if "TE" in self.main_window.mode_combo.currentText() else "TM")
        data['advanced_parameters'] = self.main_window.advanced_params

        project_dir = self.main_window.simulation_manager.current_project_dir
        if project_dir is None:
            project_dir = self.file_handler.save_project_dialog()
        if project_dir:
                self.file_handler.save_project(project_dir, data)
                self.main_window.statusBar().showMessage(f"Exported to {project_dir}/simulation_config.json")

                mode = data["polarization_mode"]
                sim_type = data["simulation_type"]
                QMessageBox.information(
                    self.main_window,
                    "Export Complete",
                    f"Data exported successfully.\n\n"
                    f"Simulation Type: {sim_type}\n"
                    f"Polarization Mode: {mode}\n"
                    f"Rectangles: {len(data['geometry']['rectangles'])}\n"
                    f"Sources: {len(data['sources'])}\n"
                    f"Measurement Points: {len(data['measurement_points'])}\n"
                    f"Grid: Δx={data['geometry']['grid_spacing']['delta_x']}, "
                    f"Δy={data['geometry']['grid_spacing']['delta_y']}\n"
                    f"Expected outputs:\n"
                    f"  {'ey_te_zwave.npy, hz_te_zwave.npy' if mode == 'TE' else 'ez_tm_zwave.npy, hy_tm_zwave.npy'}",
                )

        self.main_window.simulation_manager.current_project_dir = project_dir
        self.main_window.run_simulation()

    # ========================================================================
    # Import Menu Actions
    # ========================================================================

    def import_file(self, file_format):
        """Import file in various formats (placeholder for future implementation)"""
        filename, _ = QFileDialog.getOpenFileName(
            self.main_window, f"Import {file_format} File", ""
        )
        if filename:
            self.main_window.statusBar().showMessage(
                f"Import {file_format}: {filename} (Feature in development)"
            )
            QMessageBox.information(
                self.main_window,
                "Import",
                f"Import for {file_format} files will be implemented in future version.",
            )

    # ========================================================================
    # Help Menu Actions
    # ========================================================================

    def open_help(self):
        """Open help PDF"""
        pdf_path = self.file_handler.get_help_pdf()
        if pdf_path and os.path.exists(pdf_path):
            self.file_handler.open_pdf(pdf_path)
            self.main_window.statusBar().showMessage(
                f"Opened user guide: {os.path.basename(pdf_path)}"
            )
        else:
            QMessageBox.information(
                self.main_window,
                "Guide Unavailable",
                "The guide could not be found.\n ",
            )


    def open_video_links(self):
        """Pop up window with copy, pastable demo video links"""
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setWindowTitle("Links to demo videos - also in user guide")
        msgBox.setText(
                    "Demo 1: https://youtu.be/GA7z-kR5_Uk"
                    f"\n - In depth 2DTE wave impedance\n\n"
                    f"Demo 2: https://youtu.be/1lyCq_o03E0"
                    f"\n - 2DTM wave impedance with multiple waveguides\n\n"
                    f"Demo 3: https://youtu.be/1WU8xoqhD1A"
                    f"\n - 2DTE scattering loss with archiving and restarting\n\n"
                )
        #  Make text copyable
        msgBox.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        msgBox.setStandardButtons(QMessageBox.Ok)
        msgBox.exec_()
