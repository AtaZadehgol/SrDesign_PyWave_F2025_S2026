#Factory to create appropriate solver strategy based on simulation type

from initialValues_strategy import (
    IV_Waveguide2DTE_Strategy,
    IV_Waveguide2DTM_Strategy,
    IV_Waveguide3D_Strategy,
    IV_SParameter2DTE_Strategy,
    IV_SParameter2DTM_Strategy,
    IV_SParameter3D_Strategy,
    IV_ScatterLoss2DTE_Strategy,
    IV_ScatterLoss2DTM_Strategy,
    IV_ScatterLoss3D_Strategy
)

import sys
import os

# Get the absolute path of the current file's directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Get the absolute path of the parent directory
parent_dir = os.path.dirname(current_dir)

# Add the parent directory to sys.path
sys.path.append(parent_dir)


class IVFactory:
    #Factory to create initial value strategies based on simulation type and mode
    
    @classmethod
    def create_strategy(cls, simulation_type, polarization_mode, dimension):
 
        #Args:
            #simulation_type: 'Waveguide Propagation', 'Scattering Loss', etc.
            #polarization_mode: 'TE' or 'TM'
        
        #Returns:
            #IVStrategy instance  
            #respective solver() function
        
        # Normalize simulation type (handle variations)
        sim_type_normalized = simulation_type.lower().strip()

        
        if 'waveguide' in sim_type_normalized or 'impedance' in sim_type_normalized:
            if dimension == '2D':
                if polarization_mode == 'TE':
                    from solver.FDTD_2D_TE.wave_impedance.api_2DTE_wave import solver
                    return IV_Waveguide2DTE_Strategy(), solver
                elif polarization_mode == 'TM':
                    from solver.FDTD_2D_TM.wave_impedance.api_2DTM_wave import solver
                    return IV_Waveguide2DTM_Strategy(), solver
                else:
                    raise ValueError(f"Unknown polarization mode: {polarization_mode}")
            if dimension == '3D':
                #TODO: update once this has been accomplished
                def solver():
                    print("uh oh!")
                return IV_Waveguide3D_Strategy(), solver
            else:
                raise ValueError(f"Unknown dimension: {dimension}")
        
        elif 's-parameter' in sim_type_normalized or 'sparameter' in sim_type_normalized:
            print("I'm not ready!")
            if dimension == '2D':
                if polarization_mode == 'TE':
                    from solver.FDTD_2D_TE.sparameter_extraction.api_2DTE_sparameter import solver
                    return IV_SParameter2DTE_Strategy(), solver
                elif polarization_mode == 'TM':
                    from solver.FDTD_2D_TM.sparameter_extraction.api_2DTM_sparameter import solver
                    return IV_SParameter2DTM_Strategy(), solver
                else:
                    raise ValueError(f"Unknown polarization mode: {polarization_mode}")
            if dimension == '3D':
                #TODO: update once this has been accomplished
                def solver():
                    print("uh oh!")
                return IV_SParameter3D_Strategy(), solver
            else:
                raise ValueError(f"Unknown dimension: {dimension}")
        
        elif 'scatter' in sim_type_normalized or 'loss' in sim_type_normalized:
            if dimension == '2D':
                if polarization_mode == 'TE':
                    from solver.FDTD_2D_TE.scattering_loss.api_2DTE_scattering import solver
                    return IV_ScatterLoss2DTE_Strategy(), solver
                elif polarization_mode == 'TM':
                    from solver.FDTD_2D_TM.scattering_loss.api_2DTM_scattering import solver
                    return IV_ScatterLoss2DTM_Strategy(), solver
                else:
                    raise ValueError(f"Unknown polarization mode: {polarization_mode}")
            if dimension == '3D':
                #TODO: update once this has been accomplished
                def solver():
                    print("uh oh!")
                return IV_ScatterLoss3D_Strategy(), solver
            else:
                raise ValueError(f"Unknown dimension: {dimension}")
        
        elif 'custom' in sim_type_normalized:
            # Default to waveguide TE mode for now
	    # TODO: Accomodate TM modes as well. 
            return IV_Waveguide2DTE_Strategy()
        
        else:
            raise ValueError(f"Unknown simulation type: {simulation_type}")
    
    @classmethod
    def get_available_types(cls):
        #Get list of available simulation types
        return [
            'Waveguide Propagation',
            'S-Parameters',
            'Scattering Loss',
            'Custom Experiment'
        ]
