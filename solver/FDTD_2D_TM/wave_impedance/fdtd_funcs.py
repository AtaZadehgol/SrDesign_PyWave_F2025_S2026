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
from math import sin, cos


def make_profile(num_x_eff, rough_std, rough_acl, dx, stol, atol, mtol):
    i = 0
    while(True):
        if i > 50000:
            raise Exception('No valid profile for current settings after 300,000 profile iterations')
        test_array = create_exp_1D(num_x_eff, 0.0, rough_std, rough_acl)
        sigma, acl, mm = aux.check_discretization(test_array, dx)
        if i % 100 == 0:
            print('checked {:} profile iterations'.format(i))
        if (1-stol)*rough_std*dx < sigma < (1+stol)*rough_std*dx and (1-atol)*rough_acl*dx < acl < (1+atol)*rough_acl*dx and -mtol < mm < mtol:
            print('Valid discretized profile found after {:} iterations'.format(i))
            break
        i += 1
    return test_array

#this is the mask generator for ONLY ONE waveguide
def gen_fg_mask_sgl(num_x, num_y, bord_y, wg_width, port_len, rough_std, rough_acl, dx, mode='gen', correlation=1, upper_path='', lower_path='', atol=0.1, stol=0.1, mtol=0.01):
    fg_mask = np.zeros([num_x, num_y], dtype=bool)
    num_x_eff = num_x - 2*port_len
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

    wid_wrt_len_upper = np.append(np.zeros(port_len), wid_wrt_len_upper)
    wid_wrt_len_upper = np.append(wid_wrt_len_upper, np.zeros(port_len))
    wid_wrt_len_lower = np.append(np.zeros(port_len), wid_wrt_len_lower)
    wid_wrt_len_lower = np.append(wid_wrt_len_lower, np.zeros(port_len))

    for j in range(num_y):
        for i in range(num_x):
            if j >= (bord_y + wid_wrt_len_lower[i]) and j < (bord_y + wg_width + wid_wrt_len_upper[i]):
                fg_mask[i, j] = True
    return fg_mask

#new grid with roughness functionality!
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
        TOTAL grid dimensions in cells
    bx, by : int
        border sizes (cpml + Buffers) in cells
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

#generate a permeability mask as well
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

@cuda.jit(void(f4[:,:], f4[:,:], f4[:,:], f4[:,:], f4[:,:], f4[:], f4[:], i4, i4))
def update_ez(Ez, Hx, Hy, mod_e, curl_h, den_ex, den_ey, ie, je):
    i, j = cuda.grid(2)
    if i > 0 and i < ie-1:
        if j > 0 and j < je-1:
            Ez[i, j] = mod_e[i, j] * Ez[i, j] + curl_h[i, j]*((Hy[i, j] - Hy[i-1, j])/den_ex[i] + (Hx[i, j-1] - Hx[i, j])/den_ey[j])

'''
@cuda.jit(void(f4[:,:], f4[:,:], f4[:,:], f4, f4[:], f4[:], i4, i4))
def update_hx_hy(Hx, Hy, Ez, curl_e, den_hx, den_hy, ie, je):
    i, j = cuda.grid(2)
    if i < ie-1:
        if j < je-1:
            Hx[i, j] = Hx[i, j] + curl_e*(Ez[i, j] - Ez[i, j+1])/den_hy[j]
            Hy[i, j] = Hy[i, j] + curl_e*(Ez[i+1, j] - Ez[i, j])/den_hx[i]
'''
@cuda.jit(void(f4[:,:], f4[:,:], f4[:,:], f4[:,:], f4[:,:], f4[:], f4[:], i4, i4))
def update_hx_hy(Hx, Hy, Ez, curl_e_x, curl_e_y, den_hx, den_hy, ie, je):
    i, j = cuda.grid(2)
    if i < ie-1:
        if j < je-1:
            Hx[i, j] = Hx[i, j] + curl_e_y[i,j] * (Ez[i, j] - Ez[i, j+1])/den_hy[j]
            Hy[i, j] = Hy[i, j] + curl_e_x[i,j] * (Ez[i+1, j] - Ez[i, j])/den_hx[i]

@cuda.jit(void(f4[:,:], f4[:,:], f4[:,:], f4[:,:], f4[:,:], f4[:,:], f4[:], f4[:], f4, f4, f4, i4, i4, i4))
def update_ez_cpml_x(Psi_Ez_xlo, Psi_Ez_xhi, Ez, Hx, Hy, curl_h, be, ce, del_x, del_t, eps0, ie, je, cpml_range):
    i, j = cuda.grid(2)
    if i > 0 and i < cpml_range:
        if j > 0 and j < je-1:
            Psi_Ez_xlo[i, j] = be[i]*Psi_Ez_xlo[i, j] + ce[i]/del_x*(Hy[i, j] - Hy[i-1, j])
            Ez[i, j] = Ez[i, j] + curl_h[i, j]*del_x*Psi_Ez_xlo[i, j]
            Psi_Ez_xhi[i, j] = be[i]*Psi_Ez_xhi[i, j] + ce[i]/del_x*(Hy[ie-1-i, j] - Hy[ie-2-i, j])
            Ez[ie-1-i, j] = Ez[ie-1-i, j] + curl_h[ie-1-i, j]*del_x*Psi_Ez_xhi[i, j]


