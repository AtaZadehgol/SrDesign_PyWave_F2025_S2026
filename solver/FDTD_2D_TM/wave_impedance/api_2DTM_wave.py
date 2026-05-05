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

#this file used to be run locally but can now only be called as a module.
'''
import fdtd_config as cfg
import fdtd_funcs as funcs
import aux_funcs as aux

from IV_2DTM_wave import InitialValues_2DTM_Wave

from fdtd_main_2DTM_wave import solver
from zwave_2DTM_wave import zwave


cg = InitialValues_2DTM_Wave()
cg.automatedVarInit()
'''

from . import fdtd_main_2DTM_wave
from . import zwave_2DTM_wave

#solver is called in API
def solver(cg):
    '''
    2DTM wave runs fdtd_solver and zwave
    old expected outputs: ez_zwave.npy, ex_zwave.npy, zwave.pdf
    new expected outputs: ez, hx, and hz .npy files for each measurement region
    '''
    fdtd_main_2DTM_wave.solver(cg)
    #zwave_2DTM_wave.analyze_all_results(cg)
