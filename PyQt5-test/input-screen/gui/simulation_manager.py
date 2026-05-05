from PyQt5.QtWidgets import QMessageBox, QDialog
from datetime import datetime
import json
import os

from gui.solver_worker import SolverWorker
from gui.dialogs import ArchiveDialog
from utils.file_handler import FileHandler


class SimulationManager:
    """Manages simulation setup, execution, and monitoring"""

    def __init__(self, main_window):
        self.main_window = main_window
        self.solver_worker = None
        self.current_project_dir = None  # Will be set when simulation runs

    def run_simulation(self):
        """One-click simulation execution"""
        data = self.main_window.canvas.get_solver_data()

        # Validation
        if not self._validate_simulation_data(data):
            return

        # Set Basic Info
        data["simulation_type"] = self.main_window.exp_combo.currentText()
        data["polarization_mode"] = ("TE" if "TE" in self.main_window.mode_combo.currentText() else "TM")
        data["dimension"] = "2D"  # [TODO]: Get from GUI when 3D is supported

        # Use Set Advanced Parameters
        data["advanced_parameters"] = self.main_window.advanced_params

        file_handler = self.main_window.file_handler

        # Reuse existing project directory, or ask user for one
        if not self.current_project_dir:
            project_dir = file_handler.save_project_dialog()
            if not project_dir:
                return  # User cancelled
            self.current_project_dir = os.path.abspath(project_dir)

        # Ensure file-handler directory paths are initialized for reused projects.
        file_handler.init_dirs(self.current_project_dir)

        results_dir_path = file_handler.results_dir_path
        archive_dir_path = file_handler.archive_dir_path

        if results_dir_path and os.path.isdir(results_dir_path):
            overwrite_warning = QMessageBox.question(
                self.main_window,
                "Overwrite Results",
                "Running this simulation will overwrite your previous results.\n\n"
                "Would you like to archive the current results first?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                QMessageBox.Yes,
            )

            if overwrite_warning == QMessageBox.Cancel:
                return

            if overwrite_warning == QMessageBox.Yes:
                archive_dialog = ArchiveDialog(self.main_window)
                if archive_dialog.exec_() != QDialog.Accepted:
                    QMessageBox.information(
                        self.main_window,
                        "Archive Cancelled",
                        "Archiving cancelled. Simulation will not run.",
                    )
                    return

                archive_name = archive_dialog.get_archive_name()
                if not archive_name:
                    QMessageBox.warning(
                        self.main_window,
                        "Archive Error",
                        "Archive name was not provided. Simulation will not run.",
                    )
                    return

                if not archive_dir_path:
                    QMessageBox.warning(
                        self.main_window,
                        "Archive Error",
                        "Archive directory is not initialized. Simulation will not run.",
                    )
                    return

                archive_path = os.path.join(archive_dir_path, archive_name)
                try:
                    file_handler.archive_project(archive_path)
                except Exception as e:
                    QMessageBox.critical(
                        self.main_window,
                        "Archive Error",
                        f"Failed to archive existing results. Simulation will not run.\n\n{e}",
                    )
                    return


        # Clear previous results so stale files don't persist
        results_dir = os.path.join(self.current_project_dir, "Results")
        if os.path.isdir(results_dir):
            import shutil

            shutil.rmtree(results_dir)
        os.makedirs(results_dir, exist_ok=True)

        # Solver strategies read output_dir from advanced_parameters.
        data.setdefault("advanced_parameters", {})["output_dir"] = results_dir
        data["project_directory"] = self.current_project_dir

        # Auto-Save and Run
        self._save_and_run_simulation(data, self.current_project_dir)

    def _save_and_run_simulation(self, data, project_dir):
        """Saves JSON config to project directory and triggers the worker thread"""
        # Save configuration JSON in project directory
        config_filename = os.path.join(project_dir, "simulation_config.json")

        if self._save_configuration(config_filename, data):
            self.main_window.progress_text.clear()
            self.main_window.results_label.setText("")
            self.main_window.solver_output_dialog.log_widget.clear()  # clear old output log
            self.start_solver(config_filename, project_dir)

    def start_solver(self, json_filepath, project_dir):
        """Initializes and starts the background solver thread"""
        self.solver_worker = SolverWorker(json_filepath)

        self.solver_worker.finished.connect(self.on_solver_finished)
        self.solver_worker.progress.connect(self.on_solver_progress)

        self.solver_worker.start()
        self.main_window.open_solver_output()

    def _save_configuration(self, filename, data):
        """Silently save JSON config"""
        try:
            with open(filename, "w") as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            QMessageBox.critical(
                self.main_window, "Error", f"Failed to save simulation:\n{e}"
            )
            return False

    def _validate_simulation_data(self, data):
        """Ensure geometry and sources are present"""
        if (
            not data["sources"]
        ):
            QMessageBox.warning(
                self.main_window,
                "Missing Data",
                "Ensure you have a source point.",
            )
            return False
        if (
            (self.main_window.exp_combo.currentText() != 'Scattering Loss') 
            and not data["measurement_points"]
        ):
            QMessageBox.warning(
                self.main_window,
                "Missing Data",
                "Ensure you have a measurement point.",
            )
            return False
        return True

    def on_solver_progress(self, message):
        """Update GUI text box with real-time solver output"""
        self.main_window.progress_text.append(message)

    def on_solver_finished(self, return_code):
        """Handle simulation completion"""
        #clear and show blank status bar after simulation is completed
        self.main_window.statusBar().show()
        self.main_window.statusBar().clearMessage()
        if return_code == 0:
            # Update progress bar to Done and show saved path
            self.main_window.progress_text.set_status("Done!", success=True)
            self.main_window.results_label.setText(f"Files were saved to: {self.current_project_dir}/Results")

            self.main_window.progress_text.show_saved_path(
                f"Project saved to: {self.current_project_dir}"
            )

            self.main_window.progress_text.show_saved_path(
                f"Results saved to: {self.current_project_dir}/Results"
            )

            # Update Result Screen with the new project
            from pathlib import Path

            project_path = Path(self.current_project_dir)

            # Update all Result screens in sidebar with latest project path.
            result_screens = self.main_window.sidebar.get_result_screens()
            chart_screen = None
            for screen in result_screens:
                if getattr(screen, "view_type", "chart") == "chart" and chart_screen is None:
                    chart_screen = screen

            for screen in result_screens:
                screen.results_path = str(project_path)

            self.main_window.preload_results_widgets(project_path, force_reload=True)

            # Route to chart result view by default when available.
            target_screen = chart_screen or (result_screens[0] if result_screens else None)
            if target_screen:
                item = self.main_window.sidebar.find_item_for_screen(target_screen)
                if item is not None:
                    self.main_window.sidebar.setCurrentItem(item)
                # Explicitly trigger the screen switch
                self.main_window.on_sidebar_screen_selected(target_screen)


        else:
            # Update progress bar to failed
            self.main_window.progress_text.set_status("Simulation Failed.", success=False)

    def _open_results_folder(self):
        """Helper to open project folder"""
        import sys, subprocess

        if not self.current_project_dir:
            return

        try:
            folder_to_open = self.current_project_dir
            if sys.platform == "win32":
                os.startfile(folder_to_open)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder_to_open])
            else:
                subprocess.run(["xdg-open", folder_to_open])
        except Exception:
            pass

    def pause_simulation(self):
        """Pause simulation (placeholder for future implementation)"""
        self.main_window.statusBar().showMessage("Simulation paused")

    def resume_simulation(self):
        """Resume simulation (placeholder for future implementation)"""
        self.main_window.statusBar().showMessage("Simulation resumed")
