"""
@author: Carla Kolze

Acknowledgement
This project is part of my senior capstone project at the University of Idaho, working with Brian Guiana's code under Professor Ata Zadehgol's request

"""

import numpy as np
import matplotlib.pyplot as plt
import json
import os
from . import aux_funcs as aux

from .IV_2DTM_wave import InitialValues_2DTM_Wave

def zwave(cfg: InitialValues_2DTM_Wave):
    cell = 3
    yref = cfg.by - cell
    ez_td = np.load(f'{cfg.output_dir}/ez_zwave.npy')[:, yref]
    hx_td = np.load(f'{cfg.output_dir}/hx_zwave.npy')[:, yref]
    ez_fd = np.fft.fft(ez_td)
    hx_fd = np.fft.fft(hx_td)
    zw_sim = ez_fd / hx_fd

    ff = np.arange(0, cfg.nt, 1) / (cfg.delta_t * cfg.nt)
    fa = np.linspace(100e12, 300e12, num=100)

    eps0 = 1e-9 / (36 * np.pi)
    k0 = 2 * np.pi * fa / 3e8
    n1 = 3.5
    n2 = 1.5
    d = 100e-9
    neff = np.zeros(len(fa))
    for n in range(len(fa)):
        neff[n] = aux.find_neff(n1, n2, d, k0[n], mode='te')

    beta = k0*neff
    gamma = np.sqrt(beta**2 - n2**2 * k0**2)
    zw_ana = -1j * 2*np.pi*fa * cfg.mu / gamma

    fig, ax = plt.subplots()
    ax.plot(fa/1e12, zw_ana.imag, ls='-', c='k', label='Analytical')
    ax.plot(ff/1e12, zw_sim.imag, ls='', c='r', marker='s', mfc='none', mec='r', label='2D FDTD')

    ax.legend()
    ax.axis([100, 300, -300, 0])
    ax.set_xlabel('Frequency (THz)')
    ax.set_ylabel(r'$\Im\{ Z_{w,TE}^{-d}\}\ (\Omega)$')
    ax.grid(True)

    fig.tight_layout()
    fig.savefig('{}/zwave_te.pdf'.format(cfg.output_dir))

