"""
@author: Brian Guiana

Acknowledgement
This project was completed as part of research conducted with my major professor and advisor, Prof. Ata Zadehgol, as part of the Applied and Computational Electromagnetics Signal and Power Integrity (ACEM-SPI) Lab while working toward the Ph.D. in Electrical Engineering at the University of Idaho, Moscow, Idaho, USA. This project was funded, in part, by the National Science Foundation (NSF); award #1816542 [1].

@editor: Carla Kolze
Senior Capstone Design
"""

import numpy as np
from numba import cuda, f4, i4, void
from pyspeckle import create_exp_1D
from . import aux_funcs as aux
from math import cos, sin


def make_profile(num_x_eff, rough_std, rough_acl, dx, stol, atol, mtol):
    i = 0
    while(True):
        if i > 100000:
            raise Exception('No valid profile for current settings after 300,000 profile iterations')
        test_array = create_exp_1D(num_x_eff, 0.0, rough_std, rough_acl).astype(np.float32)
        sigma, acl, mm = aux.check_discretization(test_array, dx)
        if i % 100 == 0:
            print('checked {:} profile iterations'.format(i))
        if ((1-stol)*rough_std*dx < sigma < (1+stol)*rough_std*dx) and ((1-atol)*rough_acl*dx < acl < (1+atol)*rough_acl*dx) and (-mtol < mm < mtol):
            if not(np.isnan(sigma) or np.isnan(acl) or np.isnan(mm)) or sigma==0 or acl==0:
                print('Valid discretized profile found after {:} iterations'.format(i))
                break
        i += 1
    return test_array

# Old, boolean style for only one waveguide
def gen_fg_mask_sgl(num_x, num_y, bord_y, wg_width, settling_range, end_range, rough_std, rough_acl, dx, mode='gen', correlation=1, upper_path='', lower_path='', atol=0.1, stol=0.1, mtol=0.01):
    fg_mask = np.zeros([num_x, num_y], dtype=bool)
    num_x_eff = num_x - settling_range - end_range
    if mode == 'gen':
        wid_wrt_len_upper = make_profile(num_x_eff, rough_std, rough_acl, dx, stol, atol, mtol)
        if correlation == 1:
            wid_wrt_len_lower = wid_wrt_len_upper.copy()
        elif correlation == 2:
            wid_wrt_len_lower = -1*wid_wrt_len_upper
        elif correlation == 3:
            wid_wrt_len_lower = make_profile(num_x_eff, rough_std, rough_acl, dx, stol, atol, mtol)
        else:
            raise Exception('Choose a valid correlation type')
    elif mode == 'smooth':
        wid_wrt_len_upper = np.zeros(num_x_eff)
        wid_wrt_len_lower = np.zeros(num_x_eff)
    elif mode == 'load':
        if correlation == 1:
            wid_wrt_len_upper = np.load(upper_path+'.npy')
            wid_wrt_len_lower = np.load(upper_path+'.npy')
        elif correlation == 2:
            wid_wrt_len_upper = np.load(upper_path+'.npy')
            wid_wrt_len_lower = -1*np.load(upper_path+'.npy')
        elif correlation == 3:
            wid_wrt_len_upper = np.load(upper_path+'.npy')
            wid_wrt_len_lower = np.load(upper_path+'.npy')
    else:
        raise Exception('Choose a valid roughness profile mode')

    aux.mkdir('rough_profiles')
    np.save(upper_path, wid_wrt_len_upper)
    np.save(lower_path, wid_wrt_len_lower)

    wid_wrt_len_upper = np.append(np.zeros(settling_range), wid_wrt_len_upper)
    wid_wrt_len_upper = np.append(wid_wrt_len_upper, np.zeros(end_range))
    wid_wrt_len_lower = np.append(np.zeros(settling_range), wid_wrt_len_lower)
    wid_wrt_len_lower = np.append(wid_wrt_len_lower, np.zeros(end_range))

    for j in range(num_y):
        for i in range(num_x):
            if j >= (bord_y + wid_wrt_len_lower[i]) and j < (bord_y + wg_width + wid_wrt_len_upper[i]):
                fg_mask[i, j] = True
    return fg_mask

