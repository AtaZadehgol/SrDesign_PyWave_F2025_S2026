"""
Strategy pattern for different solver types
Maps GUI JSON data to solver parameters
"""
from abc import ABC, abstractmethod
import os
import sys

#will need below for all classes
# Get the absolute path of the current file's directory
current_dir = os.path.dirname(os.path.abspath(__file__))
# Get the absolute path of the parent directory
parent_dir = os.path.dirname(current_dir)
# Add the parent directory to sys.path
sys.path.append(parent_dir)

class IVStrategy(ABC):
    """Abstract base class for all initial value strategies"""
    
    @abstractmethod
    def validate_input(self, data):
        """Validate that input data is correct for this solver"""
        pass
    
    @abstractmethod
    def parse_and_configure(self, data):
        """Parse JSON data and return configured Inital Values instance"""
        pass
    
    @abstractmethod
    def get_expected_outputs(self):
        """Return list of expected output files/arrays"""
        pass


class IV_Waveguide2DTE_Strategy(IVStrategy):
    """Strategy for 2D TE waveguide propagation simulations"""
    
    def __init__(self):
        # Unit conversion factor - CRITICAL for correct simulation
        # TODO: Make this configurable from GUI or JSON
        self.grid_to_meters = 1e-6  # Default: 1 grid unit = 1 micrometer
    
    def validate_input(self, data):
        """Validate waveguide-specific requirements"""
        errors = []
        
        # Check for source
        if not data.get('sources'):
            errors.append("At least one source point required")

        # Check for measurement
        if not data.get('measurement_points'):
            errors.append("At least one measurement point required")
        
        # Check polarization mode
        if data.get('polarization_mode') != 'TE':
            errors.append("This solver only supports TE mode")
        
        # Validate rectangles have material properties
        for i, rect in enumerate(data.get('geometry', {}).get('rectangles', [])):
            if 'material' not in rect:
                errors.append(f"Rectangle {i} missing material properties")
        
        return errors
    
    def parse_and_configure(self, data):
        """
        Parse GUI JSON and configure InitialValues_2DTE_Wave Initial Values
        
        """

        try:
            from solver.FDTD_2D_TE.wave_impedance.IV_2DTE_wave import InitialValues_2DTE_Wave
        except ImportError:
            raise ImportError("InitialValues_2DTE_Wave solver not available. "
                            "Make sure the initial values code is in the Python path.")
        
        # Create instance (starts with Brian's defaults)
        IV_config = InitialValues_2DTE_Wave()

        # Get most of the information we need to fill in the instance
        IV_config = fill_basic_config(IV_config, data)
        
        # === INITIALIZE IV_config ===
        # This calculates all derived parameters (delta_x, delta_t, nx, ny, nt, etc.)
        IV_config.automatedVarInit()
        

        print(f"\n=== Initial Values Configured ===")
        print(f"Waveguide: {IV_config.x_interior_region*1e6:.2f} μm × {IV_config.y_interior_region*1e9:.2f} nm")
        print(f"Permittivity: εᵣ_bg={IV_config.eps_rel_bg:.2f}") 
        print(f"Frequency: f₀={IV_config.f0/1e12:.1f} THz")
        print(f"Grid: {IV_config.nx} × {IV_config.ny} cells")
        print(f"Timesteps: {IV_config.nt}")
        print(f"Resolution: Δx={IV_config.delta_x:.2e} m, Δt={IV_config.delta_t:.2e} s")
        print(f"Source: Type {IV_config.source_type}, Amplitude {IV_config.source_amp} A/m")
        print(f"source point: ({IV_config.sx}, {IV_config.sy}) and measurement: {IV_config.cx}")
        print(f"cx {IV_config.cx}, cy {IV_config.cy}")
        print(f"y_interior_region: {IV_config.y_interior_region}, x_interior_region: {IV_config.x_interior_region}")
        print(f"========================\n")
        
        return IV_config
    
    def get_expected_outputs(self):
        """Return expected output files for TE mode"""
        #TODO: these should probably be updated file locations!
        return ['ex_te_zwave.npy', 'ey_te_zwave.npy', 'hz_te_zwave.npy']


