"""
@author: Carla Kolze

Acknowledgement
This project is part of my senior capstone project at the University of Idaho, working with Brian Guiana's code under Professor Ata Zadehgol's request

"""

import numpy as np
import psutil
from time import time
from numba import cuda

from . import fdtd_main_2DTM_scattering
from . import automated_results_collection_2DTM_scattering
from . import analysis_2DTM_scattering

def solver(cg):
    '''
    2DTM scattering calls fdtd_solver and automated_results
    expected outputs: ez_fft_s15nm_lc700nm_r0.npy, hy_fft_s15nm_lc700nm_r0.npy, results_emode.npy
    '''
    res = fdtd_main_2DTM_scattering.solver(cg)
    #visualizer should handle results now - below not needed
    '''
    if (res == 0):
        automated_results_collection_2DTM_scattering.automated_results(cg)
        analysis_2DTM_scattering.analysis(cg)
    else:
        print("main solver didn't complete, can't do following tasks")
    '''