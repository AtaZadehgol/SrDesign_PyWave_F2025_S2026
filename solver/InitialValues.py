"""
@author: Carla Kolze

Acknowledgement
This project is part of senior capstone at University of Idaho, working with Brian Guiana's code under Professor Ata Zadehgol's request

"""

# =============================================================================
# Import libraries
# =============================================================================

import numpy as np

class InitialValues:
    def __init__(self):
        self.ready = False
        #defaults from brian


    @property
    def ready(self):
        return self.__ready

    @ready.setter
    def ready(self, ready):
        self.__ready = ready


    # =============================================================================
    # Material parameters
    # =============================================================================

    # Physical properties
    @property
    def eps_rel_bg(self):
        return self.__eps_rel_bg
    @eps_rel_bg.setter
    def eps_rel_bg(self, eps_rel_bg):
        self.__eps_rel_bg = eps_rel_bg            # Background/cladding relative permittivity (, float)
    
    @property
    def eps_rel_fg(self):
        return self.__eps_rel_fg
    @eps_rel_fg.setter
    def eps_rel_fg(self, eps_rel_fg):
        self.__eps_rel_fg = eps_rel_fg            # Foreground/core relative permittivity (, float)

    # Geometry
    @property
    def sgl_wg_length(self):
        return self.__sgl_wg_length
    @sgl_wg_length.setter
    def sgl_wg_length(self, sgl_wg_length):
        self.__sgl_wg_length = sgl_wg_length    # Waveguide length (m, float)

    @property
    def sgl_wg_width(self):
        return self.__sgl_wg_width
    @sgl_wg_width.setter
    def sgl_wg_width(self, sgl_wg_width):
        self.__sgl_wg_width = sgl_wg_width          # Waveguide width (m, float)

    @property
    def port_length(self):
        return self.__port_length
    @port_length.setter
    def port_length(self, port_length):
        self.__port_length = port_length            # Mode settling length for port 1 and 2

    @property
    def port1_length(self):
        return self.__port1_length
    @port1_length.setter
    def port1_length(self, port1_length):
        self.__port1_length = port1_length            # Mode settling length for port 1 (m, float)
    
    @property
    def port2_length(self):
        return self.__port2_length
    @port2_length.setter
    def port2_length(self, port2_length):
        self.__port2_length = port2_length            # Mode settling length for port 2 (m, float)

    # Roughness
    @property
    def rough_std(self):
        return self.__rough_std
    @rough_std.setter
    def rough_std(self, rough_std):
        self.__rough_std = rough_std            # Target roughness standard deviation (m, float)
    
    @property
    def rough_acl(self):
        return self.__rough_acl
    @rough_acl.setter
    def rough_acl(self, rough_acl):
        self.__rough_acl = rough_acl           # Target roughness correlation length (m, float)
    
    @property
    def tol_std(self):
        return self.__tol_std
    @tol_std.setter
    def tol_std(self, tol_std):
        self.__tol_std = tol_std                 # Standard deviation percentage tolerance (%, float)
    
    @property
    def tol_acl(self):
        return self.__tol_acl
    @tol_acl.setter
    def tol_acl(self, tol_acl):
        self.__tol_acl = tol_acl               # Correlation length percentage tolerance (%, float)

    # =============================================================================
    # Switches
    # =============================================================================

    @property
    def rough_toggle(self):
        return self.__rough_toggle
    @rough_toggle.setter
    def rough_toggle(self, rough_toggle):
        self.__rough_toggle = rough_toggle           # Toggle sidewall roughness on/off (, bool)
                                #     True: waveguide sidewalls will vary w.r.t. length
                                #     False: waveguide sidewalls are do not vary

    @property
    def ctype(self):
        return self.__ctype
    @ctype.setter
    def ctype(self, ctype):
        self.__ctype = ctype                      # Roughness profile correlation type for upper and lower profiles
                                #     1: Directly correlated (upper == lower => bend dominant)
                                #     2: Inversely correlated (upper == -lower => pinch dominant)
                                #     3: Uncorrelated (upper != lower => bend/pinch combo)
                                # The generation checks up to 300,000 unique profiles
                                #     for closeness to input parameters, or until
                                #     a valid profile is found. This is done for
                                #     both upper and lower profiles in "ctype=3"

    # =============================================================================
    # Outputs
    # =============================================================================

    # Directories
    @property
    def output_dir(self):
        return self.__output_dir
    @output_dir.setter
    def output_dir(self, output_dir):
        self.__output_dir = output_dir         # File output subfolder name
    
    @property
    def profile_number(self):
        return self.__profile_number
    @profile_number.setter
    def profile_number(self, profile_number):
        self.__profile_number = profile_number             # Simulation ID for batch simulation

    # =============================================================================
    # Source and resolution parameters
    # =============================================================================

    # Source shape
    @property
    def source_type(self):
        return self.__source_type
    @source_type.setter
    def source_type(self, source_type):
        self.__source_type = source_type                # Input source type [st] (, int)
                                #     1: Gaussian pulse
                                #     2: Wave packet
                                #     3: Time-harmonic
    @property
    def source_amp(self):
        return self.__source_amp
    @source_amp.setter
    def source_amp(self, source_amp):
        self.__source_amp = source_amp              # Source magnitude (A / m, float)
    
    @property
    def wave_packet_bw(self):
        return self.__wave_packet_bw
    @wave_packet_bw.setter
    def wave_packet_bw(self, wave_packet_bw):
        self.__wave_packet_bw = wave_packet_bw          # Wave-packet bandwidth; may be safely ignored when not using st 2 (%, float)
    
    @property
    def gauss_pulse_deg(self):
        return self.__gauss_pulse_deg
    @gauss_pulse_deg.setter
    def gauss_pulse_deg(self, gauss_pulse_deg):
        self.__gauss_pulse_deg = gauss_pulse_deg           # Frequency domain signal strength at f0, must be negative; may be safely ignored when not using st 1 (dB, float)
    
    @property
    def f0(self):
        return self.__f0
    @f0.setter
    def f0(self, f0):
        self.__f0 = f0                  # Fundamental frequency; used for st 2 and st 3 (Hz, float)

    # Resolution and duration
    @property
    def harmonics(self):
        return self.__harmonics
    @harmonics.setter
    def harmonics(self, harmonics):
        self.__harmonics = harmonics              # Number of harmonics above fundamental frequency to use (, float)
    
    @property
    def num_flights(self):
        return self.__num_flights
    @num_flights.setter
    def num_flights(self, num_flights):
        self.__num_flights = num_flights              # Number of flight times to simulate (, float)
    
    @property
    def points_per_wl(self):
        return self.__points_per_wl
    @points_per_wl.setter
    def points_per_wl(self, points_per_wl):
        self.__points_per_wl = points_per_wl             # Number of points per minimum wavelength (cells, int)

    # Boundary conditions
    @property
    def num_cpml(self):
        return self.__num_cpml
    @num_cpml.setter
    def num_cpml(self, num_cpml):
        self.__num_cpml =  num_cpml                  # CPML layer size around simulation space (cells, int)
    
    @property
    def buffer_xhat(self):
        return self.__buffer_xhat
    @buffer_xhat.setter
    def buffer_xhat(self, buffer_xhat):
        self.__buffer_xhat = buffer_xhat               # Additional buffer between souce point and cpml region, x-direction (cells, int)
    
    @property
    def ny_clad_wl(self):
        return self.__ny_clad_wl
    @ny_clad_wl.setter
    def ny_clad_wl(self, ny_clad_wl):
        self.__ny_clad_wl = ny_clad_wl              # Buffer between waveguide core and cpml regions, y-direction (lambda, float)

    # new
    @property
    def gp_tpk_coef(self):
        return self.__gp_tpk_coef
    @gp_tpk_coef.setter
    def gp_tpk_coef(self, gp_tpk_coef):
        self.__gp_tpk_coef = gp_tpk_coef

    @property
    def wp_tsp_coef(self):
        return self.__wp_tsp_coef
    @wp_tsp_coef.setter
    def wp_tsp_coef(self, wp_tsp_coef):
        self.__wp_tsp_coef = wp_tsp_coef

    @property
    def wp_tpk_coef(self):
        return self.__wp_tpk_coef
    @wp_tpk_coef.setter
    def wp_tpk_coef(self, wp_tpk_coef):
        self.__wp_tpk_coef = wp_tpk_coef

    # =============================================================================
    # Automated simulation setup
    # =============================================================================
    def automatedVarInit(self):
        self.__ready = True
    # Physical constants and value normalization
        self.eps = self.__eps_rel_bg / ( 36.0e9 * np.pi )            # Base permittivity (F/m)
        self.mu = 4.0e-7 * np.pi                              # Base permeability (H/m)
        self.c_bg = 1 / np.sqrt( self.eps * self.mu )                   # Base phase velocity (m/s)
        self.eta = np.sqrt( self.mu / self.eps )                        # Base impedance (Ohms)
        self.eps_rel_fg /= self.__eps_rel_bg                         # Normalized foreground/core relative permittivity ()
        self.f_max = self.__harmonics * self.__f0                           # Maximum simulation frequency (Hz)
        self.vp = self.c_bg / np.sqrt( self.__eps_rel_fg )                # Foreground/core phase velocity (m/s)
        self.wl = self.vp / self.f_max                                  # Minimum wavelength (m)
        self.wl_clad = self.c_bg / self.f_max                           # Cladding wavelength (m)
        self.flight_time = self.__sgl_wg_length / self.vp                 # Single flight time (s)

        self.sim_time = self.__num_flights * self.flight_time             # Simulation duration (s)
        self.delta_x = self.wl / self.__points_per_wl                     # Spatial resolution (m/cell)
        self.delta_t = self.delta_x / ( self.c_bg * np.sqrt( 2 ) )      # Temporal resolution (s/step)
        #variable delta_t = v*delta_x where v=1/(cbg*sqrt2)

        self.delta_x = self.delta_x.astype(np.float32)             # Change data type of dx to 4-byte precision
        self.delta_t = self.delta_t.astype(np.float32)             # Change data type of dt to 4-byte precision
        self.buffer_yhat = int(self.__ny_clad_wl*self.wl_clad/self.delta_x)    # Cladding buffer between waveguide and cpml region, y-direction (cells, int)

        # Space-time discretization
        self.nt = int( self.sim_time / self.delta_t )                   # Total simulation duration (steps)
        self.nx_swg = int( self.__sgl_wg_length / self.delta_x )          # Single waveguide size, x-direction (cells)
        self.ny_swg = int( self.__sgl_wg_width / self.delta_x )           # Single waveguide size, y-direction (cells)
        self.bx = self.__num_cpml + self.__buffer_xhat                      # Border size, x-direction (cells)
        self.by = self.__num_cpml + self.buffer_yhat                      # Border size, y-direction (cells)
        self.nx = 2 * self.bx + self.nx_swg                             # Computational domain size, x-direction (cells)
        self.ny = 2 * self.by + self.ny_swg                             # Computational domain size, y-direction (cells)
        #should be able to change these

        self.rstd = self.__rough_std / self.delta_x                       # Normalized roughness standard deviation (cells)
        self.racl = self.__rough_acl / self.delta_x                       # Normalized roughness autocorrelation length (cells)
        self.tol_std /= 100                                   # Normalized standard deviation tolerance ()
        self.tol_acl /= 100                                   # Normalized correlation length tolerance ()

        # Relational parameters
        self.cx = self.nx // 2                                     # Center cell, x-direction
        self.cy = self.ny // 2                                     # Center cell, y-direction
        self.cx_swg = self.nx_swg // 2                             # Single waveguide center cell, x-direction
        self.cy_swg = self.ny_swg // 2                             # Single waveguide center cell, y-direction
        self.sx = self.bx + 0             #10?                        # Source point, x-direction
        self.sy = self.by + self.cy_swg                            # Source point, y-direction
        #i feel like these should be editable?

        # =============================================================================
        # Source assignment
        # =============================================================================

        # Gaussian pulse spread and peak time
        self.gp_tsp = np.sqrt( -2 * np.log( 10**( self.__gauss_pulse_deg / 20 ) ) ) / ( 2 * np.pi * self.__f0 )
        self.gp_tpk = self.__gp_tpk_coef * self.gp_tsp

        # Wave packet spread and peak time
        self.wp_tsp = self.__wp_tsp_coef * np.sqrt( np.log( 2 ) ) / ( self.__wave_packet_bw * 2 * np.pi * self.__f0 ) #omega always 2pi f
        self.wp_tpk = self.__wp_tpk_coef * self.wp_tsp

        # Array setup
        self.GP = np.zeros(self.nt, dtype=np.float32)       # Gaussian pulse shape array
        self.WP = np.zeros(self.nt, dtype=np.float32)       # Wave packet shape array
        self.TH = np.zeros(self.nt, dtype=np.float32)       # Time-harmonic signal shape array
        self.RAMP = np.zeros(self.nt, dtype=np.float32)     # Smooth ramp shape array

        # Time step evaluation
        for n in range(self.nt):
            self.GP[n] = np.exp(-0.5 * ( ( n*self.delta_t - self.gp_tpk ) / self.gp_tsp )**2 )
            self.WP[n] = np.exp(-0.5 * ( ( n*self.delta_t - self.wp_tpk ) / self.wp_tsp )**2 ) * np.exp( 2j * np.pi * self.__f0 * ( n * self.delta_t - self.wp_tpk ) ).real
            self.RAMP[n] = self.RAMP[n-1] + self.delta_t*self.GP[n]
            self.TH[n] = np.exp( 2j * np.pi * self.__f0 * ( n * self.delta_t - self.gp_tpk ) ).real
        self.RAMP = self.RAMP / np.max( self.RAMP )                        # Set maximum magnitude of RAMP to 1

        # Apply magnitude to shape
        if self.__source_type == 1:
            self.J_SRC = (self.__source_amp * self.GP)            # Assign Gaussian pulse to source
        elif self.__source_type == 2:
            self.J_SRC = (self.__source_amp * self.WP)            # Assign wave packet to source
        elif self.__source_type == 3:
            self.J_SRC = (self.__source_amp * self.RAMP * self.TH)     # Assign time-harmonic + ramp up to source
        else:
            raise Exception('Pick a valid source type')     # Stop the program if an invalid source was chosen

        self.p1x = self.sx + int(self.__port1_length/self.delta_x)
        self.p2x = self.sx + self.nx_swg - int(self.__port2_length/self.delta_x)
        if self.p2x <= self.p1x:
            raise Exception('Port settling ranges overlap. Make the WG longer or decrease port settling range!')

        self.profile_std = str(round(self.__rough_std*1e9))
        self.profile_acl = str(round(self.__rough_acl*1e9))
        self.roughness_profile = '_s'+self.profile_std+'nm_lc'+self.profile_acl+'nm_r'+str(self.profile_number)
        self.up = './rough_profiles/profile_upper'+self.roughness_profile
        self.lp = './rough_profiles/profile_lower'+self.roughness_profile


    #functions to fill class with the defaults of Brian's code. call before setting any variables with input
    def default_2D_TE_wave(self):
        self.eps_rel_bg = 1.5**2
        self.eps_rel_fg = 3.5**2
        self.sgl_wg_length = 25.0e-6
        self.sgl_wg_width = 200e-9
        self.port1_length = 5e-6
        self.port2_length = 0e-6
        self.rough_std = 15.0e-9
        self.rough_acl = 700.0e-9
        self.tol_std = 10.0
        self.tol_acl = 10.0
        self.rough_toggle = False
        self.ctype = 3
        self.output_dir = 'Results'
        self.profile_number = 0
        self.source_type = 1
        self.source_amp = 20.0
        self.wave_packet_bw = 0.10
        self.gauss_pulse_deg = -6
        self.f0 = 194.8e12
        self.harmonics = 1.000
        self.num_flights = 2.0
        self.points_per_wl = 40
        self.num_cpml = 20
        self.buffer_xhat = 20
        self.ny_clad_wl = 2.0 
        self.gp_tpk_coef = 9
        self.wp_tsp_coef = 2
        self.wp_tpk_coef = 9
    
    def default_2D_TM_wave(self):
        self.eps_rel_bg = 1.5**2
        self.eps_rel_fg = 3.5**2
        self.sgl_wg_length = 30e-6
        self.sgl_wg_width = 200e-9
        self.port_length = 5e-6
        self.port1_length = None
        self.port2_length = None
        self.rough_std = 15.0e-9
        self.rough_acl = 700.0e-9
        self.tol_std = 10.0
        self.tol_acl = 10.0
        self.rough_toggle = False
        self.ctype = 3
        self.output_dir = 'Results'
        self.profile_number = 0
        self.source_type = 1
        self.source_amp = 5.0
        self.wave_packet_bw = 0.8
        self.gauss_pulse_deg = -6
        self.f0 = 194.8e12
        self.harmonics = 1.000
        self.num_flights = 2.0
        self.points_per_wl = 40
        self.num_cpml = 20
        self.buffer_xhat = 10
        self.ny_clad_wl = 2.0 
        self.gp_tpk_coef = 5
        self.wp_tsp_coef = 2
        self.wp_tpk_coef = 5