#same as TE except ports
class IV_Waveguide2DTM_Strategy(IVStrategy):
    """Strategy for 2D TM waveguide simulations"""
    
    def __init__(self):
        self.grid_to_meters = 1e-9
    
    def validate_input(self, data):
        errors = []
        
        if not data.get('sources'):
            errors.append("At least one source point required")

        # Check for measurement
        if not data.get('measurement_points'):
            errors.append("At least one measurement point required")
        
        if data.get('polarization_mode') != 'TM':
            errors.append("This solver only supports TM mode")

        # Validate rectangles have material properties
        for i, rect in enumerate(data.get('geometry', {}).get('rectangles', [])):
            if 'material' not in rect:
                errors.append(f"Rectangle {i} missing material properties")
        
        return errors
    
    def parse_and_configure(self, data):
        """
        Parse GUI JSON and configure InitialValues_2DTM_Wave Initial Values
        all input variables the same as TE mode
        """

        try:
            from solver.FDTD_2D_TM.wave_impedance.IV_2DTM_wave import InitialValues_2DTM_Wave
        except ImportError:
            raise ImportError("InitialValues_2DTM_Wave solver not available. "
                            "Make sure the initial values code is in the Python path.")
        
        # Create instance (starts with Brian's defaults)
        IV_config = InitialValues_2DTM_Wave()
        
        # Get most of the information we need to fill in the instance
        IV_config = fill_basic_config(IV_config, data)
        
        # === INITIALIZE IV_config ===
        # This calculates all derived parameters (delta_x, delta_t, nx, ny, nt, etc.)
        IV_config.automatedVarInit()
        

        print(f"\n=== Initial Values Configured ===")
        print(f"Waveguide: {IV_config.x_interior_region*1e6:.2f} μm × {IV_config.y_interior_region*1e9:.2f} nm")
        print(f"Permittivity: εᵣ_bg={IV_config.eps_rel_bg:.2f}") 
        print(f"Frequency: f₀={IV_config.f0/1e12:.1f} THz")
        print(f"Grid: {IV_config.nx} × {IV_config.ny} cells")
        print(f"Timesteps: {IV_config.nt}")
        print(f"Resolution: Δx={IV_config.delta_x:.2e} m, Δt={IV_config.delta_t:.2e} s")
        print(f"Source: Type {IV_config.source_type}, Amplitude {IV_config.source_amp} A/m")
        print(f"source point: ({IV_config.sx}, {IV_config.sy}) and measurement: {IV_config.cx}")
        print(f"cx {IV_config.cx}, cy {IV_config.cy}")
        print(f"y_interior_region: {IV_config.y_interior_region}, x_interior_region: {IV_config.x_interior_region}")
        print(f"========================\n")
        
        return IV_config
    
    def get_expected_outputs(self):
        return ['ez_tm_zwave.npy', 'hx_tm_zwave.npy', 'hy_tm_zwave.npy'] 


class IV_Waveguide3D_Strategy(IVStrategy):
    #TODO: whole class! and in solver!
    def parse_and_configure(self, data):
        """
        Parse and configure TM mode Initial Values
        TODO: When TM solver is available, implement similar to TE
        """
        raise NotImplementedError("3D mode solver not yet implemented. "
                                "Use 2D mode for now.")


