"""
@author: Carla Kolze

Acknowledgement
This project was completed as part of research conducted with my major professor and advisor, Prof. Ata Zadehgol, as part of the Applied and Computational Electromagnetics Signal and Power Integrity (ACEM-SPI) Lab while working toward the Ph.D. in Electrical Engineering at the University of Idaho, Moscow, Idaho, USA. This project was funded, in part, by the National Science Foundation (NSF); award #1816542 [1].

"""
# this file must be called from API

import numpy as np
import psutil
from time import time
from numba import cuda

from . import fdtd_main_2DTE_scattering
from . import automated_results_collection_2DTE_scattering
from . import analysis_2DTE_scattering

def solver(cg):
    '''
    2DTE scattering loss runs fdtd_solver, automated_results, and analysis
    expected output files: ey_fft_s15nm_lc700nm_r0.npy, hz_fft_s15nm_lc700nm_r0.npy, results_hmode.npy
    analysis prints stuff
    '''
    res = fdtd_main_2DTE_scattering.solver(cg)
    #TODO: remove below since visualizer should completely handle results?
    '''
    if (res == 0):
        automated_results_collection_2DTE_scattering.automated_results(cg)
        analysis_2DTE_scattering.analysis(cg)
    else:
        print("main solver didn't complete, can't do following tasks")
    '''