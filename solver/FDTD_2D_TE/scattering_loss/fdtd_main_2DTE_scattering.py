"""
@author: Carla Kolze

Acknowledgement
This project is part of my senior capstone project at the University of Idaho, working with Brian Guiana's code under Professor Ata Zadehgol's request

"""

import numpy as np
import os
import psutil
from time import time
from numba import cuda

#import fdtd_config as cfg
from . import fdtd_funcs as funcs
from . import aux_funcs as aux

from .IV_2DTE_scattering import InitialValues_2DTE_Scattering

def solver(cfg: InitialValues_2DTE_Scattering):
    print('The simulation size will be: {:} x {:} cubic cells over {:} time steps\n\n\n'.format(cfg.nx, cfg.ny, cfg.nt))
    aux.mkdir(cfg.output_dir)
    cuda.select_device(0)

    # =============================================================================
    # Main array definition
    # =============================================================================

    EX = np.zeros([cfg.nx, cfg.ny], dtype=np.float32)     # Electric field at current time step, x-component
    EY = np.zeros([cfg.nx, cfg.ny], dtype=np.float32)     # Electric field at current time step, y-component
    HZ = np.zeros([cfg.nx, cfg.ny], dtype=np.float32)     # Magnetic field at current time step, z-component

    # Assign Materials
    if hasattr(cfg, 'rectangles') and len(cfg.rectangles) > 0:
        print('has rect attr')
        #multi-material: use rectangles from json
        EPS_REL_MAP = funcs.gen_eps_map_from_rectangles_textured(
            cfg.nx, cfg.ny, cfg.rectangles, cfg.delta_x, cfg.eps_rel_bg,
            cfg.bx, cfg.by,
            global_rough_toggle=cfg.rough_toggle,
            global_rough_std=cfg.rough_std,
            global_rough_acl=cfg.rough_acl,
            global_tol_std=cfg.tol_std,
            global_tol_acl=cfg.tol_acl,
            profile_base_path='./rough_profiles'
        )

        print('\n=== Permittivity Map Debug Info ===')
        print(f'EPS_REL_MAP shape: {EPS_REL_MAP.shape}')
        print(f'EPS_REL_MAP dtype: {EPS_REL_MAP.dtype}')
        print(f'EPS_REL_MAP unique values (relative): {np.unique(EPS_REL_MAP)}')
        print(f'EPS_REL_MAP min: {np.min(EPS_REL_MAP):.4f}, max: {np.max(EPS_REL_MAP):.4f}')
        print(f'Background ε_r: {cfg.eps_rel_bg:.4f}')  

        EPS_MASK = (cfg.eps * EPS_REL_MAP).astype(np.float32)

        #generate permeability map
        MU_REL_MAP = funcs.gen_mu_map_from_rectangles(
            cfg.nx, cfg.ny, cfg.rectangles, cfg.delta_x, cfg.mu_rel_bg,
            cfg.bx, cfg.by
        )

        print('\n=== Permeability Map Debug Info ===')
        print(f'MU_REL_MAP shape: {MU_REL_MAP.shape}')
        print(f'MU_REL_MAP dtype: {MU_REL_MAP.dtype}')
        print(f'MU_REL_MAP unique values (relative): {np.unique(MU_REL_MAP)}')
        print(f'MU_REL_MAP min: {np.min(MU_REL_MAP):.4f}, max: {np.max(MU_REL_MAP):.4f}')
        print(f'Background μ_r: {cfg.mu_rel_bg:.4f}')

        MU_MASK = (cfg.mu * MU_REL_MAP).astype(np.float32)

    else:
            #legacy single-waveguide case
        print('legacy single waveguide')
        if cfg.rough_toggle:
            FG_REG = funcs.gen_fg_mask_sgl(cfg.nx, cfg.ny, cfg.by, cfg.ny_swg, cfg.p1x, cfg.nx-cfg.p2x, cfg.rstd, cfg.racl, cfg.delta_x, mode='gen', correlation=cfg.ctype, upper_path=cfg.up, lower_path=cfg.lp, atol=cfg.tol_acl, stol=cfg.tol_std, mtol=0.01)
        else:
            FG_REG = funcs.gen_fg_mask_sgl(cfg.nx, cfg.ny, cfg.by, cfg.ny_swg, cfg.p1x, cfg.nx-cfg.p2x, cfg.rstd, cfg.racl, cfg.delta_x, mode='smooth')

        EPS_MASK = (cfg.eps * ( cfg.eps_rel_fg * FG_REG + 1 * ~FG_REG )).astype(np.float32)
        MU_MASK = np.ones([cfg.nx, cfg.ny], dtype=np.float32) * cfg.mu  # All non-magnetic


    EPS_EX = EPS_MASK.copy().astype(np.float32)
    EPS_EY = EPS_MASK.copy().astype(np.float32)

    MU_HZ = MU_MASK.copy().astype(np.float32)

    for j in range(1, cfg.ny):
        for i in range(1, cfg.nx):
            EPS_EX[i, j] = 0.5 * (EPS_MASK[i, j] + EPS_MASK[i-1, j])
            EPS_EY[i, j] = 0.5 * (EPS_MASK[i, j] + EPS_MASK[i, j-1])
            # Average permeability for Hz component (at cell corners)
            MU_HZ[i, j] = 0.25 * (MU_MASK[i, j] + MU_MASK[i-1, j] + MU_MASK[i, j-1] + MU_MASK[i-1, j-1])

    CBX = cfg.delta_t / EPS_EX
    CBY = cfg.delta_t / EPS_EY
    DB = cfg.delta_t / MU_HZ #array for main domain
    DB_CPML = (cfg.delta_t / cfg.mu).astype(np.float32) #scalar for cpml


    # Define data storage arrays
    HZfr = np.zeros([cfg.nx, cfg.ny], dtype=np.float32)
    HZfi = np.zeros([cfg.nx, cfg.ny], dtype=np.float32)
    EYfr = np.zeros([cfg.nx, cfg.ny], dtype=np.float32)
    EYfi = np.zeros([cfg.nx, cfg.ny], dtype=np.float32)

    EXfr = np.zeros([cfg.nx, cfg.ny], dtype=np.float32)
    EXfi = np.zeros([cfg.nx, cfg.ny], dtype=np.float32)

    # NEW: Measurement regions
    if hasattr(cfg, 'measurement_pts') and cfg.measurement_pts:
        measurement_regions = cfg.expand_measurement_points()
        if len(measurement_regions) > 0:
            print(f'\n=== Measurement Regions ===')
            print(f'Total regions: {len(measurement_regions)}')

            # Create FREQUENCY-DOMAIN storage for each region (not time-domain!)
            measurement_data = []
            '''
            for region in measurement_regions:
                num_pts = region['num_points']
                region_data = {
                    'name': region['name'],
                    'safe_name': region['safe_name'],
                    'type': region['type'],
                    'EX': np.zeros([cfg.nt, num_pts], dtype=np.float32),
                    'EY': np.zeros([cfg.nt, num_pts], dtype=np.float32),
                    'HZ': np.zeros([cfg.nt, num_pts], dtype=np.float32),
                }
            '''
            for region in measurement_regions:
                num_pts = region['num_points']
                region_data = {
                    'name': region['name'],
                    'safe_name': region['safe_name'],
                    'type': region['type'],
                    # Frequency domain - no time dimension
                    'EX_real': np.zeros([num_pts], dtype=np.float32),
                    'EX_imag': np.zeros([num_pts], dtype=np.float32),
                    'EY_real': np.zeros([num_pts], dtype=np.float32),
                    'EY_imag': np.zeros([num_pts], dtype=np.float32),
                    'HZ_real': np.zeros([num_pts], dtype=np.float32),
                    'HZ_imag': np.zeros([num_pts], dtype=np.float32),
                }
                measurement_data.append(region_data)

            print('===========================\n')
        else:
            measurement_regions = None
            measurement_data = None
    else:
        measurement_regions = None
        measurement_data = None

    # =============================================================================
    # Begin CPML
    # =============================================================================

    # Computational domain limits
    offset = 2
    ll = 0+offset
    lb = 0+offset
    lr = cfg.nx - ll
    lt = cfg.ny - lb

    # Constants
    m_grade = 4                                     # Grading maximum exponent for sigma and kappa
    m_alpha = 1                                     # Grading maximum exponent for alpha
    cpml_sigma_optimal = 0.8 * ( m_grade + 1 ) / ( cfg.eta * cfg.delta_x )  # Optimal sigma value
    cpml_sigma_max = 1.2 * cpml_sigma_optimal       # Maximum sigma value
    cpml_alpha_max = 0.05                           # Maximum alpha value
    cpml_kappa_max = 5                          # Maximum kappa value if CPML is on

    # # Define arrays
    PSI_EX_YLO = np.zeros([cfg.nx, cfg.num_cpml], dtype=np.float32)     # Ex correction field, low-side y-boundary
    PSI_EX_YHI = np.zeros([cfg.nx, cfg.num_cpml], dtype=np.float32)     # Ex correction field, high-side y-boundary
    PSI_EY_XLO = np.zeros([cfg.num_cpml, cfg.ny], dtype=np.float32)     # Ey correction field, low-side x-boundary
    PSI_EY_XHI = np.zeros([cfg.num_cpml, cfg.ny], dtype=np.float32)     # Ey correction field, high-side x-boundary

    PSI_HZ_XLO = np.zeros([cfg.num_cpml, cfg.ny], dtype=np.float32)     # Hz correction field, low-side x-boundary
    PSI_HZ_XHI = np.zeros([cfg.num_cpml, cfg.ny], dtype=np.float32)     # Hz correction field, high-side x-boundary
    PSI_HZ_YLO = np.zeros([cfg.nx, cfg.num_cpml], dtype=np.float32)     # Hz correction field, low-side y-boundary
    PSI_HZ_YHI = np.zeros([cfg.nx, cfg.num_cpml], dtype=np.float32)     # Hz correction field, high-side y-boundary

    SE = np.zeros(cfg.num_cpml, dtype=np.float32)
    KE = np.zeros(cfg.num_cpml, dtype=np.float32)
    AE = np.zeros(cfg.num_cpml, dtype=np.float32)
    BE = np.zeros(cfg.num_cpml, dtype=np.float32)
    CE = np.zeros(cfg.num_cpml, dtype=np.float32)

    SH = np.zeros(cfg.num_cpml, dtype=np.float32)
    KH = np.zeros(cfg.num_cpml, dtype=np.float32)
    AH = np.zeros(cfg.num_cpml, dtype=np.float32)
    BH = np.zeros(cfg.num_cpml, dtype=np.float32)
    CH = np.zeros(cfg.num_cpml, dtype=np.float32)

    KXE = np.ones(cfg.nx, dtype=np.float32) * cfg.delta_x
    KYE = np.ones(cfg.ny, dtype=np.float32) * cfg.delta_x
    KXH = np.ones(cfg.nx, dtype=np.float32) * cfg.delta_x
    KYH = np.ones(cfg.ny, dtype=np.float32) * cfg.delta_x

    for d in range(cfg.num_cpml):
        SE[d] = cpml_sigma_max * ( (d+0.5)/cfg.num_cpml )**m_grade
        KE[d] = 1 + (cpml_kappa_max - 1)*( (d+0.5)/cfg.num_cpml )**m_grade
        AE[d] = cpml_alpha_max * ((cfg.num_cpml - (d+0.5))/cfg.num_cpml)**m_alpha
        BE[d] = np.exp( -1 * ( SE[d]/KE[d] + AE[d] ) * ( cfg.delta_t / cfg.eps ) )
        CE[d] = SE[d] / (SE[d] * KE[d] + KE[d]**2 * AE[d]) * (BE[d] - 1)

        SH[d] = cpml_sigma_max * ( d/cfg.num_cpml )**m_grade
        KH[d] = 1 + (cpml_kappa_max - 1)*( d/cfg.num_cpml )**m_grade
        AH[d] = cpml_alpha_max * ((cfg.num_cpml - d)/cfg.num_cpml)**m_alpha
        BH[d] = np.exp( -1 * ( SH[d]/KH[d] + AH[d] ) * ( cfg.delta_t / cfg.eps ) )
        CH[d] = SH[d] / (SH[d] * KH[d] + KH[d]**2 * AH[d]) * (BH[d] - 1)

    for d in range(cfg.num_cpml):
        KXE[ll+cfg.num_cpml-(d+1)] = KE[d] * cfg.delta_x  # dx
        KYE[lb+cfg.num_cpml-(d+1)] = KE[d] * cfg.delta_x  # dy
        KXH[ll+cfg.num_cpml-d] = KH[d] * cfg.delta_x      # dx
        KYH[lb+cfg.num_cpml-d] = KH[d] * cfg.delta_x      # dy
        KXE[lr-(d+1)] = KE[-(d+1)] * cfg.delta_x          # dx
        KYE[lt-(d+1)] = KE[-(d+1)] * cfg.delta_x          # dy
        KXH[lr-(d+1)] = KH[-(d+1)] * cfg.delta_x          # dx
        KYH[lt-(d+1)] = KH[-(d+1)] * cfg.delta_x          # dy

    # =============================================================================
    # GPU Processing Setup
    # =============================================================================

    # Declare thread sizes
    tpbx = 1
    tpby = 128

    # Declare block sizes
    bpgx = int(np.ceil(cfg.nx / tpbx))
    bpgy = int(np.ceil(cfg.ny / tpby))
    bpgx_pml = int(np.ceil(cfg.num_cpml / tpbx))
    bpgy_pml = int(np.ceil(cfg.num_cpml / tpby))

    # Combine into tuples
    tpb = (tpbx, tpby)
    bpg_xy = (bpgx, bpgy)
    bpg_xp = (bpgx, bpgy_pml)
    bpg_py = (bpgx_pml, bpgy)

    # GPU process feedback
    cells_on_device = 5*(cfg.nx*cfg.ny) + 4*(cfg.num_cpml*cfg.nx + cfg.num_cpml*cfg.ny + cfg.num_cpml) + 2*(cfg.nx + cfg.ny) + 1*(cfg.nt)
    device_req_mem = 4*cells_on_device / 1024 / 1024
    print('Transferring {:.0f} Mcells onto GPU, requiring {:} MB'.format(cells_on_device/1e6, device_req_mem))

    # Device arrays of size (nx*ny)
    dEX = cuda.to_device(EX)
    dEY = cuda.to_device(EY)
    dHZ = cuda.to_device(HZ)
    dCBX = cuda.to_device(CBX)
    dCBY = cuda.to_device(CBY)
    #new DB for permeability
    dDB = cuda.to_device(DB)

    dHZfr = cuda.to_device(HZfr)
    dHZfi = cuda.to_device(HZfi)
    dEYfr = cuda.to_device(EYfr)
    dEYfi = cuda.to_device(EYfi)

    dEXfr = cuda.to_device(EXfr)
    dEXfi = cuda.to_device(EXfi)

    # Device arrays of size (num_cpml*nx)
    dPSI_EX_YLO = cuda.to_device(PSI_EX_YLO)
    dPSI_EX_YHI = cuda.to_device(PSI_EX_YHI)
    dPSI_HZ_YLO = cuda.to_device(PSI_HZ_YLO)
    dPSI_HZ_YHI = cuda.to_device(PSI_HZ_YHI)

    # Device arrays of size (num_cpml*ny)
    dPSI_EY_XLO = cuda.to_device(PSI_EY_XLO)
    dPSI_EY_XHI = cuda.to_device(PSI_EY_XHI)
    dPSI_HZ_XLO = cuda.to_device(PSI_HZ_XLO)
    dPSI_HZ_XHI = cuda.to_device(PSI_HZ_XHI)

    # Device arrays of size (num_cpml)
    dBE = cuda.to_device(BE)
    dBH = cuda.to_device(BH)
    dCE = cuda.to_device(CE)
    dCH = cuda.to_device(CH)

    # Device arrays of size (nx)
    dKXE = cuda.to_device(KXE)
    dKXH = cuda.to_device(KXH)

    # Device arrays of size (ny)
    dKYE = cuda.to_device(KYE)
    dKYH = cuda.to_device(KYH)

    # Device arrays of size (nt)
    dJ_SRC = cuda.to_device(cfg.J_SRC)

    # =============================================================================
    # Multi-source setup
    # =============================================================================

    if hasattr(cfg, 'sources') and cfg.sources and len(cfg.sources) > 0:
        print('\\n=== Multi-source mode ===')

        # Expand line sources into individual points
        expanded_sources = cfg.expand_source_points()
        print(f'Total source points: {len(expanded_sources)}')

        # Transfer all source waveforms to GPU
        device_waveforms = []
        for idx, waveform in enumerate(cfg.source_waveforms):
            device_waveforms.append(cuda.to_device(waveform))

        # Pre-calculate grid positions for all source points
        source_positions = []
        for src_point in expanded_sources:
            src_x = int(src_point['x'] / cfg.delta_x) + cfg.bx  # Add border offset
            src_y = int(src_point['y'] / cfg.delta_x) + cfg.by  # Add border offset
            wf_idx = src_point['waveform_idx']

            source_positions.append({
                'x': src_x,
                'y': src_y,
                'waveform': device_waveforms[wf_idx],
                'name': src_point['name']
            })
            print(f"  {src_point['name']}: grid position ({src_x}, {src_y}), waveform {wf_idx}")

        print('===========================\\n')
    else:
        print('Using legacy single-source mode\\n')
        expanded_sources = None
        source_positions = None

    # =============================================================================
    # Measurement region setup
    # =============================================================================

    # SCATTERING RECORDS ALL MSMTS??

    if measurement_regions is not None:
        print('\n=== Converting measurement points to grid indices ===')

        # Convert all measurement points from meters to grid indices
        for idx, region in enumerate(measurement_regions):
            x_indices = []
            y_indices = []

            for pt in region['points']:
                # Convert meters to grid cells and add border offset
                x_idx = int(pt['x'] / cfg.delta_x) + cfg.bx
                y_idx = int(pt['y'] / cfg.delta_x) + cfg.by
                x_indices.append(x_idx)
                y_indices.append(y_idx)

            # Store as numpy arrays in measurement_data
            measurement_data[idx]['x_indices'] = np.array(x_indices, dtype=np.int32)
            measurement_data[idx]['y_indices'] = np.array(y_indices, dtype=np.int32)

        # Transfer measurement arrays and indices to GPU
        device_measurement_data = []

        for idx, region in enumerate(measurement_regions):
            mdata = measurement_data[idx]

            '''
                'dEX': cuda.to_device(mdata['EZ']),
                'dEY': cuda.to_device(mdata['HX']),
                'dHZ': cuda.to_device(mdata['HY']),
            '''

            device_region = {
                'name': mdata['name'],
                'safe_name': mdata['safe_name'],
                'type': mdata['type'],
                'num_points': region['num_points'],
                'dEX_real': cuda.to_device(mdata['EX_real']),
                'dEX_imag': cuda.to_device(mdata['EX_imag']),
                'dEY_real': cuda.to_device(mdata['EY_real']),
                'dEY_imag': cuda.to_device(mdata['EY_imag']),
                'dHZ_real': cuda.to_device(mdata['HZ_real']),
                'dHZ_imag': cuda.to_device(mdata['HZ_imag']),
                'dx_indices': cuda.to_device(mdata['x_indices']),
                'dy_indices': cuda.to_device(mdata['y_indices']),
                'bpg': int(np.ceil(region['num_points'] / tpby))
            }
            device_measurement_data.append(device_region)
        
            # Setup grid for this region
            #bpg_region = int(np.ceil(region['num_points'] / tpby))
            #device_region['bpg'] = bpg_region
            #print(f"  {region['name']} ({region['type']}): {region['num_points']} points, bpg={bpg_region}")
            print(f"  {region['name']} ({region['type']}): {region['num_points']} points")

        print('===========================\n')
    else:
        device_measurement_data = None


    import matplotlib.pyplot as plt
    # After material assignment (around line 70 in fdtd_main)
    if hasattr(cfg, 'rectangles') and len(cfg.rectangles) > 0:
        # ... material setup code ...
        
        # VISUALIZATION: Check material maps
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        
        # Permittivity map
        im0 = axes[0, 0].imshow(EPS_MASK.T, origin='lower', aspect='auto', cmap='viridis')
        axes[0, 0].set_title('Permittivity (ε)')
        axes[0, 0].set_xlabel('x (cells)')
        axes[0, 0].set_ylabel('y (cells)')
        plt.colorbar(im0, ax=axes[0, 0])
        
        # Permeability map
        im1 = axes[0, 1].imshow(MU_MASK.T, origin='lower', aspect='auto', cmap='plasma')
        axes[0, 1].set_title('Permeability (μ)')
        plt.colorbar(im1, ax=axes[0, 1])
        
        # Combined (eps * mu for refractive index squared)
        n_squared = (EPS_MASK / cfg.eps) * (MU_MASK / cfg.mu)
        im2 = axes[1, 0].imshow(n_squared.T, origin='lower', aspect='auto', cmap='RdYlBu_r')
        axes[1, 0].set_title('n² (ε_r × μ_r)')
        plt.colorbar(im2, ax=axes[1, 0])
        
        # Mark sources and measurements if they exist
        axes[1, 1].imshow(EPS_MASK.T, origin='lower', aspect='auto', cmap='gray', alpha=0.3)
        
        # Plot sources
        if expanded_sources:
            for src in expanded_sources:
                src_x_grid = int(src['x'] / cfg.delta_x) + cfg.bx
                src_y_grid = int((src['y']) / cfg.delta_x) + cfg.by
                axes[1, 1].plot(src_x_grid, src_y_grid, 'ro', ms=10, label='Source')
        
        # Plot measurements
        if measurement_regions:
            for region in measurement_regions:
                for pt in region['points']:
                    x_idx = int(pt['x'] / cfg.delta_x) + cfg.bx
                    y_idx = int((pt['y']) / cfg.delta_x) + cfg.by
                    axes[1, 1].plot(x_idx, y_idx, 'g.', ms=2)
        
        axes[1, 1].set_title('Sources (red) & Measurements (green)')
        axes[1, 1].set_xlabel('x (cells)')
        axes[1, 1].set_ylabel('y (cells)')
        
        plt.tight_layout()
        plt.savefig(f'{cfg.output_dir}/domain_initialization.png', dpi=150)
        print(f'Saved domain visualization to {cfg.output_dir}/domain_initialization.png')
        plt.close()


    # =============================================================================
    # Time stepping loop
    # =============================================================================

    feedback_interval = np.round(np.linspace(0, cfg.nt, num=101))
    process = psutil.Process(os.getpid())
    last40 = np.zeros(40)
    loop_start_time = time()
    cu_time = time() - loop_start_time

    print('loop started')
    for n in range(cfg.nt):
        # Update H-field component
        funcs.update_hz[bpg_xy, tpb](dEX, dEY, dHZ, dKXH, dKYH, dDB, ll, lb, lr, lt)    #updated

        # Update H-field component in PML
        funcs.update_pml_hz_yinc[bpg_xp, tpb](dPSI_HZ_YLO, dPSI_HZ_YHI, dEX, dHZ, dBH, dCH, DB_CPML, cfg.delta_x, cfg.num_cpml, ll, lb, lr, lt)
        funcs.update_pml_hz_xinc[bpg_py, tpb](dPSI_HZ_XLO, dPSI_HZ_XHI, dEY, dHZ, dBH, dCH, DB_CPML, cfg.delta_x, cfg.num_cpml, ll, lb, lr, lt)

        # Update source conditions
        if source_positions is not None:
            # Multi-source mode: inject at each source point
            for src_pos in source_positions:
                # Point source (3-cell span for numerical stability)
                funcs.update_source[bpg_xy, tpb](dHZ, src_pos['waveform'], 
                                                src_pos['x'], 
                                                src_pos['y']-1, 
                                                src_pos['y']+2, 
                                                n)
        else: 
            funcs.update_source[bpg_xy, tpb](dHZ, dJ_SRC, cfg.sx, cfg.by+2, cfg.by+cfg.ny_swg-2, n)

        # Update E-field components
        funcs.update_ex[bpg_xy, tpb](dEX, dHZ, dKYE, dCBX, ll, lb, lr, lt)
        funcs.update_ey[bpg_xy, tpb](dEY, dHZ, dKXE, dCBY, ll, lb, lr, lt)

        # Update E-field components in PML
        funcs.update_pml_ex_yinc[bpg_xp, tpb](dPSI_EX_YLO, dPSI_EX_YHI, dEX, dHZ, dBE, dCE, dCBX, cfg.delta_x, cfg.num_cpml, ll, lb, lr, lt)
        funcs.update_pml_ey_xinc[bpg_py, tpb](dPSI_EY_XLO, dPSI_EY_XHI, dEY, dHZ, dBE, dCE, dCBY, cfg.delta_x, cfg.num_cpml, ll, lb, lr, lt)

        # Record Data
        funcs.simul_fft[bpg_xy, tpb](dHZfr, dHZfi, dHZ, cfg.f0, n+0.0, cfg.delta_t, cfg.nx, cfg.ny)
        funcs.simul_fft[bpg_xy, tpb](dEYfr, dEYfi, dEY, cfg.f0, n+0.5, cfg.delta_t, cfg.nx, cfg.ny)
        funcs.simul_fft[bpg_xy, tpb](dEXfr, dEXfi, dEY, cfg.f0, n+0.5, cfg.delta_t, cfg.nx, cfg.ny)

        '''
        # NEW: Record at measurement regions
        if device_measurement_data is not None:
            for region_data in device_measurement_data:
                funcs.record_measurement_points[region_data['bpg'], tpby](
                    region_data['dEX'], dEX, region_data['dx_indices'], 
                    region_data['dy_indices'], n, region_data['num_points']
                )
                funcs.record_measurement_points[region_data['bpg'], tpby](
                    region_data['dEY'], dEY, region_data['dx_indices'], 
                    region_data['dy_indices'], n, region_data['num_points']
                )
                funcs.record_measurement_points[region_data['bpg'], tpby](
                    region_data['dHZ'], dHZ, region_data['dx_indices'], 
                    region_data['dy_indices'], n, region_data['num_points']
                )
        '''
        print('recording')
        # NEW: Record FFT at measurement regions
        if device_measurement_data is not None:
            for region_data in device_measurement_data:
                funcs.simul_fft_points[region_data['bpg'], tpby](
                    region_data['dEX_real'], region_data['dEX_imag'], dEX, 
                    region_data['dx_indices'], region_data['dy_indices'],
                    cfg.f0, n+0.5, cfg.delta_t, region_data['num_points']
                )
                funcs.simul_fft_points[region_data['bpg'], tpby](
                    region_data['dEY_real'], region_data['dEY_imag'], dEY,
                    region_data['dx_indices'], region_data['dy_indices'],
                    cfg.f0, n+0.5, cfg.delta_t, region_data['num_points']
                )
                funcs.simul_fft_points[region_data['bpg'], tpby](
                    region_data['dHZ_real'], region_data['dHZ_imag'], dHZ,
                    region_data['dx_indices'], region_data['dy_indices'],
                    cfg.f0, n+0.0, cfg.delta_t, region_data['num_points']
                )

        # Progress feedback
        last40 = np.roll(last40, 1)
        iter_time = time() - cu_time - loop_start_time
        cu_time = time() - loop_start_time
        last40[0] = iter_time
        if (n == feedback_interval).any():
            avg_iter_time = np.average(last40)
            cu_time = time() - loop_start_time
            time_rem = avg_iter_time * ( cfg.nt - n - 1 )
            print('\nStep {} of {} done, {:.1f} % complete'.format(n+1, cfg.nt, n/(cfg.nt-2)*100))
            print('Loop time elapsed:         {} (hr) {} (min) {:.1f} (s)'.format(int(cu_time/3600), int((cu_time - 3600*(cu_time//3600))//60), cu_time - 60*((cu_time - 3600*(cu_time//3600))//60) - 3600*(cu_time//3600)))
            print('Avg. loop period:          {:.2f} (ms)'.format(avg_iter_time*1000))
            print('Estimated time remaining:  {} (hr) {} (min) {:.1f} (s)'.format(int(time_rem/3600), int((time_rem - 3600*(time_rem//3600))//60), time_rem - 60*((time_rem - 3600*(time_rem//3600))//60) - 3600*(time_rem//3600)))
            print('Memory used:              {:6.3f} (GB)'.format(process.memory_info().rss/1024/1024/1024))
            print('MC/sec:                    {}'.format((cfg.nx * cfg.ny) / (1e6 * avg_iter_time)))

    # =============================================================================
    # Post-simulation processes and analytics
    # =============================================================================

    looping_time = time() - loop_start_time
    SPEED_MCells_Sec = (cfg.nx * cfg.ny * cfg.nt) / (1e6 * looping_time)
    lth = int(np.floor(looping_time / 3600))
    ltm = int(np.floor((looping_time - lth*3600) / 60))
    lts = int(np.ceil(looping_time - lth*3600 - ltm*60))
    if lts == 60:
        lts -= 60
        ltm += 1
    if ltm < 10:
        ltm = '0'+str(ltm)
    if lts < 10:
        lts = '0'+str(lts)
    print('FDTD loop time was: {:}:{:}:{:}'.format(lth, ltm, lts))
    print('Speed in MCells/sec: {:}'.format(SPEED_MCells_Sec))

    # =============================================================================
    # Save storage arrays to files
    # =============================================================================

    '''
    print('saving results')
    np.save(cfg.output_dir+'/'+cfg.hz_fft_name+cfg.roughness_profile, dHZfr.copy_to_host() - 1j*dHZfi.copy_to_host())
    np.save(cfg.output_dir+'/'+cfg.ey_fft_name+cfg.roughness_profile, dEYfr.copy_to_host() - 1j*dEYfi.copy_to_host())
    print('results saved!')
    '''
    print(f'Saving results to {cfg.output_dir}')
    np.save('{}/hz_zwave'.format(cfg.output_dir), dHZfr.copy_to_host() - j*dHZfi.copy_to_host())
    np.save('{}/ey_zwave'.format(cfg.output_dir), dEYfr.copy_to_host() - j*dEYfi.copy_to_host())
    np.save('{}/ex_zwave'.format(cfg.output_dir), dEXfr.copy_to_host() - j*dEXfi.copy_to_host())

    # NEW: Save measurement region frequency-domain data
    if device_measurement_data is not None:
        import json
        
        for idx, region_data in enumerate(device_measurement_data):
            safe_name = region_data['safe_name']
            mdata = measurement_data[idx]

            '''
            # Save field data
            np.save(f'{cfg.output_dir}/hz_{safe_name}.npy', 
                    region_data['dHZ'].copy_to_host(mdata['HZ']))
            np.save(f'{cfg.output_dir}/ex_{safe_name}.npy', 
                    region_data['dEX'].copy_to_host(mdata['EX']))
            np.save(f'{cfg.output_dir}/ey_{safe_name}.npy', 
                    region_data['dEY'].copy_to_host(mdata['EY']))
            '''
            
            # Combine real and imaginary into complex arrays
            ex_complex = (region_data['dEX_real'].copy_to_host(mdata['EX_real']) - 
                        j*region_data['dEX_imag'].copy_to_host(mdata['EX_imag']))
            ey_complex = (region_data['dEY_real'].copy_to_host(mdata['EY_real']) - 
                        j*region_data['dEY_imag'].copy_to_host(mdata['EY_imag']))
            hz_complex = (region_data['dHZ_real'].copy_to_host(mdata['HZ_real']) - 
                        j*region_data['dHZ_imag'].copy_to_host(mdata['HZ_imag']))
            
            # Save frequency-domain fields (shape: [num_points])
            np.save(f'{cfg.output_dir}/ex_{safe_name}_fft.npy', ex_complex)
            np.save(f'{cfg.output_dir}/ey_{safe_name}_fft.npy', ey_complex)
            np.save(f'{cfg.output_dir}/hz_{safe_name}_fft.npy', hz_complex)

            # Save metadata for this region
            # Extract start/end from original JSON
            mp_original = cfg.measurement_pts[idx]
            x_start_meters = mp_original['x']
            y_start_meters = mp_original['y']
            x_end_meters = mp_original.get('xend', x_start_meters)
            y_end_meters = mp_original.get('yend', y_start_meters)

            metadata = {
                'name': region_data['name'],
                'type': region_data['type'],
                'num_points': region_data['num_points'],
                'x_start_meters': x_start_meters,
                'y_start_meters': y_start_meters,
                'x_end_meters': x_end_meters,
                'y_end_meters': y_end_meters,
                'shape': {
                    'point': [1, 1],
                    'line': [region_data['num_points'], 1] if x_end_meters!= x_start_meters else [1, region_data['num_points']],
                    'surface': [
                        int(abs(x_end_meters - x_start_meters) / cfg.delta_x) + 1,
                        int(abs(y_end_meters - y_start_meters) / cfg.delta_x) + 1
                    ]
                }[region_data['type']],
                'grid_indices': {
                    'x': mdata['x_indices'].tolist(),
                    'y': mdata['y_indices'].tolist()
                }
            }

            with open(f'{cfg.output_dir}/metadata_{safe_name}.json', 'w') as f:
                json.dump(metadata, f, indent=2)

            print(f"  Saved {region_data['name']} ({region_data['type']}) - {region_data['num_points']} points")

    print(f'results saved in {cfg.output_dir}!')

    cuda.close()
    return 0
