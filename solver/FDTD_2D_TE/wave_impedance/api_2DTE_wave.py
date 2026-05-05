"""
@author: Carla Kolze

Acknowledgement
This project is part of my senior capstone project at the University of Idaho, working with Brian Guiana's code under Professor Ata Zadehgol's request
"""


#this file no longer works simply locally due to the python module stuff.

'''
that is, now that I am exporting these files as python packages so I can call them in the API directory,
you can't import the files as normal from this local directory.

and you can't run these files without calling them either!
'''

import numpy as np
#import os
import psutil
from time import time
from numba import cuda

#from IV_2DTE_wave import InitialValues_2DTE_Wave
#from fdtd_main_2DTE_wave import solver

from . import fdtd_main_2DTE_wave
from . import zwave_2DTE_wave

#cg = IV_2DTE_wave.InitialValues_2DTE_Wave()
#cg.default_2D_TE_wave()
#cg.automatedVarInit()

#solver is what gets called in the API
def solver(cg):
    '''
    2DTE waveguide runs fdtd_solver.
    old expected output files: ex_zwave.npy, hz_zwave.npy, and zwave.pdf
    new expected output files: ex, ey, and hz .npy files for each measurement region
    '''
    fdtd_main_2DTE_wave.solver(cg)
    #zwave_2DTE_wave.zwave(cg)          #will create pdfs of all measurement regions. not necessary given the visualizer should do this
    #zwave_2DTE_wave.zwave_analysis(cg) #can out region name in as second argument