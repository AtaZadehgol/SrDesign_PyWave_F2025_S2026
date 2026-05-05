from PyQt5.QtCore import QThread, pyqtSignal
import subprocess
import sys
import os 
from gui.progress_tags import iter_grouped

class SolverWorker(QThread):
    finished = pyqtSignal(int)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    
    def __init__(self, json_filepath):
        super().__init__()
        self.json_filepath = json_filepath
        self.process = None
        
        # Locate the solver script
        current_file_path = os.path.dirname(os.path.abspath(__file__)) 
        sr_dir = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path))) 
        self.solver_script = os.path.join(sr_dir, 'API', 'json_to_solver.py')

        # Read the project directory from the JSON config so we can
        # report the correct results path and use it as the working dir.
        self.project_dir = None
        try:
            import json as _json
            with open(self.json_filepath, 'r') as _f:
                _data = _json.load(_f)
            self.project_dir = _data.get('project_directory', None)
        except Exception:
            pass

    def run(self):
        try:
            json_abs_path = os.path.abspath(self.json_filepath)

            self.progress.emit(f"[INFO:] Running solver via: {self.solver_script}")
            if self.project_dir:
                self.progress.emit(f"[INFO:] Project Directory: {self.project_dir}")

            self.process = subprocess.Popen(
                [sys.executable, '-u', self.solver_script, json_abs_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
            
            iter_grouped(self.process.stdout, self.progress.emit)
 
            self.process.wait()

            # Check for errors in stderr
            stderr_data = self.process.stderr.read()
            if stderr_data:
                self.progress.emit(f"[SECTION: System Warnings]\n{stderr_data.strip()}")

            if self.process.returncode == 0 and self.project_dir:
                results_path = os.path.join(self.project_dir, 'Results')
                self.progress.emit(f" ✓ Results saved to: {results_path} - go to the 'Results' Tab for graphs.")
            
            self.finished.emit(self.process.returncode)

        except Exception as e:
            self.error.emit(str(e))
            self.finished.emit(-1)