class IV_ScatterLoss2DTE_Strategy(IVStrategy):
    """Strategy for 2DTE scattering loss analysis"""

    def validate_input(self, data):
        errors = []
        
        # Check for source
        if not data.get('sources'):
            errors.append("At least one source point required")

        # don't need to check for measurement pts because default to whole domain
        
        # Check polarization mode
        if data.get('polarization_mode') != 'TE':
            errors.append("This solver only supports TE mode")
        
        # Validate rectangles have material properties
        for i, rect in enumerate(data.get('geometry', {}).get('rectangles', [])):
            if 'material' not in rect:
                errors.append(f"Rectangle {i} missing material properties")
        
        return errors
    
    def parse_and_configure(self, data):
        """
        Parse GUI JSON and configure InitialValues_2DTM_Scatter Loss Values
        
        """
        try: 
            from solver.FDTD_2D_TE.scattering_loss.IV_2DTE_scattering import InitialValues_2DTE_Scattering
        except ImportError:
            raise ImportError("InitialValues_2DTE_Scattering Loss solver not available.    ")

        # Create instance
        IV_config = InitialValues_2DTE_Scattering()

        # fill most input info
        IV_config = fill_basic_config(IV_config, data)

        sim_params = data.get('advanced_parameters', {})

        # special scattering loss info
        IV_config.hz_fft_name = sim_params.get('hz_fft_name', 'hz_fft')
        IV_config.ex_fft_name = sim_params.get('ex_fft_name', 'ex_fft')
        IV_config.ey_fft_name = sim_params.get('ey_fft_name', 'ey_fft')

        # === INITIALIZE IV_config ===
        # This calculates all derived parameters (delta_x, delta_t, nx, ny, nt, etc.)
        IV_config.automatedVarInit()
        

        print(f"\n=== Initial Values Configured ===")
        print(f"Waveguide: {IV_config.x_interior_region*1e6:.2f} μm × {IV_config.y_interior_region*1e9:.2f} nm")
        print(f"Permittivity: εᵣ_bg={IV_config.eps_rel_bg:.2f}") 
        print(f"Frequency: f₀={IV_config.f0/1e12:.1f} THz")
        print(f"Grid: {IV_config.nx} × {IV_config.ny} cells")
        print(f"Timesteps: {IV_config.nt}")
        print(f"Resolution: Δx={IV_config.delta_x:.2e} m, Δt={IV_config.delta_t:.2e} s")
        print(f"Source: Type {IV_config.source_type}, Amplitude {IV_config.source_amp} A/m")
        print(f"source point: ({IV_config.sx}, {IV_config.sy}) and measurement: {IV_config.cx}")
        print(f"cx {IV_config.cx}, cy {IV_config.cy}")
        print(f"y_interior_region: {IV_config.y_interior_region}, x_interior_region: {IV_config.x_interior_region}")
        print(f"========================\n")
        
        return IV_config
        
    def get_expected_outputs(self):
        return ['scatter_loss.npy', 'loss_profile.npy']