# Grid initializer for multiple waveguides with roughness capability
def gen_eps_map_from_rectangles_textured(nx, ny, rectangles, delta_x, eps_rel_bg, bx, by,
                                  global_rough_toggle=False, 
                                  global_rough_std=0, global_rough_acl=0,
                                  global_tol_std=0.1, global_tol_acl=0.1,
                                  profile_base_path='./rough_profiles'):
    """
    Generate a permittivity map from a list of rectangle specifications.
    
    Parameters:
    -----------
    nx, ny : int
        Grid dimensions in cells
    rectangles : list of dict
        Each dict should have:
        - 'position': {'x': float, 'y': float} in METERS
        - 'dimensions': {'width': float, 'height': float} in METERS
        - 'material': {'permittivity': float}
        - 'roughness': (optional) {
            'rough_toggle': bool,
            'std': float (meters),
            'acl': float (meters),
            'correlation_type': int (1, 2, or 3),
            'tol_std': float (percent, optional),
            'tol_acl': float (percent, optional),
            'tol_mean': float (optional)
          }
    delta_x : float
        Grid spacing in meters (from FDTD solver)
    eps_rel_bg : float
        Background relative permittivity (already squared, e.g., 1.5**2 = 2.25)
    rough_toggle : bool
        Enable roughness on rectangle edges
    rough_std, rough_acl : float
        Roughness parameters in meters (if needed for profile generation)
    rstd, racl : float
        Normalized roughness parameters in cells
    tol_std, tol_acl : float
        Tolerance for roughness profile generation
    ctype : int
        Correlation type (1=correlated, 2=inverse, 3=uncorrelated)
    profile_base_path : str
        Base path for saving/loading roughness profiles
    
    Returns:
    --------
    eps_rel_map : np.ndarray
        2D array of relative permittivity values (normalized by eps_rel_bg)
    """

    #mean tolerance
    MTol = 0.01

    # Initialize to background (normalized to 1.0)
    eps_rel_map = np.ones([nx, ny], dtype=np.float32)

    # Paint each rectangle
    for rect_idx, rect in enumerate(rectangles):
        # Extract rectangle properties (in meters)
        pos_x_meters = rect['position']['x']
        pos_y_meters = rect['position']['y']
        width_meters = rect['dimensions']['width']
        height_meters = rect['dimensions']['height']
        eps_r = rect['material']['permittivity']
        rect_name = rect.get('name', f'rect_{rect_idx}')
        print('ok')

        # Convert from meters to grid cell indices (for 'interior' region where wgs are)
        x_start_interior = int(pos_x_meters / delta_x)
        y_start_interior = int(pos_y_meters / delta_x)
        x_end_interior = int((pos_x_meters + width_meters) / delta_x)
        y_end_interior = int((pos_y_meters + height_meters) / delta_x)

        # Add border offset to get absolute positions in full grid
        x_start = bx + x_start_interior
        y_start = by + y_start_interior
        x_end = bx + x_end_interior
        y_end = by + y_end_interior

        # Clamp to grid bounds
        x_start = max(0, min(x_start, nx-1))
        x_end = max(0, min(x_end, nx))
        y_start = max(0, min(y_start, ny-1))
        y_end = max(0, min(y_end, ny))

        # Normalize permittivity relative to background
        eps_rel_normalized = eps_r / eps_rel_bg

        # Generate or use smooth edges
        rect_width_cells = x_end - x_start
        rect_height_cells = y_end - y_start

        #functional with simple global roughness params
        rect_roughness = rect.get('roughness', {})
        rough_enabled = rect_roughness.get('rough_toggle', global_rough_toggle)

        if rough_enabled and rect_width_cells > 0 and rect_height_cells > 0:
            # Get roughness parameters (use rectangle-specific or fall back to global)
            rough_std = rect_roughness.get('rough_std', global_rough_std)
            rough_acl = rect_roughness.get('rough_acl', global_rough_acl)
            max_acl = (width_meters / 2) - 1e-9
            if rough_acl > max_acl:
                rough_acl = max_acl
            
            ctype = rect_roughness.get('ctype', 3)

            # Get tolerance parameters (use rectangle-specific or fall back to global)
            tol_std = rect_roughness.get('tol_std', global_tol_std)
            tol_acl = rect_roughness.get('tol_acl', global_tol_acl)
            tol_mean = rect_roughness.get('tol_mean', MTol)

            # Convert tolerances from percent to fraction
            tol_std_frac = tol_std / 100.0
            tol_acl_frac = tol_acl / 100.0

            # Convert roughness to cells
            rstd = rough_std / delta_x
            racl = rough_acl / delta_x

            # Generate roughness profiles for this rectangle
            upper_path = f'{profile_base_path}/profile_upper_{rect_name.replace(" ", "_")}'
            lower_path = f'{profile_base_path}/profile_lower_{rect_name.replace(" ", "_")}'

            print(f'Generating roughness for {rect_name}:')
            print(f'  std={rough_std*1e9:.1f}nm (tol=±{tol_std:.1f}%), acl={rough_acl*1e9:.1f}nm (tol=±{tol_acl:.1f}%), type={ctype}')

            # Generate upper and lower edge roughness profiles
            if ctype == 1:
                # Correlated
                upper_profile = make_profile(rect_width_cells, rstd, racl, delta_x, 
                                             tol_std_frac, tol_acl_frac, MTol)
                lower_profile = upper_profile.copy()
            elif ctype == 2:
                # Anti-correlated
                upper_profile = make_profile(rect_width_cells,  rstd, racl, delta_x, 
                                             tol_std_frac, tol_acl_frac, MTol)
                lower_profile = -1 * upper_profile
            elif ctype == 3:
                # Uncorrelated
                upper_profile = make_profile(rect_width_cells, rstd, racl, delta_x, 
                                             tol_std_frac, tol_acl_frac, MTol)
                lower_profile = make_profile(rect_width_cells, rstd, racl, delta_x, 
                                             tol_std_frac, tol_acl_frac, MTol)
            else:
                raise Exception(f'Invalid correlation type {ctype} for rectangle {rect_name}. Choose 1, 2, or 3.')

            # Save profiles
            aux.mkdir(profile_base_path)
            np.save(upper_path, upper_profile)
            np.save(lower_path, lower_profile)

            # Paint rectangle with rough edges
            for i in range(rect_width_cells):
                abs_x = x_start + i
                if abs_x >= nx:
                    break

                # Calculate y range with roughness
                y_lower = y_start + int(lower_profile[i])
                y_upper = y_end + int(upper_profile[i])

                # Clamp to grid bounds
                y_lower = max(0, min(y_lower, ny))
                y_upper = max(0, min(y_upper, ny))

                # Paint this column
                if y_upper > y_lower:
                    eps_rel_map[abs_x, y_lower:y_upper] = eps_rel_normalized
        else:
            # Smooth rectangle (no roughness)
            print(f'Painting smooth rectangle: {rect_name}')
            eps_rel_map[x_start:x_end, y_start:y_end] = eps_rel_normalized

    return eps_rel_map

