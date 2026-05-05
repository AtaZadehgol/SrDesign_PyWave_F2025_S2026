"""
@author: Carla Kolze

Acknowledgement
This project is part of my senior capstone project at the University of Idaho, working with Brian Guiana's code under Professor Ata Zadehgol's request
"""
import sys
import os
# Get the absolute path of the current file's directory
current_dir = os.path.dirname(os.path.abspath(__file__))
# Get the absolute path of the parent directory
parent_dir = os.path.dirname(current_dir)
# Add the parent directory to sys.path
sys.path.append(parent_dir)

from solver.FDTD_2D_TE.wave_impedance.IV_2DTE_wave import InitialValues_2DTE_Wave

from solver.FDTD_2D_TE.wave_impedance.fdtd_main_2DTE_wave import solver

cg = InitialValues_2DTE_Wave()
#cg.default_2D_TE_wave()
cg.automatedVarInit()
solver(cg)