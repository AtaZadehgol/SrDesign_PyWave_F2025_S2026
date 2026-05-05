#import numpy as np

'''
class initValues2DsParam:
    # =============================================================================
    # Material parameters
    # =============================================================================

    # Physical properties
    __eps_rel_bg = 1.5**2            # Background/cladding relative permittivity (, float)
    __eps_rel_fg = 3.5**2            # Foreground/core relative permittivity (, float)

    # Geometry
    __sgl_wg_length = 15.0e-6        # Waveguide length (m, float)
    __sgl_wg_height = 0.2e-6         # Single waveguide height (m, float)

    __pitch = 2.0e-6                 # Pitch between waveguides (m, float)
    __num_lines = 1                  # Number of parallel waveguides (, int)

    __port1_length = 5.0e-6          # Modal settling length for port 1 (m, float)
    __port2_length = 5.0e-6          # Modal settling length for port 2 (m, float)

    # Roughness
    __rough_std = 20.0e-9            # Target roughness standard deviation (m, float)
    __rough_acl = 500.0e-9           # Target roughness correlation length (m, float)
    __tol_std = 10.0                 # Standard deviation percentage tolerance (%, float)
    __tol_acl = 10.0                 # Correlation length percentage tolerance (%, float)

    # =============================================================================
    # Switches
    # =============================================================================

    __rough_toggle = True            # Toggle sidewall roughness on/off (, bool)
                                #     True: waveguide sidewalls will vary w.r.t. length
                                #     False: waveguide sidewalls are do not vary

    __ctype = 3                      # Roughness profile correlation type for upper and lower profiles
                                #     1: Directly correlated (upper == lower => bend dominant)
                                #     2: Inversely correlated (upper == -lower => pinch dominant)
                                #     3: Uncorrelated (upper != lower => bend/pinch combo)
                                # The generation checks up to 300,000 unique profiles
                                #     for closeness to input parameters, or until
                                #     a valid profile is found. This is done for
                                #     both upper and lower profiles in "ctype=3"

    __precision = np.float32         # Floating point arithmetic precision. Choose np.float32 or np.float64
    __sim_type = 's-param'           # Simulation type. Choose 's-param'. Other outputs not ready yet.
    __auto_condition = True          # Automatically condition settings for "Source
                                #     parameters" and "Resolution and duration"
                                #     for the provided "S-Parameter Extraction"
                                #     settings (, bool)

    __feedback_at_n_percent = 10     # Interval between feedback readouts (%, int or float)
    __profile_number = 0             # Roughness profile index number (, int)

    # =============================================================================
    # Simulation parameters
    # =============================================================================

    # Outputs
    __output_dir = 'Results'         # Output directory name (, str)
                                #     A new folder will be generated in the
                                #     working directory if one by the specified
                                #     name does not already exist. Do not
                                #     include the './' prefix.
    __prof_dir = 'rough_profiles'    # Storage directory for rough profiles (, str)
                                #     A new folder will be generated in the
                                #     working directory.

    __sparam_file = 'check_func'     # Output file name for S-Parameter extraction (, str)

    # S-Parameter Extraction
    __sparam_fmin = 100e12           # Minimum frequency for S-Parameter output file (Hz, float) #170e12 TM
    __sparam_fmax = 300e12           # Maximum frequency for S-Parameter output file (Hz, float) #230e12 TM
    __sparam_num_freqs = 101         # Number of frequencies between fmin and fmax, inclusive (, int) #10001 TM

    # Source parameters
    __source_type = 2                # Input source type (, int)

                                #     2: Wave packet
                                #     3: Time-harmonic
    __source_amp = 5.0               # Source magnitude (V / m, float)
    __wave_packet_bw = 0.5           # Wave-packet bandwidth; may be safely ignored when not using st 2 (%, float)
    __gauss_pulse_deg = -6           # Frequency domain signal strength at f0, must be negative; may be safely ignored when not using st 1 (dB, float)
    __f0 = 194.8e12                  # Fundamental frequency; used for st 2 and st 3 (Hz, float)

    # Resolution and duration
    __harmonics = 1.000              # Number of harmonics above fundamental frequency to use (, float)
    __num_flights = 2.0              # Number of flight times to simulate (, float)
    __points_per_wl = 40             # Number of points per minimum wavelength (cells, int)

    # Boundary conditions
    __num_cpml = 20                  # CPML layer size around simulation space (cells, int)
    __buffer_xhat = 20               # Buffer length between source and cpml region size, x-direction (cells, int)
    __ny_clad_wl = 2.0               # Buffer between waveguide core and cpml regions, y-direction (lambda, float)
'''

class Methoding:
    def __init__(self):
        self.__size = None
        self.size = 2
        self.__cat = 5
        self.__material = 5
    
    @property
    def size(self):
        return self.__size
    
    @size.setter
    def size(self, size):
        if (size < 2):
            raise ValueError("size too small")
        print("setter called")
        self.__size = size

    @property
    def cat(self):
        return self.__cat
    
    @property
    def material(self):
        print("in getter")
        return self.__material

    @material.setter
    def material(self, material):
        if (material > 3):
            raise ValueError("material too big")
        print("setter 2 called")
        self.__material = material

    @property
    def ttt(self):
        return self.__ttt
    @ttt.setter
    def ttt(self):
        self.__ttt = self.material

car = Methoding()
print(car.size, car.material)
car.size = 5
car.material = 3
print(car.size, car.material, car.cat, car.ttt)