class IV_ScatterLoss2DTM_Strategy(IVStrategy):
    """Strategy for 2DTM scattering loss analysis"""
    
    def validate_input(self, data):
        errors = []
        
        # Check for source
        if not data.get('sources'):
            errors.append("At least one source point required")

        # don't need to check for measurement pts because default to whole domain
        
        # Check polarization mode
        if data.get('polarization_mode') != 'TM':
            errors.append("This solver only supports TM mode")
        
        # Validate rectangles have material properties
        for i, rect in enumerate(data.get('geometry', {}).get('rectangles', [])):
            if 'material' not in rect:
                errors.append(f"Rectangle {i} missing material properties")
        
        return errors
    
    def parse_and_configure(self, data):
        """
        Parse GUI JSON and configure InitialValues_2DTM_Scatter Loss Values
        
        """
        try: 
            from solver.FDTD_2D_TM.scattering_loss.IV_2DTM_scattering import InitialValues_2DTM_Scattering
        except ImportError:
            raise ImportError("InitialValues_2DTM_Scattering Loss solver not available.    ")
        
        # Create instance
        IV_config = InitialValues_2DTM_Scattering()

        # fill most input info
        IV_config = fill_basic_config(IV_config, data)

        sim_params = data.get('advanced_parameters', {})

        # special scattering loss info
        IV_config.hz_fft_name = sim_params.get('ez_fft_name', 'ez_fft')
        IV_config.ex_fft_name = sim_params.get('hx_fft_name', 'hx_fft')
        IV_config.ey_fft_name = sim_params.get('hy_fft_name', 'hy_fft')

        # === INITIALIZE IV_config ===
        # This calculates all derived parameters (delta_x, delta_t, nx, ny, nt, etc.)
        IV_config.automatedVarInit()
        

        print(f"\n=== Initial Values Configured ===")
        print(f"Waveguide: {IV_config.x_interior_region*1e6:.2f} μm × {IV_config.y_interior_region*1e9:.2f} nm")
        print(f"Permittivity: εᵣ_bg={IV_config.eps_rel_bg:.2f}") 
        print(f"Frequency: f₀={IV_config.f0/1e12:.1f} THz")
        print(f"Grid: {IV_config.nx} × {IV_config.ny} cells")
        print(f"Timesteps: {IV_config.nt}")
        print(f"Resolution: Δx={IV_config.delta_x:.2e} m, Δt={IV_config.delta_t:.2e} s")
        print(f"Source: Type {IV_config.source_type}, Amplitude {IV_config.source_amp} A/m")
        print(f"source point: ({IV_config.sx}, {IV_config.sy}) and measurement: {IV_config.cx}")
        print(f"cx {IV_config.cx}, cy {IV_config.cy}")
        print(f"y_interior_region: {IV_config.y_interior_region}, x_interior_region: {IV_config.x_interior_region}")
        print(f"========================\n")
        
        return IV_config
    
    
    def get_expected_outputs(self):
        return ['scatter_loss.npy', 'loss_profile.npy']

class IV_ScatterLoss3D_Strategy(IVStrategy):
    """Strategy for 3D scattering loss analysis"""

    #TODO: whole class! and in solver!
    
    def validate_input(self, data):
        errors = []
        # TODO: Add scatter loss specific validation
        return errors
    
    def parse_and_configure(self, data):
        """TODO: Implement when scatter loss solver is available"""
        raise NotImplementedError("Scattering Loss solver not yet implemented")
    
    def get_expected_outputs(self):
        return ['scatter_loss.npy', 'loss_profile.npy']


class IV_SParameter2DTE_Strategy(IVStrategy):
    """Strategy for 2DTE S-parameter calculations"""

    #TODO: whole class!
    
    def validate_input(self, data):
        errors = []
        
        sources = data.get('sources', [])
        if len(sources) < 2:
            errors.append("S-parameter analysis requires at least 2 ports (sources)")
        
        return errors
    
    def parse_and_configure(self, data):
        """TODO: Implement when S-parameter solver is available"""
        raise NotImplementedError("S-parameter solver not yet implemented")
    
    def get_expected_outputs(self):
        return ['s11.npy', 's21.npy', 's12.npy', 's22.npy']
    
class IV_SParameter2DTM_Strategy(IVStrategy):
    """Strategy for 2DTM S-parameter calculations"""

    #TODO: whole class!
    
    def validate_input(self, data):
        errors = []
        
        sources = data.get('sources', [])
        if len(sources) < 2:
            errors.append("S-parameter analysis requires at least 2 ports (sources)")
        
        return errors
    
    def parse_and_configure(self, data):
        """TODO: Implement when S-parameter solver is available"""
        raise NotImplementedError("S-parameter solver not yet implemented")
    
    def get_expected_outputs(self):
        return ['s11.npy', 's21.npy', 's12.npy', 's22.npy']
    