#new to handle things
def zwave_analysis(cfg: InitialValues_2DTM_Wave, measurement_name=None, point_index=None):
    """
    Wave impedance analysis for measurement regions.
    
    Parameters:
    -----------
    cfg : InitialValues_2DTM_Wave
        Configuration object
    measurement_name : str, optional
        Name of measurement region to analyze. If None, looks for legacy data.
    point_index : int or tuple, optional
        For lines/surfaces: which point to analyze
        - int: index into flattened array
        - tuple (ix, iy): for surfaces, spatial indices
        If None, uses first point or averages
    """
    
    # Try to load measurement region data (new system)
    if measurement_name is not None:
        safe_name = measurement_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
        
        ex_file = f'{cfg.output_dir}/ex_{safe_name}.npy'
        hx_file = f'{cfg.output_dir}/hx_{safe_name}.npy'
        #NOTE: assuming we want hx because of legacy, but might want hy? depends on propogation direction
        meta_file = f'{cfg.output_dir}/metadata_{safe_name}.json'
        
        if not os.path.exists(ex_file):
            raise FileNotFoundError(f"Measurement data not found: {ex_file}")
        
        # Load data
        ex_data = np.load(ex_file)  # Shape: [nt, num_points]
        hx_data = np.load(hx_file)  # Shape: [nt, num_points]

        #NOTE: if wave propagates in y direction should be hx??
        
        with open(meta_file) as f:
            metadata = json.load(f)
        
        # Extract time series for analysis
        if metadata['type'] == 'point':
            # Single point - simple
            ex_td = ex_data[:, 0]
            hx_td = hx_data[:, 0]
            analysis_label = f"{measurement_name} (point)"
            
        elif metadata['type'] == 'line':
            # Line - use specific point or average
            if point_index is not None:
                ex_td = ex_data[:, point_index]
                hx_td = hx_data[:, point_index]
                analysis_label = f"{measurement_name} (point {point_index})"
            else:
                # Average across the line
                ex_td = np.mean(ex_data, axis=1)
                hx_td = np.mean(hx_data, axis=1)
                analysis_label = f"{measurement_name} (line average)"
                
        elif metadata['type'] == 'surface':
            # Surface - use specific point or average
            if point_index is not None:
                if isinstance(point_index, tuple):
                    # Convert 2D index to 1D
                    nx_surf, ny_surf = metadata['shape']
                    flat_idx = point_index[0] * ny_surf + point_index[1]
                    ex_td = ex_data[:, flat_idx]
                    hx_td = hx_data[:, flat_idx]
                    analysis_label = f"{measurement_name} (point {point_index})"
                else:
                    ex_td = ex_data[:, point_index]
                    hx_td = hx_data[:, point_index]
                    analysis_label = f"{measurement_name} (point {point_index})"
            else:
                # Average across entire surface
                ex_td = np.mean(ex_data, axis=1)
                hx_td = np.mean(hx_data, axis=1)
                analysis_label = f"{measurement_name} (surface average)"
        
        output_suffix = safe_name
        
    else:
        # Legacy mode - use old cross-section data
        print("Using legacy cross-section data")
        
        cell = 3
        yref = cfg.by - cell
        
        ex_td = np.load(f'{cfg.output_dir}/ex_zwave.npy')[:, yref]
        hx_td = np.load(f'{cfg.output_dir}/hx_zwave.npy')[:, yref]
        analysis_label = f"Legacy (y-cell {yref})"
        output_suffix = "legacy"
    
    # Perform FFT
    ex_fd = np.fft.fft(ex_td)
    hx_fd = np.fft.fft(hx_td)
    zw_sim = -1 * ex_fd / hx_fd
    
    # Frequency array
    ff = np.arange(0, cfg.nt, 1) / (cfg.delta_t * cfg.nt)
    
    # Analytical solution (if applicable)
    # NOTE: This assumes a specific waveguide geometry - modify as needed
    fa = np.linspace(100e12, 300e12, num=100)
    eps0 = 1e-9 / (36 * np.pi)
    k0 = 2 * np.pi * fa / 3e8
    
    # These should come from your actual waveguide parameters
    # For multi-waveguide, you might need to specify which waveguide
    n1 = 3.5  # Core index (e.g., Silicon)
    n2 = 1.5  # Cladding index
    d = 200e-9  # Waveguide height
    
    neff = np.zeros(len(fa))
    for n in range(len(fa)):
        neff[n] = aux.find_neff(n1, n2, d, k0[n], mode='tm')
    
    beta = k0 * neff
    gamma = np.sqrt(beta**2 - n2**2 * k0**2)
    zw_ana = -1 * gamma / (1j * 2*np.pi*fa*eps0*n2**2)
    
    # Plot
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.plot(fa/1e12, zw_ana.imag, ls='-', c='k', lw=2, label='Analytical')
    ax.plot(ff/1e12, zw_sim.imag, ls='', c='r', marker='s', 
            mfc='none', mec='r', ms=4, label=f'Simulation: {analysis_label}')
    
    ax.legend()
    ax.axis([100, 300, 0, 500])
    ax.set_xlabel('Frequency (THz)', fontsize=12)
    ax.set_ylabel(r'$\Im\{ Z_{w,TM}^{-d}\}\ (\Omega)$', fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.set_title(f'Wave Impedance Analysis: {analysis_label}')
    
    fig.tight_layout()
    fig.savefig(f'{cfg.output_dir}/zwave_tm_{output_suffix}.pdf')
    plt.close(fig)
    
    print(f"Saved wave impedance plot: zwave_tm_{output_suffix}.pdf")
    
    return ff, zw_sim, fa, zw_ana


def analyze_all_measurements(cfg: InitialValues_2DTM_Wave):
    """
    Run wave impedance analysis on all measurement regions.
    """
    # Find all measurement metadata files
    import glob
    
    metadata_files = glob.glob(f'{cfg.output_dir}/metadata_*.json')
    
    if len(metadata_files) == 0:
        print("No measurement regions found. Using legacy mode.")
        zwave_analysis(cfg, measurement_name=None)
        return
    
    print(f"Found {len(metadata_files)} measurement regions")
    
    for meta_file in metadata_files:
        # Extract measurement name from filename
        # metadata_Output_Point_1.json -> Output_Point_1
        safe_name = os.path.basename(meta_file).replace('metadata_', '').replace('.json', '')
        
        with open(meta_file) as f:
            metadata = json.load(f)
        
        measurement_name = metadata['name']
        
        print(f"\nAnalyzing: {measurement_name} ({metadata['type']})")
        
        try:
            # For points and lines, analyze directly
            if metadata['type'] in ['point', 'line']:
                zwave_analysis(cfg, measurement_name=measurement_name)
            
            # For surfaces, you might want to analyze specific points or average
            elif metadata['type'] == 'surface':
                # Option 1: Average across surface
                zwave_analysis(cfg, measurement_name=measurement_name, point_index=None)
                
                # Option 2: Analyze center point
                # nx, ny = metadata['shape']
                # center_idx = (nx//2, ny//2)
                # zwave_analysis(cfg, measurement_name=measurement_name, point_index=center_idx)
                
        except Exception as e:
            print(f"  Error analyzing {measurement_name}: {e}")
