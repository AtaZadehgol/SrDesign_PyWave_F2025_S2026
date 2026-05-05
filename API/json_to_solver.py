#Manager that loads JSON from GUI and configures FDTD solver

import json
from initialValues_factory import IVFactory
from metadata_writer import write_metadata
import sys
import os


class JSONToSolverManager:
    """
    High-level manager that:
    1. Loads JSON file from GUI export
    2. Selects appropriate solver strategy
    3. Validates and parses data
    4. Returns configured solver ready to run
    """
    
    def __init__(self, json_filepath):
        """
        Initialize manager with JSON file path
        
        Args:
            json_filepath: Path to JSON file exported from GUI
        """
        self.json_filepath = json_filepath
        self.data = None
        self.strategy = None
        self.initialValues = None
    
    def load_json(self):
        #Load and parse JSON file
        try:
            with open(self.json_filepath, 'r') as f:
                self.data = json.load(f)
            print(f"✓ Loaded JSON from: {self.json_filepath}")
            return True
        except FileNotFoundError:
            print(f"✗ Error: File not found: {self.json_filepath}")
            return False
        except json.JSONDecodeError as e:
            print(f"✗ Error: Invalid JSON format: {e}")
            return False
    
    def configure_InitialValues(self):
        """
        Configure Initial Values from loaded JSON data
        
        Returns:
            Configured Initial Value instance, or None if error
            And appropriate solver function
        """
        if not self.data:
            if not self.load_json():
                return None
        
        #TODO: need to get the dimension as well! assuming 2D for now
        dimension = self.data.get('dimension', '2D')

        # Extract simulation type and mode
        sim_type = self.data.get('simulation_type', 'Waveguide Propagation')
        if dimension == '2D':
            pol_mode = self.data.get('polarization_mode', 'TE')
        else:
            pol_mode = 'NA'

        
        print(f"\n=== Configuration ===")

        print(f"Dimension: {dimension}")
        
        if dimension == '2D':
            print(f"Polarization Mode: {pol_mode}")

        print(f"Simulation Type: {sim_type}")
        
        # Create appropriate strategy
        try:
            self.strategy, self.solve = IVFactory.create_strategy(sim_type, pol_mode, dimension)
            print(f"✓ Created solver strategy: {self.strategy.__class__.__name__}")
        except ValueError as e:
            print(f"✗ Error: {e}")
            return None
        
        # Validate input data
        print("\n=== Validating Input ===")
        errors = self.strategy.validate_input(self.data)
        
        if errors:
            print("✗ Validation failed:")
            for error in errors:
                print(f"  • {error}")
            return None
        else:
            print("✓ Input validation passed")
        
        # Parse and configure initial values
        print("\n=== Configuring Inital Vlaues ===")
        try:
            self.initialValues = self.strategy.parse_and_configure(self.data)
            print("✓ Initial Values configured successfully!")
            return self.initialValues, self.solve
        except NotImplementedError as e:
            print(f"✗ Error: {e}")
            return None
        except Exception as e:
            print(f"✗ Error configuring initial values: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_InitialValues(self):
        """
        Get configured initial values instance
        Returns:
            Configured intial values instance, or None if not configured
        """

        if not self.initialValues:
            self.configure_InitialValues()
        return self.initialValues
    
    def print_summary(self):
        #Print summary of configuration

        if not self.initialValues:
            print("No initialValues instance configured yet")
            return
        
        #just for user, doesn't actually do anything new
        print("\n" + "="*60)
        print("INITIAL VALUES CONFIGURATION SUMMARY")
        print("="*60)
        print(f"Simulation Type: {self.data.get('simulation_type')}")
        print(f"Polarization: {self.data.get('polarization_mode')}")
        print(f"\nGeometry:")
        print(f"  Length: {self.initialValues.x_interior_region*1e6:.2f} μm")
        print(f"  Width: {self.initialValues.y_interior_region*1e9:.2f} nm")
        print(f"\nMaterial:")
        print(f"  εᵣ (core): {self.initialValues.eps_rel_fg:.2f}")
        print(f"  εᵣ (background): {self.initialValues.eps_rel_bg:.2f}")
        print(f"\nSimulation:")
        print(f"  Frequency: {self.initialValues.f0/1e12:.1f} THz")
        print(f"  Grid: {self.initialValues.nx} × {self.initialValues.ny} cells")
        print(f"  Timesteps: {self.initialValues.nt}")
        print(f"  Duration: {self.initialValues.sim_time*1e12:.2f} ps")
        print(f"\nExpected Outputs:")
        for output in self.strategy.get_expected_outputs():
            print(f"  • {output}")
        print("="*60 + "\n")


# ===== USAGE EXAMPLE =====
def main(json_file):

    # Get the absolute path of the current file's directory
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # Get the absolute path of the parent directory
    parent_dir = os.path.dirname(current_dir)

    # Add the parent directory to sys.path
    sys.path.append(parent_dir)
    
    '''
    if len(sys.argv) < 2:
        print("Usage: python json_to_solver.py <path_to_json_file>")
        sys.exit(1)
    '''
    
    #json_file = sys.argv[1]
    
    # Create manager
    manager = JSONToSolverManager(json_file)
    
    # Configure IV class
    config, solver = manager.configure_InitialValues()
    print(solver)
    
    if config:
        # Print summary
        manager.print_summary()

        # Solver is now ready to use!
        print("✓ Solver is ready for FDTD simulation")

        try:
            solver(config)
        except Exception as e:
            print("✗ Failed to run solver - see system warnings")
            sys.stderr.write(f"ERROR: Script failed with exception: {e}\n")
            sys.exit(1)

        # Write metadata file after successful simulation
        print("\n=== Writing Metadata ===")
        sim_type = manager.data.get('simulation_type', 'Unknown')
        pol_mode = manager.data.get('polarization_mode', 'TE')
        dimension = manager.data.get('dimension', '2D')

        # Get project directory from JSON data if provided
        project_dir = manager.data.get('project_directory', None)

        write_metadata(
            config=config,
            simulation_type=sim_type,
            polarization_mode=pol_mode,
            dimension=dimension,
            json_data=manager.data,
            project_dir=project_dir
        )

        '''
        #should print output as (change in the individual fns?)
        sys.stdout.write(f"status")
        sys.stdout.flush() #forces message to be sent immediately
        '''

    else:
        print("✗ Failed to configure solver")
        sys.exit(1)


if __name__ == '__main__':
    try:
        json_path = sys.argv[1]
        if len(sys.argv) < 2:
            print("Usage: python json_to_solver.py <path_to_json_file>")
            sys.exit(1)
        main(json_path)
    except Exception as e:
        sys.stderr.write(f"ERROR: Script failed with exception: {e}\n")
        sys.stderr.flush()