# Generate a permeability mask as well
def gen_mu_map_from_rectangles(nx, ny, rectangles, delta_x, mu_rel_bg, bx, by):
    """
    Generate a permeability map from a list of rectangle specifications.
    
    Parameters:
    -----------
    nx, ny : int
        TOTAL grid dimensions in cells (including borders)
    bx, by : int
        Border sizes (CPML + buffers) in cells
    rectangles : list of dict
        Each dict should have material.permeability
    delta_x : float
        Grid spacing in meters
    mu_rel_bg : float
        Background relative permeability (typically 1.0)
    
    Returns:
    --------
    mu_rel_map : np.ndarray
        2D array of relative permeability values (normalized by mu_rel_bg)
    """

    # Initialize to background (normalized to 1.0)
    mu_rel_map = np.ones([nx, ny], dtype=np.float32)

    # Paint each rectangle
    for rect_idx, rect in enumerate(rectangles):
        # Extract rectangle properties
        pos_x_meters = rect['position']['x']
        pos_y_meters = rect['position']['y']
        width_meters = rect['dimensions']['width']
        height_meters = rect['dimensions']['height']
        mu_r = rect['material'].get('permeability', 1.0)

        # Convert from meters to grid cell indices (in interior region)
        x_start_interior = int(pos_x_meters / delta_x)
        y_start_interior = int(pos_y_meters / delta_x)
        x_end_interior = int((pos_x_meters + width_meters) / delta_x)
        y_end_interior = int((pos_y_meters + height_meters) / delta_x)

        # Add border offset
        x_start = bx + x_start_interior
        y_start = by + y_start_interior
        x_end = bx + x_end_interior
        y_end = by + y_end_interior

        # Clamp to grid bounds
        x_start = max(0, min(x_start, nx-1))
        x_end = max(0, min(x_end, nx))
        y_start = max(0, min(y_start, ny-1))
        y_end = max(0, min(y_end, ny))

        # Normalize permeability relative to background
        mu_rel_normalized = mu_r / mu_rel_bg

        # Paint rectangle into map
        mu_rel_map[x_start:x_end, y_start:y_end] = mu_rel_normalized

    return mu_rel_map


