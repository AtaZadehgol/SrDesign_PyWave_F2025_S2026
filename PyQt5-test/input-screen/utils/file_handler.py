# ============================================================================
# File: utils/file_handler.py
"""
File handling utilities for EM Wave Visualization Tool
"""
import json
import os
import shutil
import subprocess
from pathvalidate import sanitize_filename
import platform
from PyQt5.QtWidgets import QFileDialog, QMessageBox


class FileHandler:
    """Handles all file operations for the application"""

    def __init__(self):
        self.help_dir = os.path.join(os.path.dirname(__file__), "..", "help_pdfs")
        self.project_dir_path = None
        self.results_dir_path = None
        self.archive_dir_path = None
        self.project_metadata_path = None
        self.config_path = None
        self._archive_dir_name = "Archive"
        self._results_dir_name = "Results"
        self._config_name = "Simulation_Config.json"
        self._project_metadata_name = "project_metadata.json"

    def init_dirs(self, project_dir):
        self.project_dir_path = os.path.abspath(project_dir)
        self.results_dir_path = os.path.join(self.project_dir_path, self._results_dir_name)
        self.archive_dir_path = os.path.join(self.project_dir_path, self._archive_dir_name)
        self.project_metadata_path = os.path.join(self.project_dir_path, self._project_metadata_name)
        self.config_path = os.path.join(self.project_dir_path, self._config_name)

    def save_project_dialog(self):
        """Prompt for project folder path in one dialog and return directory path"""
        selected_path, _ = QFileDialog.getSaveFileName(
            None,
            "Save Project As Folder",
            "",
            "Folders (*)",
        )
        if not selected_path:
            return None

        selected_path = os.path.normpath(selected_path)
        parent_dir = os.path.dirname(selected_path)
        project_name = os.path.basename(selected_path).strip()
        if not project_name:
            return None

        cleaned_project_name = sanitize_filename(project_name)
        if not cleaned_project_name:
            return None

        return os.path.join(parent_dir, cleaned_project_name)

    def save_config_dialog(self):
        """Prompt for project folder path in one dialog and return directory path"""
        selected_path, _ = QFileDialog.getSaveFileName(
            None,
            "Save Config as a JSON File",
            "",
            "JSON Files (*.json)",
        )
        if not selected_path:
            return None

        selected_path = os.path.normpath(selected_path)
        parent_dir = os.path.dirname(selected_path)
        config_name = os.path.basename(selected_path).strip()
        if not config_name:
            return None

        cleaned_config_name = sanitize_filename(config_name)
        if not cleaned_config_name:
            return None

        self.config_path = os.path.join(parent_dir, cleaned_config_name)

        return self.config_path

    def load_project_dialog(self):
        """Show load project dialog"""
        filename, _ = QFileDialog.getOpenFileName(None, "Load Project", "", "JSON Files (*.json)")
        if filename is not None:
            self.init_dirs(os.path.dirname(filename))
        return filename

    def export_solver_dialog(self):
        """Show export solver data dialog"""
        filename, _ = QFileDialog.getSaveFileName(
            None, "Export Solver Input", "", "JSON Files (*.json);;All Files (*)"
        )
        return filename

    def save_project(self, project_dir, data):
        """Create project directory structure and save config JSON"""
        try:
            self.init_dirs(project_dir)
            os.makedirs(self.project_dir_path, exist_ok=True)
            return self.save_config(self.config_path, data)
        except Exception as e:
            QMessageBox.critical(None, "Save Error", f"Failed to save project: {str(e)}")
            return False

    def save_config(self, filepath, data):
        """Save configuration JSON to specified filepath"""
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to save configuration: {str(e)}")
            return False

    def load_project(self, filename):
        """Load project data from file"""
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except Exception as e:
            QMessageBox.critical(None, "Load Error", f"Failed to load project: {str(e)}")
            return None

    def export_solver_data(self, filename, data):
        """Export data for solver"""
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            QMessageBox.critical(None, "Export Error", f"Failed to export data: {str(e)}")
            return False

    def get_help_pdf(self):
        """Get the help PDF from the tutorials folder"""
        base = os.path.dirname(os.path.abspath(__file__))
        pdf_path = os.path.join(base, "..", "tutorials", "help_example.pdf")
        return os.path.normpath(pdf_path)

    def open_pdf(self, filepath):
        """Open PDF in system default viewer"""
        system = platform.system()
        try:
            if system == 'Windows':
                os.startfile(filepath)
            elif system == 'Darwin':  # macOS
                subprocess.Popen(['open', filepath])
            else:  # Linux
                subprocess.Popen(['xdg-open', filepath])
            return True
        except Exception as e:
            QMessageBox.warning(None, "Error", f"Could not open PDF: {str(e)}")
            return False

    def archive_project(self, archive_path):
            try:
                os.makedirs(archive_path, exist_ok=True)

                if self.config_path and os.path.isfile(self.config_path):
                    shutil.copy2(self.config_path, archive_path)

                if self.results_dir_path and os.path.isdir(self.results_dir_path):
                    shutil.copytree(
                        self.results_dir_path,
                        os.path.join(archive_path, os.path.basename(self.results_dir_path)),
                        dirs_exist_ok=True,
                    )

                if self.project_metadata_path and os.path.isfile(self.project_metadata_path):
                    shutil.copy2(self.project_metadata_path, archive_path)
            except Exception as e:
                raise RuntimeError(f"Failed to archive project to '{archive_path}': {e}") from e

    def get_archived_names(self):
        """Get list of archived result names"""
        if (self.archive_dir_path is None) or (not os.path.exists(self.archive_dir_path)):
            return []
        else:
            return [name for name in os.listdir(self.archive_dir_path) if os.path.isdir(os.path.join(self.archive_dir_path, name))]