class IV_SParameter3D_Strategy(IVStrategy):
    """Strategy for 3D S-parameter calculations"""

    #TODO: whole class! and in solver!
    
    def validate_input(self, data):
        errors = []
        
        sources = data.get('sources', [])
        if len(sources) < 2:
            errors.append("S-parameter analysis requires at least 2 ports (sources)")
        
        return errors
    
    def parse_and_configure(self, data):
        """TODO: Implement when S-parameter solver is available"""
        raise NotImplementedError("S-parameter solver not yet implemented")
    
    def get_expected_outputs(self):
        return ['s11.npy', 's21.npy', 's12.npy', 's22.npy']


def fill_basic_config(IV_config, data):
    # === EXTRACT DATA FROM JSON ===
    geometry = data.get('geometry', {})
    rectangles = geometry.get('rectangles', [])
    sources = data.get('sources', [])
    measurement_pts = data.get('measurement_points', [])
    grid_spacing = geometry.get('grid_spacing', {})
    canvas_data = geometry.get('grid_dimensions', {})
    sim_params = data.get('advanced_parameters', {})

    print('Received {} rectangles and {} sources'.format(len(rectangles), len(sources)))
        
    # === MAP GEOMETRY ===
    # Whole map geometry
    #TODO verify this is what we actually want
    if canvas_data:
        IV_config.x_interior_region = canvas_data['domain_width']   #x dimension (in meters)
        IV_config.y_interior_region = canvas_data['domain_height']   #y dimension (in meters)

    #Waveguides (rectanlges)
    if rectangles:
        IV_config.rectangles = rectangles
        # each rectangle's dimensions, material properties, roughness, etc, are filled in in the mask funcs function

    else:
        print('no rectangles received')
            
    # Find background/cladding (use sim_param eps_rel_bg or default to air)
    IV_config.eps_rel_bg = float(sim_params.get('eps_rel_bg', 1.5**2))
    IV_config.eps_rel_mu = float(sim_params.get('eps_rel_mu', 1.0))

    # Sources
    if sources:
        IV_config.sources = sources
        # each source's info is parsed in IV class and solver

    domain_meas = {
        'x': 0,
        'y': 0,
        'name': 'Domain',
        'shape': 'Surface',
        'xend': IV_config.x_interior_region,
        'yend': IV_config.y_interior_region,
    }

    # Measurement points
    if measurement_pts:
        IV_config.measurement_pts = measurement_pts
    else:
        IV_config.measurement_pts.append(domain_meas)
  

    # === MAP SIMULATION PARAMETERS ===
    # These come from the ribbon controls and advanced parameters dialog
        
    # Frequency parameters
    IV_config.f0 = float(sim_params.get('frequency', 194.8e12))  # Hz
    IV_config.harmonics = float(sim_params.get('harmonics', 1.0))
        
    # Resolution parameters
    IV_config.points_per_wl = int(sim_params.get('points_per_wavelength', 40))
    IV_config.delta_t_coef = float(sim_params.get('delta_t_coef', 1))
    IV_config.delta_x = float(grid_spacing.get('delta_x', -1)) #negative 1 tells solver to use legacy calculation

    #Buffer / Cladding Parameters
    IV_config.num_cpml = int(sim_params.get('num_cpml', 20))
    #IV_config.buffer_xhat = int(sim_params.get('buffer_xhat', 20))
    #IV_config.ny_clad_wl = float(sim_params.get('ny_clad_wl', 2.0))
    IV_config.buffer_wavelengths = float(sim_params.get('buffer_wavelengths', 0))   # user doesn't have option right now, so set to 0

    #TODO fix dimensins. for now RECALCULATE INTERIOR REGION - subtract cpml info
    IV_config.x_interior_region-= 2*IV_config.num_cpml*IV_config.delta_x
    IV_config.y_interior_region-= 2*IV_config.num_cpml*IV_config.delta_x
        
    # Duration
    IV_config.num_flights = float(sim_params.get('num_flights', 2.0))
        
    # Output configuration
    IV_config.output_dir = str(sim_params.get('output_dir', 'Results'))
    IV_config.profile_number = float(sim_params.get('profile_number', 0))

    return IV_config