#                          Ex     , Hz     , kye  , cb     , ib, jb, ie, je
@cuda.jit(func_or_sig=void(f4[:,:], f4[:,:], f4[:], f4[:,:], i4, i4, i4, i4))
def update_ex(Ex, Hz, kye, cb, ib, jb, ie, je):
    i, j = cuda.grid(2)
    if i > ib and i < ie:
        if j >= jb and j < je:
            Ex[i, j] = Ex[i, j] + cb[i, j] * (Hz[i, j+1] - Hz[i, j]) / kye[j]


#                          Ey     , Hz     , kxe  , cb     , ib, jb, ie, je
@cuda.jit(func_or_sig=void(f4[:,:], f4[:,:], f4[:], f4[:,:], i4, i4, i4, i4))
def update_ey(Ey, Hz, kxe, cb, ib, jb, ie, je):
    i, j = cuda.grid(2)
    if i >= ib and i < ie:
        if j > jb and j < je:
            Ey[i, j] = Ey[i, j] + cb[i, j] * (Hz[i, j] - Hz[i+1, j]) / kxe[i]

'''
#                          Ex     , Ey     , Hz     , kxh  , kyh  , db, ib, jb, ie, je
@cuda.jit(func_or_sig=void(f4[:,:], f4[:,:], f4[:,:], f4[:], f4[:], f4, i4, i4, i4, i4))
def update_hz(Ex, Ey, Hz, kxh, kyh, db, ib, jb, ie, je):
    i, j = cuda.grid(2)
    if i > ib and i < ie:
        if j > jb and j < je:
            Hz[i, j] = Hz[i, j] + db * ( (Ex[i, j] - Ex[i, j-1]) / kyh[j] - (Ey[i, j] - Ey[i-1, j]) / kxh[i] )
'''

# NEW signature:
@cuda.jit(func_or_sig=void(f4[:,:], f4[:,:], f4[:,:], f4[:], f4[:], f4[:,:], i4, i4, i4, i4))
def update_hz(Ex, Ey, Hz, kxh, kyh, db, ib, jb, ie, je):
    #                                      ^^^^^^^ now array
    i, j = cuda.grid(2)
    if i > ib and i < ie:
        if j > jb and j < je:
            Hz[i, j] = Hz[i, j] + db[i, j] * ( (Ex[i, j] - Ex[i, j-1]) / kyh[j] - (Ey[i, j] - Ey[i-1, j]) / kxh[i] )
            #                         ^^^^^^ index into array

