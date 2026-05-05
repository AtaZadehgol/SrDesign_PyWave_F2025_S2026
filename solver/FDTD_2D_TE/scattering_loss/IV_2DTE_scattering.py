"""
@author: Carla Kolze

Acknowledgement
This project is part of senior capstone at University of Idaho, working with Brian Guiana's code under Professor Ata Zadehgol's request

"""

# =============================================================================
# Import libraries
# =============================================================================

import numpy as np

class InitialValues_2DTE_Scattering:
    def __init__(self):
        self.ready = False

        #brian defaults
        self.eps_rel_bg = 1.5**2
        self.mu_rel_bg = 1.0

        #if for 1 rectangle
        self.eps_rel_fg = 3.5**2
        self.x_interior_region = 45.0e-6        # interior x dimension (length of wg is single legacy)
        self.y_interior_region = 200e-9         # interior y dimension (width of wg is single legacy)
        self.port1_length = 5e-6
        self.port2_length = 0e-6
        self.rough_std = 15.0e-9
        self.rough_acl = 700.0e-9
        self.tol_std = 10.0
        self.tol_acl = 10.0
        self.rough_toggle = True
        self.ctype = 3

        self.output_dir = 'Results'
        self.hz_fft_name = 'hz_fft'
        self.ex_fft_name = 'ex_fft'
        self.ey_fft_name = 'ey_fft'
        self.profile_number = 0

        #per source now
        self.source_type = 1
        self.source_amp = 20.0
        self.wave_packet_bw = 0.10
        self.gauss_pulse_deg = -6
        self.f0 = 194.8e12

        self.harmonics = 1.000
        self.num_flights = 2.0
        self.points_per_wl = 40
        self.num_cpml = 20
        self.delta_x = -1   #will be set or recalculated
        self.delta_t_coef = 1

        self.buffer_xhat = 20
        self.ny_clad_wl = 2.0
        self.gp_tsp_coef = 1
        self.gp_tpk_coef = 9
        self.wp_tsp_coef = 2
        self.wp_tpk_coef = 9

        #multiple waveguide functionality
        self.rectangles = []
        self.canvas_length_meters = None    #total canvas length in meters
        self.canvas_height_meters = None    #total canvas height in meters
        self.gui_x_spacing = None           #grid spacing from the GUI
        self.gui_y_spacing = None           #grid spacing from GUI

        #multiple sources
        self.sources = []

        #multiple measurement points
        self.measurement_pts = []

    @property
    def ready(self):
        return self.__ready

    @ready.setter
    def ready(self, ready):
        self.__ready = ready

    # =============================================================================
    #   Important info from GUI to help set things up
    # =============================================================================
    @property
    def rectangles(self):
        return self.__rectangles
    @rectangles.setter
    def rectangles(self, rectangles):
        self.__rectangles = rectangles

    @property
    def canvas_length_meters(self):
        return self.__canvas_length_meters
    @canvas_length_meters.setter
    def canvas_length_meters(self, canvas_length_meters):
        self.__canvas_length_meters = canvas_length_meters

    @property
    def canvas_height_meters(self):
        return self.__canvas_height_meters
    @canvas_height_meters.setter
    def canvas_height_meters(self, canvas_height_meters):
        self.__canvas_height_meters = canvas_height_meters

    @property
    def gui_x_spacing(self):
        return self.__gui_x_spacing
    @gui_x_spacing.setter
    def gui_x_spacing(self, gui_x_spacing):
        self.__gui_x_spacing = gui_x_spacing

    @property
    def gui_y_spacing(self):
        return self.__gui_y_spacing
    @gui_y_spacing.setter
    def gui_y_spacing(self, gui_y_spacing):
        self.__gui_y_spacing = gui_y_spacing

    @property
    def sources(self):
        return self.__sources
    @sources.setter
    def sources(self, sources):
        self.__sources = sources

    @property
    def measurement_pts(self):
        return self.__measurement_pts
    @measurement_pts.setter
    def measurement_pts(self, measurement_pts):
        self.__measurement_pts = measurement_pts


    # =============================================================================
    # Material parameters
    # =============================================================================

    # Physical properties
    @property
    def eps_rel_bg(self):
        return self.__eps_rel_bg
    @eps_rel_bg.setter
    def eps_rel_bg(self, eps_rel_bg):
        self.__eps_rel_bg = eps_rel_bg              # Background/cladding relative permittivity (, float)

    @property
    def mu_rel_bg(self):
        return self.__mu_rel_bg
    @mu_rel_bg.setter
    def mu_rel_bg(self, mu_rel_bg):
        self.__mu_rel_bg = mu_rel_bg                # Background/cladding relative permeability (, float)

    @property
    def eps_rel_fg(self):
        return self.__eps_rel_fg
    @eps_rel_fg.setter
    def eps_rel_fg(self, eps_rel_fg):
        self.__eps_rel_fg = eps_rel_fg              # Foreground/core relative permittivity (, float)

    # Geometry
    @property
    def x_interior_region(self):
        return self.__x_interior_region
    @x_interior_region.setter
    def x_interior_region(self, x_interior_region):
        self.__x_interior_region = x_interior_region    # Waveguide length (m, float)

    @property
    def y_interior_region(self):
        return self.__y_interior_region
    @y_interior_region.setter
    def y_interior_region(self, y_interior_region):
        self.__y_interior_region = y_interior_region          # Waveguide width (m, float)


    # Roughness
    @property
    def rough_std(self):
        return self.__rough_std
    @rough_std.setter
    def rough_std(self, rough_std):
        self.__rough_std = rough_std                # Target roughness standard deviation (m, float)

    @property
    def rough_acl(self):
        return self.__rough_acl
    @rough_acl.setter
    def rough_acl(self, rough_acl):
        self.__rough_acl = rough_acl                # Target roughness correlation length (m, float)

    @property
    def tol_std(self):
        return self.__tol_std
    @tol_std.setter
    def tol_std(self, tol_std):
        self.__tol_std = tol_std                    # Standard deviation percentage tolerance (%, float)

    @property
    def tol_acl(self):
        return self.__tol_acl
    @tol_acl.setter
    def tol_acl(self, tol_acl):
        self.__tol_acl = tol_acl                    # Correlation length percentage tolerance (%, float)

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


    #output files
    @property
    def hz_fft_name(self):
        return self.__hz_fft_name
    @hz_fft_name.setter
    def hz_fft_name(self, hz_fft_name):
        self.__hz_fft_name = hz_fft_name

    @property
    def ex_fft_name(self):
        return self.__ex_fft_name
    @ex_fft_name.setter
    def ex_fft_name(self, ex_fft_name):
        self.__ex_fft_name = ex_fft_name

    @property
    def ey_fft_name(self):
        return self.__ey_fft_name
    @ey_fft_name.setter
    def ey_fft_name(self, ey_fft_name):
        self.__ey_fft_name = ey_fft_name

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
        self.__source_amp = source_amp                  # Source magnitude (A / m, float)

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
        self.__gauss_pulse_deg = gauss_pulse_deg        # Frequency domain signal strength at f0, must be negative; may be safely ignored when not using st 1 (dB, float)

    @property
    def f0(self):
        return self.__f0
    @f0.setter
    def f0(self, f0):
        self.__f0 = f0                                  # Fundamental frequency; used for st 2 and st 3 (Hz, float)

    # Resolution and duration
    @property
    def harmonics(self):
        return self.__harmonics
    @harmonics.setter
    def harmonics(self, harmonics):
        self.__harmonics = harmonics                    # Number of harmonics above fundamental frequency to use (, float)

    @property
    def num_flights(self):
        return self.__num_flights
    @num_flights.setter
    def num_flights(self, num_flights):
        self.__num_flights = num_flights                # Number of flight times to simulate (, float)

    @property
    def points_per_wl(self):
        return self.__points_per_wl
    @points_per_wl.setter
    def points_per_wl(self, points_per_wl):
        self.__points_per_wl = points_per_wl            # Number of points per minimum wavelength (cells, int)

    #RESOLUTION!
    @property
    def delta_x(self):
        return self.__delta_x
    @delta_x.setter
    def delta_x(self, delta_x):
        self.__delta_x = delta_x

    @property
    def delta_t_coef(self):
        return self.__delta_t_coef
    @delta_t_coef.setter
    def delta_t_coef(self, delta_t_coef):
        self.__delta_t_coef = delta_t_coef

    # Boundary conditions
    @property
    def num_cpml(self):
        return self.__num_cpml
    @num_cpml.setter
    def num_cpml(self, num_cpml):
        self.__num_cpml =  num_cpml                     # CPML layer size around simulation space (cells, int)

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
        self.__ny_clad_wl = ny_clad_wl                  # Buffer between waveguide core and cpml regions, y-direction (lambda, float)

    @property
    def buffer_wavelengths(self):
        return self.__buffer_wavelengths

    @buffer_wavelengths.setter
    def buffer_wavelengths(self, buffer_wavelengths):
        self.__buffer_wavelengths = buffer_wavelengths  # Wavelength to set buffers between waveguide region and cpml regions, both directions (lambda, float)

    @property
    def gp_tsp_coef(self):
        return self.__gp_tsp_coef
    @gp_tsp_coef.setter
    def gp_tsp_coef(self, gp_tsp_coef):
        self.__gp_tsp_coef = gp_tsp_coef

    @property
    def gp_tsp_coef(self):
        return self.__gp_tsp_coef
    @gp_tsp_coef.setter
    def gp_tsp_coef(self, gp_tsp_coef):
        self.__gp_tsp_coef = gp_tsp_coef

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
        self.eps = self.__eps_rel_bg / ( 36.0e9 * np.pi )               # Base permittivity (F/m)
        self.mu = self.__mu_rel_bg * 4.0e-7 * np.pi                     # Base permeability (H/m)
        self.c_bg = 1 / np.sqrt( self.eps * self.mu )                   # Base phase velocity (m/s)
        self.eta = np.sqrt( self.mu / self.eps )                        # Base impedance (Ohms)

        self.c_max = self.c_bg

        # Find maximum frequency across all sources
        if self.sources and len(self.sources) > 0:
            source_frequencies = [source.get('frequency', self.__f0) for source in self.sources]
            max_source_freq = max(source_frequencies)
            self.f_max = self.__harmonics * max_source_freq
            print(f'Using f_max = {self.f_max/1e12:.2f} THz (from max source frequency)')
        else:
            # Legacy: use global f0
            self.f_max = self.__harmonics * self.__f0                   # Maximum simulation frequency (Hz)

        #find minimum wavelength, manimum phase velocity, and max flight time
        if self.rectangles and len(self.rectangles) > 0:

            min_vp = float('inf')
            max_flight_time = 0
            for rect in self.rectangles:
                #TODO: fix dimensions
                # gui sends us total domain, but we want to calculate rectangles based of interior region
                # so take cpml off of starting coordinate
                rect['position']['x'] -= self.num_cpml * self.delta_x
                rect['position']['y'] -= self.num_cpml * self.delta_x

                #gui sends us top left coordinate for x,y but we want bottom left. calculate that now.
                top_y = rect['position']['y']
                bottom_y = top_y - rect['dimensions']['height']
                rect['position']['y'] = bottom_y

                #onto material properties
                rect_eps = rect['material']['permittivity']
                rect_mu = rect['material']['permeability']

                # relative permittivity and permeability compared to background
                rect_eps_rel = rect_eps / self.__eps_rel_bg
                rect_mu_rel = rect_mu / self.__mu_rel_bg

                #phase velocty in this waveguide relative to background
                rect_vp = self.c_bg / np.sqrt(rect_eps_rel * rect_mu_rel)

                # want slowest phase velocity
                if rect_vp < min_vp:
                    min_vp = rect_vp

                # want speed in fastest material for delta t
                if rect_vp > self.c_max:
                    self.c_max = rect_vp

                #geometry for flight time
                rect_width = rect['dimensions']['width']                    #in meters
                rect_height = rect['dimensions']['height']                  #in meters
                rect_diagonal = np.sqrt(rect_width**2 + rect_height**2)     #get the diagonal dimension in meters
                rect_flight_time = rect_diagonal / rect_vp

                #want longest flight time
                if rect_flight_time > max_flight_time:
                    max_flight_time = rect_flight_time

            #use slowest phase velofity
            self.vp = min_vp

            #use shortest wavelength
            self.wl = self.vp / self.f_max

            #use longest flight time
            self.flight_time = max_flight_time

        else: #legacy single-waveguide mode
            null_rect = {
                'position': {
                    'x': 0,
                    'y': 0
                },
                'dimensions': {
                    'width': 0,
                    'height': 0
                },
                'name': 'null',
                'material': {
                    'permittivity': 1,
                    'permeability': 1,
                    'conductivity': 1
                },
                'roughness': {
                    "rough_toggle": False
                }
            }
            self.rectangles.append(null_rect)
            self.eps_rel_fg = self.__eps_rel_bg                         # Set to same material
            self.eps_rel_fg /= self.__eps_rel_bg                        # Normalized foreground/core relative permittivity ()
            self.vp = self.c_bg / np.sqrt(self.__eps_rel_fg)            # Foreground/core phase velocity (m/s)
            self.wl = self.vp / (self.__harmonics * self.__f0)          # Minimum wavelength (m)
            self.flight_time = self.__x_interior_region / self.vp       # Single flight time (s)

        self.wl_clad = self.c_bg / self.f_max                           # Cladding wavelength (m)

        self.sim_time = self.__num_flights * self.flight_time           # Simulation duration (s)

        if self.delta_x == -1:                                          # Only calculate if given a negative (impossible) number
            self.delta_x = self.wl / self.__points_per_wl               # Spatial resolution (m/cell)
        self.delta_t = self.delta_t_coef * self.delta_x / ( self.c_max * np.sqrt( 2 ) )    # Temporal resolution (s/step)

        #self.delta_x = self.delta_x.astype(np.float32)                  # Change data type of dx to 4-byte precision
        #self.delta_t = self.delta_t.astype(np.float32)                  # Change data type of dt to 4-byte precision
        #self.buffer_yhat = int(self.__ny_clad_wl * self.wl_clad / self.delta_x)    # Cladding buffer between waveguide and cpml region, y-direction (cells, int)
        self.buffer_cells = int(self.__buffer_wavelengths * self.wl_clad / self.delta_x)        # currently user doesn't explicitly set this to anything, but useful to have incase

        # Space-time discretization
        self.nt = int( self.sim_time / self.delta_t )                   # Total simulation duration (steps)
        self.nx_swg = int( self.__x_interior_region / self.delta_x )    # interior region size, x-direction (cells)
        self.ny_swg = int( self.__y_interior_region / self.delta_x )    # interior region size, y-direction (cells)
        self.bx = self.__num_cpml + self.buffer_cells                   # Border size, x-direction (cells)  # was + buffer_xhat
        self.by = self.__num_cpml + self.buffer_cells                   # Border size, y-direction (cells)  # was + buffer_yhat
        self.nx = 2 * self.bx + self.nx_swg                             # Computational domain size, x-direction (cells)
        self.ny = 2 * self.by + self.ny_swg                             # Computational domain size, y-direction (cells)
        #should be able to change these     - but really allowing user to change nx_swg and ny_swg

        self.rstd = self.__rough_std / self.delta_x                     # Normalized roughness standard deviation (cells)
        self.racl = self.__rough_acl / self.delta_x                     # Normalized roughness autocorrelation length (cells)
        self.tol_std /= 100                                             # Normalized standard deviation tolerance ()
        self.tol_acl /= 100                                             # Normalized correlation length tolerance ()

        # Relational parameters - completely unused now
        self.cx = self.nx // 2                                     # Center cell, x-direction
        self.cy = self.ny // 2                                     # Center cell, y-direction
        self.cx_swg = self.nx_swg // 2                             # Single waveguide center cell, x-direction
        self.cy_swg = self.ny_swg // 2                             # Single waveguide center cell, y-direction
        self.sx = self.bx + 10                                     # Source point, x-direction
        self.sy = self.by + self.cy_swg                            # Source point, y-direction
        #should above be changeable?!

        # =============================================================================
        # Source assignment
        # =============================================================================

        if self.sources and len(self.sources) > 0:
            # Multi-source mode: create waveform for each source
            self.source_waveforms = []

            for src_idx, source in enumerate(self.sources):
                src_name = source.get('name', f'Source {src_idx}')
                src_type_str = source.get('source_type', 'Gaussian Pulse')
                src_amp = source.get('amplitude', self.__source_amp)
                src_freq = source.get('frequency', self.__f0)

                # Map source type string to integer
                type_map = {
                    'Gaussian Pulse': 1,
                    'Wave Packet': 2,
                    'Time Harmonic': 3
                }
                src_type = type_map.get(src_type_str, 1)

                print(f'Generating waveform for {src_name}: {src_type_str} at {src_freq/1e12:.2f} THz')

                # Generate waveform based on type
                if src_type == 1:  # Gaussian Pulse
                    gp_deg = source.get('gauss_pulse_deg', self.__gauss_pulse_deg)
                    gp_tsp_coef = source.get('gp_tsp_coef', self.__gp_tsp_coef)
                    gp_tpk_coef = source.get('gp_tpk_coef', self.__gp_tpk_coef)

                    gp_tsp = gp_tsp_coef * np.sqrt(-2 * np.log(10**(gp_deg/20))) / (2*np.pi*src_freq)
                    gp_tpk = gp_tpk_coef * gp_tsp

                    waveform = np.zeros(self.nt, dtype=np.float32)
                    for n in range(self.nt):
                        waveform[n] = src_amp * np.exp(-0.5 * ((n*self.delta_t - gp_tpk)/gp_tsp)**2)

                    print(f'  Gaussian: tsp={gp_tsp*1e15:.2f} fs, tpk={gp_tpk*1e15:.2f} fs (delay)')

                elif src_type == 2:  # Wave Packet
                    wp_bw = source.get('wave_packet_bw', self.__wave_packet_bw)
                    wp_tsp_coef = source.get('wp_tsp_coef', self.__wp_tsp_coef)
                    wp_tpk_coef = source.get('wp_tpk_coef', self.__wp_tpk_coef)

                    wp_tsp = wp_tsp_coef * np.sqrt(np.log(2)) / (wp_bw * 2*np.pi*src_freq)
                    wp_tpk = wp_tpk_coef * wp_tsp

                    waveform = np.zeros(self.nt, dtype=np.float32)
                    for n in range(self.nt):
                        envelope = np.exp(-0.5 * ((n*self.delta_t - wp_tpk)/wp_tsp)**2)
                        carrier = np.exp(2j * np.pi * src_freq * (n*self.delta_t - wp_tpk)).real
                        waveform[n] = src_amp * envelope * carrier

                    print(f'  Wave Packet: tsp={wp_tsp*1e15:.2f} fs, tpk={wp_tpk*1e15:.2f} fs, bw={wp_bw*100:.1f}%')

                elif src_type == 3:  # Time Harmonic
                    # Get ramp-up parameters (can be per-source or use global)
                    gp_deg = source.get('gauss_pulse_deg', self.__gauss_pulse_deg)
                    gp_tsp_coef = source.get('gp_tsp_coef', self.__gp_tsp_coef)
                    gp_tpk_coef = source.get('gp_tpk_coef', self.__gp_tpk_coef)

                    # Generate ramp using Gaussian envelope
                    gp_tsp = gp_tsp_coef * np.sqrt(-2 * np.log(10**(gp_deg/20))) / (2*np.pi*src_freq)
                    gp_tpk = gp_tpk_coef * gp_tsp

                    GP_ramp = np.zeros(self.nt, dtype=np.float32)
                    RAMP = np.zeros(self.nt, dtype=np.float32)
                    for n in range(self.nt):
                        GP_ramp[n] = np.exp(-0.5 * ((n*self.delta_t - gp_tpk)/gp_tsp)**2)
                        RAMP[n] = RAMP[n-1] + self.delta_t * GP_ramp[n]
                    RAMP = RAMP / np.max(RAMP)

                    TH = np.zeros(self.nt, dtype=np.float32)
                    for n in range(self.nt):
                        TH[n] = np.exp(2j*np.pi*src_freq*(n*self.delta_t - gp_tpk)).real

                    # Combine TH and RAMP
                    waveform = src_amp * RAMP * TH

                    print(f'  Time Harmonic: freq={src_freq/1e12:.2f} THz, ramp delay={gp_tpk*1e15:.2f} fs')

                self.source_waveforms.append(waveform)

            # For backward compatibility, also create J_SRC from first source
            self.J_SRC = self.source_waveforms[0]

        else: #Legacy single source line:
            # Gaussian pulse spread and peak time
            self.gp_tsp = self.__gp_tsp_coef * np.sqrt( -2 * np.log( 10**( self.__gauss_pulse_deg / 20 ) ) ) / ( 2 * np.pi * self.__f0 )
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

        #for legacy - but just sets port to 0
        self.port1_length = 0
        self.port2_length = 0
        self.p1x = self.sx + int(self.port1_length/self.delta_x)
        self.p2x = self.sx + self.nx_swg - int(self.port2_length/self.delta_x)

        self.profile_std = str(round(self.__rough_std*1e9))
        self.profile_acl = str(round(self.__rough_acl*1e9))
        self.roughness_profile = '_s'+self.profile_std+'nm_lc'+self.profile_acl+'nm_r'+str(self.profile_number)
        self.up = './rough_profiles/profile_upper'+self.roughness_profile
        self.lp = './rough_profiles/profile_lower'+self.roughness_profile

    # Called in fdtd_main - fills in all the source points from any source lines. assumes all points on line have same qualities
    def expand_source_points(self):
        """
        Expand line sources into arrays of point sources.
        Returns a list where each element is a dict with:
        - 'x', 'y': position in meters
        - 'waveform_idx': which waveform to use (index into source_waveforms)
        """
        expanded_points = []

        for src_idx, source in enumerate(self.sources):
            shape = source.get('shape', 'Point')

            x_start = source['x']
            y_start = source['y']

            #TODO: fix dimensions
            x_start -= self.num_cpml*self.delta_x
            y_start -= self.num_cpml*self.delta_x

            if shape == 'Point':
                # Single point source
                expanded_points.append({
                    'x': x_start,
                    'y': y_start,
                    'waveform_idx': src_idx,
                    'name': source.get('name', f'Source {src_idx}')
                })

            elif shape == 'Line':
                # Line source - expand into multiple points
                x_end = source.get('xend', None)  # If xend exists, horizontal line
                y_end = source.get('yend', None)  # If yend exists, vertical line

                #TODO: fix dimensions
                #x_end -= self.num_cpml*self.delta_x
                #y_end -= self.num_cpml*self.delta_x

                # Calculate line length and number of cells - ok if x start is bigger or x end if bigger
                dx = 0
                dy = 0
                if x_end:
                    x_end -= self.num_cpml*self.delta_x
                    dx = x_end - x_start
                if y_end:
                    y_end -= self.num_cpml*self.delta_x
                    dy = y_end - y_start
                print('dx, dy', dx, dy)
                line_length = np.sqrt(dx**2 + dy**2)
                num_cells = int(line_length / self.delta_x) + 1
                print('line info', line_length, num_cells)

                # Generate points along the line
                for i in range(num_cells):
                    t = i / max(num_cells - 1, 1)  # Parameter from 0 to 1
                    x_pos = x_start + t * dx
                    y_pos = y_start + t * dy
                    print(x_pos, y_pos)
                    expanded_points.append({
                        'x': x_pos,
                        'y': y_pos,
                        'waveform_idx': src_idx,
                        'name': f"{source.get('name', f'Source {src_idx}')} pt{i}"
                    })

        return expanded_points


    # Called in fdtd_main - fills in all the source points from any source lines. assumes all points on line have same qualities
    def expand_measurement_points(self):
        """
        Expand measurement regions into arrays of points IN METERS.
        Grid conversion happens in fdtd_main.
        Returns a list where each element is a dict with:
        - 'type': 'point', 'line', or 'surface'
        - 'name': identifier
        - 'num_points': number of points in measurement region
        - 'x', 'y': position in meters
        """
        if not hasattr(self, '_InitialValues_2DTE_Scattering__measurement_pts') or not self.__measurement_pts:
            return []

        measurement_regions = []
        print(self.__measurement_pts)

        for mp_idx, mp in enumerate(self.__measurement_pts):
            x_start = mp['x']
            y_start = mp['y']
            x_end = mp.get('xend', x_start)
            y_end = mp.get('yend', y_start)
            shape = mp.get('shape', 'Point')  # User specifies shape explicitly

            #TODO: fix dimensions
            x_start -= self.num_cpml*self.delta_x
            y_start -= self.num_cpml*self.delta_x
            x_end -= self.num_cpml*self.delta_x
            y_end -= self.num_cpml*self.delta_x

            # Ensure proper ordering for surfaces
            if x_end < x_start:
                x_start, x_end = x_end, x_start
            if y_end < y_start:
                y_start, y_end = y_end, y_start

            # Generate all points in METERS
            points = []

            if shape == 'Point':
                points.append({'x': x_start, 'y': y_start})
                meas_type = 'point'

            elif shape == 'Line':
                # Handles horizontal, vertical, AND diagonal lines
                dx = x_end - x_start
                dy = y_end - y_start
                line_length = np.sqrt(dx**2 + dy**2)
                num_cells = int(line_length / self.delta_x) + 1

                for i in range(num_cells):
                    t = i / max(num_cells - 1, 1)
                    x_pos = x_start + t * dx
                    y_pos = y_start + t * dy
                    points.append({'x': x_pos, 'y': y_pos})

                meas_type = 'line'

            elif shape == 'Surface':
                # Rectangle - all cells in the region
                nx = int(abs(x_end - x_start) / self.delta_x) + 1
                ny = int(abs(y_end - y_start) / self.delta_x) + 1
                for ix in range(nx):
                    for iy in range(ny):
                        x_pos = x_start + ix * self.delta_x
                        y_pos = y_start + iy * self.delta_x
                        points.append({'x': x_pos, 'y': y_pos})

                meas_type = 'surface'

            else:
                raise ValueError(f"Unknown measurement shape: {shape}")

            safe_name = mp.get('name', f'Measurement {mp_idx}').replace(' ', '_')

            measurement_regions.append({
                'type': meas_type,
                'name': mp.get('name', f'Measurement {mp_idx}'),
                'safe_name': safe_name,
                'num_points': len(points),
                'points': points  # In meters
            })

            print(f"  {mp.get('name', f'Measurement {mp_idx}')} ({meas_type}): {len(points)} points")

        return measurement_regions