@cuda.jit(void(f4[:,:], f4[:,:], f4[:,:], f4[:,:], f4[:,:], f4[:,:], f4[:], f4[:], f4, f4, f4, i4, i4, i4))
def update_ez_cpml_y(Psi_Ez_ylo, Psi_Ez_yhi, Ez, Hx, Hy, curl_h, be, ce, del_x, del_t, eps0, ie, je, cpml_range):
    i, j = cuda.grid(2)
    if i > 0 and i < ie-1:
        if j > 0 and j < cpml_range:
            Psi_Ez_ylo[i, j] = be[j]*Psi_Ez_ylo[i, j] + ce[j]/del_x*(Hx[i, j-1] - Hx[i, j])
            Ez[i, j] = Ez[i, j] + curl_h[i, j]*del_x*Psi_Ez_ylo[i, j]
            Psi_Ez_yhi[i, j] = be[j]*Psi_Ez_yhi[i, j] + ce[j]/del_x*(Hx[i, je-2-j] - Hx[i, je-1-j])
            Ez[i, je-1-j] = Ez[i, je-1-j] + curl_h[i, je-1-j]*del_x*Psi_Ez_yhi[i, j]


@cuda.jit(void(f4[:,:], f4[:,:], f4[:,:], f4[:,:], f4[:], f4[:], f4, f4, f4, i4, i4, i4))
def update_hy_cpml_x(Psi_Hy_xlo, Psi_Hy_xhi, Hy, Ez, bh, ch, del_x, del_t, mu0, ie, je, cpml_range):
    i, j = cuda.grid(2)
    if i > 0 and i < cpml_range:
        if j < je-1:
            Psi_Hy_xlo[i, j] = bh[i]*Psi_Hy_xlo[i, j] + ch[i]/del_x*(Ez[i+1, j] - Ez[i, j])
            Hy[i, j] = Hy[i, j] + del_t/mu0*Psi_Hy_xlo[i, j]
            Psi_Hy_xhi[i, j] = bh[i]*Psi_Hy_xhi[i, j] + ch[i]/del_x*(Ez[ie-1-i, j] - Ez[ie-2-i, j])
            Hy[ie-2-i, j] = Hy[ie-2-i, j] + del_t/mu0*Psi_Hy_xhi[i, j]


@cuda.jit(void(f4[:,:], f4[:,:], f4[:,:], f4[:,:], f4[:], f4[:], f4, f4, f4, i4, i4, i4))
def update_hx_cpml_y(Psi_Hx_ylo, Psi_Hx_yhi, Hx, Ez, bh, ch, del_x, del_t, mu0, ie, je, cpml_range):
    i, j = cuda.grid(2)
    if i < ie-1:
        if j > 0 and j < cpml_range:
            Psi_Hx_ylo[i, j] = bh[j]*Psi_Hx_ylo[i, j] + ch[j]/del_x*(Ez[i, j] - Ez[i, j+1])
            Hx[i, j] = Hx[i, j] + del_t/mu0*Psi_Hx_ylo[i, j]
            Psi_Hx_yhi[i, j] = bh[j]*Psi_Hx_yhi[i, j] + ch[j]/del_x*(Ez[i, je-2-j] - Ez[i, je-1-j])
            Hx[i, je-2-j] = Hx[i, je-2-j] + del_t/mu0*Psi_Hx_yhi[i, j]


@cuda.jit(void(f4[:,:], f4[:,:], f4[:,:], f4, f4, f4, i4, i4))
def simul_fft(Re, Im, F, freq, step, dt, ie, je):
    i, j = cuda.grid(2)
    if i < ie:
        if j < je:
            Re[i, j] = Re[i, j] + F[i, j] * cos( 2 * np.pi * freq * step * dt )
            Im[i, j] = Im[i, j] + F[i, j] * sin( 2 * np.pi * freq * step * dt )


@cuda.jit(void(f4[:,:], f4, i4, i4, i4, i4))
def update_source(Field, Source, sxb, sxe, syb, sye):
    i, j = cuda.grid(2)
    if i >= sxb and i < sxe:
        if j >= syb and j < sye:
            Field[i, j ] = Field[i, j] - Source


#              Ezz    , Ez     , zs, ic, je
@cuda.jit(void(f4[:,:], f4[:,:], i4, i4, i4))
def map_efield_zwave(Ezz, Ez, zwstep, icut, je):
    j = cuda.grid(1)
    if j < je:
        Ezz[zwstep, j] = Ez[icut, j]


#              Hxz    , Hx     , zs, ic, je
@cuda.jit(void(f4[:,:], f4[:,:], i4, i4, i4))
def map_hfield_zwave(Hxz, Hx, zwstep, icut, je):
    j = cuda.grid(1)
    if j < je:
        Hxz[zwstep, j] = 0.5 * (Hx[icut, j] + Hx[icut, j-1])

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