#                          F      , S    , sx, sm, , step
@cuda.jit(func_or_sig=void(f4[:,:], f4[:], i4, i4, i4, i4))
def update_source(Field, Source, sx, sy_min, sy_max, step):
    i, j = cuda.grid(2)
    if i == sx and j >= sy_min and j < sy_max:
        Field[i, j] = Field[i, j] + Source[step]

#                          Re     , Im     , F      , freq, step, dt, ie, je
@cuda.jit(func_or_sig=void(f4[:,:], f4[:,:], f4[:,:], f4, f4, f4, i4, i4))
def simul_fft(Re, Im, F, freq, step, dt, ie, je):
    i, j = cuda.grid(2)
    if i < ie:
        if j < je:
            Re[i, j] = Re[i, j] + F[i, j] * cos( 2 * np.pi * freq * step * dt )
            Im[i, j] = Im[i, j] + F[i, j] * sin( 2 * np.pi * freq * step * dt )


#                          PEx_yl , PEx_yh , Ex     , Hz     , be   , ce   , cb     , dy, pe, ib, jb, ie, je
@cuda.jit(func_or_sig=void(f4[:,:], f4[:,:], f4[:,:], f4[:,:], f4[:], f4[:], f4[:,:], f4, i4, i4, i4, i4 ,i4))
def update_pml_ex_yinc(Psi_Ex_ylo, Psi_Ex_yhi, Ex, Hz, be, ce, cb, dy, pmle, ib, jb, ie, je):
    i, j = cuda.grid(2)
    if i > ib and i < ie:
        if j < pmle:
            Psi_Ex_ylo[i, j] = be[-(j+1)]*Psi_Ex_ylo[i, j] + ce[-(j+1)]*(Hz[i, jb+j+1] - Hz[i, jb+j])/dy
            Ex[i, jb+j] = Ex[i, jb+j] + cb[i, jb+j]*Psi_Ex_ylo[i, j]
            Psi_Ex_yhi[i, j] = be[j] * Psi_Ex_yhi[i, j] + ce[j] * (Hz[i, je-pmle+j+1] - Hz[i, je-pmle+j])/dy
            Ex[i, je-pmle+j] = Ex[i, je-pmle+j] + cb[i, je-pmle+j]*Psi_Ex_yhi[i, j]


#                          PEy_xl , PEy_xh , Ey     , Hz     , be   , ce   , cb     , dx, pe, ib, jb, ie, je
@cuda.jit(func_or_sig=void(f4[:,:], f4[:,:], f4[:,:], f4[:,:], f4[:], f4[:], f4[:,:], f4, i4, i4, i4, i4, i4))
def update_pml_ey_xinc(Psi_Ey_xlo, Psi_Ey_xhi, Ey, Hz, be, ce, cb, dx, pmle, ib, jb, ie, je):
    i, j = cuda.grid(2)
    if i < pmle:
        if j > jb and j < je and i < pmle:
            Psi_Ey_xlo[i, j] = be[-(i+1)]*Psi_Ey_xlo[i, j] + ce[-(i+1)]*(Hz[ib+i, j] - Hz[ib+i+1, j])/dx
            Ey[ib+i, j] = Ey[ib+i, j] + cb[ib+i, j]*Psi_Ey_xlo[i, j]
            Psi_Ey_xhi[i, j] = be[i] * Psi_Ey_xhi[i, j] + ce[i] * (Hz[ie-pmle+i, j] - Hz[ie-pmle+i+1, j])/dx
            Ey[ie-pmle+i, j] = Ey[ie-pmle+i, j] + cb[ie-pmle+i, j]*Psi_Ey_xhi[i, j]


