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

from .IV_2DTM_wave import InitialValues_2DTM_Wave

def solver(cfg: InitialValues_2DTM_Wave):
    print('The simulation size will be: {:} x {:} cubic cells over {:} time steps\n\n\n'.format(cfg.nx, cfg.ny, cfg.nt))
    aux.mkdir(cfg.output_dir)
    cuda.select_device(0)

    # =============================================================================
    # Main array definition
    # =============================================================================

    EZ = np.zeros([cfg.nx, cfg.ny], dtype=np.float32)         # Electric field at current time step, z-component
    HX = np.zeros([cfg.nx, cfg.ny], dtype=np.float32)         # Magnetic field at current time step, x-component
    HY = np.zeros([cfg.nx, cfg.ny], dtype=np.float32)         # Magnetic field at current time step, y-component

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

        '''debugging statements'''
        print(f"EPS_REL_MAP shape: {EPS_REL_MAP.shape}")
        print(f"EPS_REL_MAP unique values: {np.unique(EPS_REL_MAP)}")
        print(f"Should see: 1.0 (background) and {12.25/cfg.eps_rel_bg:.3f}, {4.0/cfg.eps_rel_bg:.3f} (rectangles)")

        EPS_MASK = (cfg.eps * EPS_REL_MAP).astype(np.float32)

        #permeability mask
        MU_REL_MAP = funcs.gen_mu_map_from_rectangles(
            cfg.nx, cfg.ny, cfg.rectangles, cfg.delta_x, cfg.mu_rel_bg,
            cfg.bx, cfg.by
        )
        MU_MASK = (cfg.mu * MU_REL_MAP).astype(np.float32)
    
    #otherwise, use legacy for only one waveguide
    else:
        if cfg.rough_toggle:
            FG_REG = funcs.gen_fg_mask_sgl(cfg.nx, cfg.ny, cfg.by, cfg.ny_swg, cfg.p1x, cfg.rstd, cfg.racl, cfg.delta_x, mode='gen', correlation=cfg.ctype, upper_path=cfg.up, lower_path=cfg.lp, atol=cfg.tol_acl, stol=cfg.tol_std, mtol=0.01)
        else:
            FG_REG = funcs.gen_fg_mask_sgl(cfg.nx, cfg.ny, cfg.by, cfg.ny_swg, cfg.p1x, cfg.rstd, cfg.racl, cfg.delta_x, mode='smooth')

        EPS_MASK = cfg.eps * ( cfg.eps_rel_fg * FG_REG + 1 * ~FG_REG )
        EPS_MASK = EPS_MASK.astype(np.float32)

        #new permeability mask
        MU_MASK = np.ones([cfg.nx, cfg.ny], dtype=np.float32) * cfg.mu

    SIGMA_MASK = np.zeros([cfg.nx, cfg.ny], dtype=np.float32)

    # Curl arrays
    #CURL_E = cfg.delta_t / ( cfg.mu * cfg.delta_x )
    #below is all for mu map
    MU_HX = MU_MASK.copy().astype(np.float32)
    MU_HY = MU_MASK.copy().astype(np.float32)

    for j in range(1, cfg.ny):
        for i in range(1, cfg.nx):
            # Hx on vertical edges - average top and bottom
            MU_HX[i, j] = 0.5 * (MU_MASK[i, j] + MU_MASK[i, j-1])
            
            # Hy on horizontal edges - average left and right
            MU_HY[i, j] = 0.5 * (MU_MASK[i, j] + MU_MASK[i-1, j])

    # Now CURL_E depends on position (it's an array, not scalar)
    CURL_E_X = cfg.delta_t / ( MU_HY * cfg.delta_x )  # For Hy update
    CURL_E_Y = cfg.delta_t / ( MU_HX * cfg.delta_x )  # For Hx update

    CURL_E_X = CURL_E_X.astype(np.float32)
    CURL_E_Y = CURL_E_Y.astype(np.float32)

    CURL_H = 2 * cfg.delta_t / ( cfg.delta_x * ( 2 * EPS_MASK + SIGMA_MASK * cfg.delta_t ) )
    MOD_E = ( 2 * EPS_MASK - SIGMA_MASK * cfg.delta_t ) / ( 2 * EPS_MASK + SIGMA_MASK * cfg.delta_t )

    #CURL_E = CURL_E.astype(np.float32)
    CURL_E_X = CURL_E_X.astype(np.float32)
    CURL_E_Y = CURL_E_Y.astype(np.float32)
    CURL_H = CURL_H.astype(np.float32)
    MOD_E = MOD_E.astype(np.float32)

    # Define data storage arrays
    EZT = np.zeros([cfg.nt, cfg.ny], dtype=np.float32)
    HXT = np.zeros([cfg.nt, cfg.ny], dtype=np.float32)

    # NEW: Measurement regions
    if hasattr(cfg, 'measurement_pts') and cfg.measurement_pts:
        measurement_regions = cfg.expand_measurement_points()
        
        if len(measurement_regions) > 0:
            print(f'\n=== Measurement Regions ===')
            print(f'Total regions: {len(measurement_regions)}')
            
            # Create storage for each region
            measurement_data = []
            for region in measurement_regions:
                num_pts = region['num_points']
                region_data = {
                    'name': region['name'],
                    'safe_name': region['safe_name'],
                    'type': region['type'],
                    'EZ': np.zeros([cfg.nt, num_pts], dtype=np.float32),
                    'HX': np.zeros([cfg.nt, num_pts], dtype=np.float32),
                    'HY': np.zeros([cfg.nt, num_pts], dtype=np.float32),
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
    # CPML setup
    # =============================================================================

    # Constants
    m_grade = 4                                                        # Grading maximum exponent for sigma and kappa
    m_alpha = 1                                                        # Grading maximum exponent for alpha
    cpml_sigma_optimal = 0.8*(m_grade+1)/(cfg.eta*cfg.delta_x)         # Optimal sigma value

    cpml_sigma_max = 1.2*cpml_sigma_optimal                            # Maximum sigma value
    cpml_alpha_max = 0.05                                              # Maximum alpha value
    cpml_kappa_max = 5                                                 # Maximum kappa value if CPML is on

    # Define arrays
    PSI_EZ_XLO = np.zeros([cfg.cpml_range, cfg.ny], dtype=np.float32)  # Ez correction field, low-side x-boundary
    PSI_EZ_XHI = np.zeros([cfg.cpml_range, cfg.ny], dtype=np.float32)  # Ez correction field, high-side x-boundary
    PSI_EZ_YLO = np.zeros([cfg.nx, cfg.cpml_range], dtype=np.float32)  # Ez correction field, low-side y-boundary
    PSI_EZ_YHI = np.zeros([cfg.nx, cfg.cpml_range], dtype=np.float32)  # Ez correction field, high-side y-boundary
    PSI_HX_YLO = np.zeros([cfg.nx, cfg.cpml_range], dtype=np.float32)  # Hx correction field, low-side y-boundary
    PSI_HX_YHI = np.zeros([cfg.nx, cfg.cpml_range], dtype=np.float32)  # Hx correction field, high-side y-boundary
    PSI_HY_XLO = np.zeros([cfg.cpml_range, cfg.ny], dtype=np.float32)  # Hy correction field, low-side x-boundary
    PSI_HY_XHI = np.zeros([cfg.cpml_range, cfg.ny], dtype=np.float32)  # Hy correction field, high-side x-boundary

    AE_CPML = np.zeros(cfg.cpml_range, dtype=np.float32)               # Electric field alpha grading
    KE_CPML = np.zeros(cfg.cpml_range, dtype=np.float32)               # Electric field kappa grading
    SE_CPML = np.zeros(cfg.cpml_range, dtype=np.float32)               # Electric field sigma grading

    AH_CPML = np.zeros(cfg.cpml_range, dtype=np.float32)               # Magnetic field alpha grading
    KH_CPML = np.zeros(cfg.cpml_range, dtype=np.float32)               # Magnetic field kappa grading
    SH_CPML = np.zeros(cfg.cpml_range, dtype=np.float32)               # Magnetic field sigma grading

    BE = np.zeros(cfg.cpml_range, dtype=np.float32)                    # Electric field auxiliary variable b
    CE = np.zeros(cfg.cpml_range, dtype=np.float32)                    # Electric field auxiliary variable c
    BH = np.zeros(cfg.cpml_range, dtype=np.float32)                    # Magnetic field auxiliary variable b
    CH = np.zeros(cfg.cpml_range, dtype=np.float32)                    # Magnetic field auxiliary variable c

    DEN_EX = np.ones(cfg.nx, dtype=np.float32)                         # Electric field x-direction kappa division
    DEN_EY = np.ones(cfg.ny, dtype=np.float32)                         # Electric field y-direction kappa division
    DEN_HX = np.ones(cfg.nx, dtype=np.float32)                         # Magnetic field x-direction kappa division
    DEN_HY = np.ones(cfg.ny, dtype=np.float32)                         # Magnetic field y-direction kappa division

    # Assign array values
    for q in range(cfg.num_cpml):
        AE_CPML[q] = cpml_alpha_max * ( q / cfg.num_cpml )**m_alpha
        KE_CPML[q] = 1 + ( cpml_kappa_max - 1 ) * ( ( cfg.cpml_range - q - 1 ) / cfg.num_cpml )**m_grade
        SE_CPML[q] = cpml_sigma_max * ( ( cfg.cpml_range - q - 1 ) / cfg.num_cpml )**m_grade
        BE[q] = np.exp( -1 * ( SE_CPML[q] / KE_CPML[q] + AE_CPML[q] ) * cfg.delta_t / cfg.eps )
        CE[q] = SE_CPML[q] / ( SE_CPML[q] + KE_CPML[q] * AE_CPML[q] ) / KE_CPML[q] * ( BE[q] - 1 )

        AH_CPML[q] = cpml_alpha_max * ( ( q + 0.5 ) / cfg.num_cpml )**m_alpha
        KH_CPML[q] = 1 + ( cpml_kappa_max - 1 ) * ( ( cfg.cpml_range - q - 1.5 ) / cfg.num_cpml )**m_grade
        SH_CPML[q] = cpml_sigma_max * ( ( cfg.cpml_range - q - 1.5 ) / cfg.num_cpml )**m_grade
        BH[q] = np.exp( -1 * ( SH_CPML[q] / KH_CPML[q] + AH_CPML[q] ) * cfg.delta_t / cfg.eps )
        CH[q] = SH_CPML[q] / ( SH_CPML[q] + KH_CPML[q] * AH_CPML[q] ) / KH_CPML[q] * ( BH[q] - 1 )

        DEN_EX[q] = KE_CPML[q]
        DEN_EX[cfg.nx-1-q] = KE_CPML[q]
        DEN_EY[q] = KE_CPML[q]
        DEN_EY[cfg.ny-1-q] = KE_CPML[q]
        DEN_HX[q] = KH_CPML[q]
        DEN_HX[cfg.nx-2-q] = KH_CPML[q]
        DEN_HY[q] = KH_CPML[q]
        DEN_HY[cfg.ny-2-q] = KH_CPML[q]

    # =============================================================================
    # GPU Processing Setup
    # =============================================================================

    # Declare thread sizes
    tpbx = 1
    tpby = 128

    # Declare block sizes
    bpgx = int(np.ceil(cfg.nx/tpbx))
    bpgy = int(np.ceil(cfg.ny/tpby))
    bpgx_pml = int(np.ceil(cfg.cpml_range/tpbx))
    bpgy_pml = int(np.ceil(cfg.cpml_range/tpby))

    # Combine into tuples
    tpb = (tpbx, tpby)
    bpg = (bpgx, bpgy)
    bpg_pmlx = (bpgx_pml, bpgy)
    bpg_pmly = (bpgx, bpgy_pml)

    # GPU Process feedback
    cells_on_device = 5*(cfg.nx*cfg.ny) + 4*(cfg.cpml_range + cfg.cpml_range*cfg.nx + cfg.cpml_range*cfg.ny) + 2*(cfg.nx + cfg.ny + cfg.nt*cfg.ny)
    device_req_mem = 4*cells_on_device / 1024 / 1024
    print('Transferring {:.0f} Mcells onto GPU, requiring {:} MB'.format(cells_on_device/1e6, device_req_mem))

    # Device arrays of size (nx*ny)
    dEZ = cuda.to_device(EZ)
    dHX = cuda.to_device(HX)
    dHY = cuda.to_device(HY)
    dMOD_E = cuda.to_device(MOD_E)
    dCURL_H = cuda.to_device(CURL_H)

    # NEW: Add permeability arrays
    dCURL_E_X = cuda.to_device(CURL_E_X)
    dCURL_E_Y = cuda.to_device(CURL_E_Y)

    # Device arrays of size (cpml_range)
    dBE = cuda.to_device(BE)
    dCE = cuda.to_device(CE)
    dBH = cuda.to_device(BH)
    dCH = cuda.to_device(CH)

    # Device arrays of size (nx)
    dDEN_EX = cuda.to_device(DEN_EX)
    dDEN_HX = cuda.to_device(DEN_HX)

    # Device arrays of size (ny)
    dDEN_EY = cuda.to_device(DEN_EY)
    dDEN_HY = cuda.to_device(DEN_HY)

    # Device arrays of size (cpml_range*nx)
    dPSI_EZ_YLO = cuda.to_device(PSI_EZ_YLO)
    dPSI_EZ_YHI = cuda.to_device(PSI_EZ_YHI)
    dPSI_HX_YLO = cuda.to_device(PSI_HX_YLO)
    dPSI_HX_YHI = cuda.to_device(PSI_HX_YHI)

    # Device arrays of size (cpml_range*ny)
    dPSI_EZ_XLO = cuda.to_device(PSI_EZ_XLO)
    dPSI_EZ_XHI = cuda.to_device(PSI_EZ_XHI)
    dPSI_HY_XLO = cuda.to_device(PSI_HY_XLO)
    dPSI_HY_XHI = cuda.to_device(PSI_HY_XHI)

    # Device arrays of size (nt*ny)
    dEZT = cuda.to_device(EZT)
    dHXT = cuda.to_device(HXT)

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
                'waveform': device_waveforms[wf_idx],   #CPU array! sticking with Brian's method here
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
            
            device_region = {
                'name': mdata['name'],
                'safe_name': mdata['safe_name'],
                'type': mdata['type'],
                'num_points': region['num_points'],
                'dEZ': cuda.to_device(mdata['EZ']),
                'dHX': cuda.to_device(mdata['HX']),
                'dHY': cuda.to_device(mdata['HY']),
                'dx_indices': cuda.to_device(mdata['x_indices']),
                'dy_indices': cuda.to_device(mdata['y_indices'])
            }
            device_measurement_data.append(device_region)
            
            # Setup grid for this region
            bpg_region = int(np.ceil(region['num_points'] / tpby))
            device_region['bpg'] = bpg_region
            
            print(f"  {region['name']} ({region['type']}): {region['num_points']} points, bpg={bpg_region}")
        
        print('===========================\n')
    else:
        device_measurement_data = None

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
        # Update E-field component
        funcs.update_ez[bpg, tpb](dEZ, dHX, dHY, dMOD_E, dCURL_H, dDEN_EX, dDEN_EY, cfg.nx, cfg.ny)

        # Update source condition
        if source_positions is not None:
            # Multi-source mode: inject at each source point
            for src_pos in source_positions:
                src_value = src_pos['waveform'][n]  # Scalar at this timestep
                funcs.update_source[bpg, tpb](dEZ, src_value,
                                            src_pos['x'], src_pos['x']+1,
                                            src_pos['y']-1, src_pos['y']+2)
        else:
            # Legacy single-source mode
            funcs.update_source[bpg, tpb](dEZ, cfg.J_SRC[n], cfg.sx, cfg.sx+1, cfg.by, cfg.ny-cfg.by)

        # Update E-field component in PML
        funcs.update_ez_cpml_x[bpg_pmlx, tpb](dPSI_EZ_XLO, dPSI_EZ_XHI, dEZ, dHX, dHY, dCURL_H, dBE, dCE, cfg.delta_x, cfg.delta_t, cfg.eps, cfg.nx, cfg.ny, cfg.cpml_range)
        funcs.update_ez_cpml_y[bpg_pmly, tpb](dPSI_EZ_YLO, dPSI_EZ_YHI, dEZ, dHX, dHY, dCURL_H, dBE, dCE, cfg.delta_x, cfg.delta_t, cfg.eps, cfg.nx, cfg.ny, cfg.cpml_range)

        # Update H-field components
        #funcs.update_hx_hy[bpg, tpb](dHX, dHY, dEZ, CURL_E, dDEN_HX, dDEN_HY, cfg.nx, cfg.ny)
        funcs.update_hx_hy[bpg, tpb](dHX, dHY, dEZ, dCURL_E_X, dCURL_E_Y, dDEN_HX, dDEN_HY, cfg.nx, cfg.ny) #new

        # Update H-field components in PML
        funcs.update_hy_cpml_x[bpg_pmlx, tpb](dPSI_HY_XLO, dPSI_HY_XHI, dHY, dEZ, dBH, dCH, cfg.delta_x, cfg.delta_t, cfg.mu, cfg.nx, cfg.ny, cfg.cpml_range)
        funcs.update_hx_cpml_y[bpg_pmly, tpb](dPSI_HX_YLO, dPSI_HX_YHI, dHX, dEZ, dBH, dCH, cfg.delta_x, cfg.delta_t, cfg.mu, cfg.nx, cfg.ny, cfg.cpml_range)

        # Record Data
        funcs.map_efield_zwave[bpgy, tpby](dEZT, dEZ, n, cfg.cx, cfg.ny)
        funcs.map_hfield_zwave[bpgy, tpby](dHXT, dHX, n, cfg.cx, cfg.ny)

        # NEW: Record at measurement regions
        if device_measurement_data is not None:
            for region_data in device_measurement_data:
                funcs.record_measurement_points[region_data['bpg'], tpby](
                    region_data['dEZ'], dEZ, region_data['dx_indices'], 
                    region_data['dy_indices'], n, region_data['num_points']
                )
                funcs.record_measurement_points[region_data['bpg'], tpby](
                    region_data['dHX'], dHX, region_data['dx_indices'], 
                    region_data['dy_indices'], n, region_data['num_points']
                )
                funcs.record_measurement_points[region_data['bpg'], tpby](
                    region_data['dHY'], dHY, region_data['dx_indices'], 
                    region_data['dy_indices'], n, region_data['num_points']
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

    print('saving results')
    np.save('{}/ez_zwave'.format(cfg.output_dir), dEZT.copy_to_host(EZT))
    np.save('{}/hx_zwave'.format(cfg.output_dir), dHXT.copy_to_host(HXT))

    # NEW: Save measurement region data
    if device_measurement_data is not None:
        import json
        
        for idx, region_data in enumerate(device_measurement_data):
            safe_name = region_data['safe_name']
            mdata = measurement_data[idx]
            region_info = measurement_regions[idx]
            
            # Save field data
            np.save(f'{cfg.output_dir}/ez_{safe_name}.npy', 
                    region_data['dEZ'].copy_to_host(mdata['EZ']))
            np.save(f'{cfg.output_dir}/hx_{safe_name}.npy', 
                    region_data['dHX'].copy_to_host(mdata['HX']))
            np.save(f'{cfg.output_dir}/hy_{safe_name}.npy', 
                    region_data['dHY'].copy_to_host(mdata['HY']))
            
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
