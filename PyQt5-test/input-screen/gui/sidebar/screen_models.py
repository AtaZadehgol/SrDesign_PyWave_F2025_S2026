class ProblemDefinitionScreen:
    def __init__(self, name, canvas_data=None):
        self.name = name
        self.canvas_data = canvas_data or {}

    def to_dict(self):
        return {
            'name': self.name,
            'canvas_data': self.canvas_data
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data.get('name', ''),
            canvas_data=data.get('canvas_data', {})
        )

class ResultScreen:
    def __init__(
        self,
        name,
        result_files=None,
        results_path=None,
        simulation_type=None,
        view_type="chart",
        selected_variables=None,
        active_variable=None,
    ):
        self.name = name
        self.result_files = result_files or []
        self.results_path = results_path  # Path to Results directory
        self.simulation_type = simulation_type or "Wave Impedance"  # Type of simulation
        self.view_type = view_type or "chart"
        self.selected_variables = selected_variables or []
        self.active_variable = active_variable

    def to_dict(self):
        return {
            'name': self.name,
            'result_files': self.result_files,
            'results_path': self.results_path,
            'simulation_type': self.simulation_type,
            'view_type': self.view_type,
            'selected_variables': self.selected_variables,
            'active_variable': self.active_variable,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data.get('name', ''),
            result_files=data.get('result_files', []),
            results_path=data.get('results_path'),
            simulation_type=data.get('simulation_type', 'Wave Impedance'),
            view_type=data.get('view_type', 'chart'),
            selected_variables=data.get('selected_variables', []),
            active_variable=data.get('active_variable'),
        )