#                          PHz_xl , PHz_xh , Ey     , Hz     , bh   , ch   , db, dx, pe, ib, jb, ie, je
@cuda.jit(func_or_sig=void(f4[:,:], f4[:,:], f4[:,:], f4[:,:], f4[:], f4[:], f4, f4, i4, i4, i4, i4, i4))
def update_pml_hz_xinc(Psi_Hz_xlo, Psi_Hz_xhi, Ey, Hz, bh, ch, db, dx, pmle, ib, jb, ie, je):
    i, j = cuda.grid(2)
    if i > 0 and i < pmle:
        if j > jb and j < je:
            Psi_Hz_xlo[i, j] = bh[-i]*Psi_Hz_xlo[i, j] + ch[-i]*(Ey[ib+i, j] - Ey[ib+i-1, j])/dx
            Hz[ib+i, j] = Hz[ib+i, j] - db*Psi_Hz_xlo[i, j]
            Psi_Hz_xhi[i, j] = bh[i]*Psi_Hz_xhi[i, j] + ch[i]*(Ey[ie-pmle+i, j] - Ey[ie-pmle+i-1, j])/dx
            Hz[ie-pmle+i, j] = Hz[ie-pmle+i, j] - db*Psi_Hz_xhi[i, j]


#                          PHz_yl , PHz_yh , Ex     , Hz     , bh   , ch   , db, dy, pe, ib, jb, ie, je
@cuda.jit(func_or_sig=void(f4[:,:], f4[:,:], f4[:,:], f4[:,:], f4[:], f4[:], f4, f4, i4, i4, i4, i4, i4))
def update_pml_hz_yinc(Psi_Hz_ylo, Psi_Hz_yhi, Ex, Hz, bh, ch, db, dy, pmle, ib, jb, ie, je):
    i, j = cuda.grid(2)
    if i > ib and i < ie:
        if j > 0 and j < pmle:
            Psi_Hz_ylo[i, j] = bh[-j]*Psi_Hz_ylo[i, j] + ch[-j]*(Ex[i, jb+j] - Ex[i, jb+j-1])/dy
            Hz[i, jb+j] = Hz[i, jb+j] + db*Psi_Hz_ylo[i, j]
            Psi_Hz_yhi[i, j] = bh[j]*Psi_Hz_yhi[i, j] + ch[j]*(Ex[i, je-pmle+j] - Ex[i, je-pmle+j-1])/dy
            Hz[i, je-pmle+j] = Hz[i, je-pmle+j] + db*Psi_Hz_yhi[i, j]

@cuda.jit(void(f4[:,:], f4[:,:], i4[:], i4[:], i4, i4))
def record_measurement_points(measurements, field, mp_x_array, mp_y_array, timestep, num_points):
    """
    Record field values at specific measurement points
    
    measurements: [nt, num_points] - output array
    field: [nx, ny] - current field to sample
    mp_x_array: [num_points] - x-indices of measurement points
    mp_y_array: [num_points] - y-indices of measurement points
    timestep: current time step
    num_points: number of measurement points
    """
    idx = cuda.grid(1)
    if idx < num_points:
        mp_x = mp_x_array[idx]
        mp_y = mp_y_array[idx]
        measurements[timestep, idx] = field[mp_x, mp_y]


@cuda.jit(void(f4[:], f4[:], f4[:,:], i4[:], i4[:], f4, f4, f4, i4))
def simul_fft_points(Re, Im, F, x_indices, y_indices, freq, step, dt, num_points):
    """
    Simultaneous FFT at specific measurement points
    
    Re, Im: [num_points] - accumulated real/imag FFT
    F: [nx, ny] - current field
    x_indices, y_indices: [num_points] - measurement locations
    """
    idx = cuda.grid(1)
    if idx < num_points:
        i = x_indices[idx]
        j = y_indices[idx]
        Re[idx] = Re[idx] + F[i, j] * cos(2 * np.pi * freq * step * dt)
        Im[idx] = Im[idx] + F[i, j] * sin(2 * np.pi * freq * step * dt)