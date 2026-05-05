"""
@author: Carla Kolze

Acknowledgement
This project is part of my senior capstone project at the University of Idaho, working with Brian Guiana's code under Professor Ata Zadehgol's request
"""

import os
from time import sleep
from subprocess import run

import fdtd_funcs as funcs
import aux_funcs as aux

from IV_2DTE_sparameter import InitialValues_2DTE_SParameter

from fdtd_main_2DTE_sparameter import solver
from extract_sparams_2DTE_sparameters import extract_sparams

cg = InitialValues_2DTE_SParameter()
cg.automatedVarInit()

if cg.sim_type == 's-param':
    print('launching S-paramter Extraction Simulation')
    print('Simulating {} coupled lines ({} sims total)'.format(cg.num_lines, cg.num_lines*4))

    for line in range(cg.num_lines):
        print('Evaluating line {}'.format(line+1))
        solver(cg, line, 'f', 'i')
        sleep(5)
        solver(cg, line, 'f', 'r')
        sleep(5)
        solver(cg, line, 'b', 'i')
        sleep(5)
        solver(cg, line, 'b', 'r')
        sleep(5)

    print('\n\n\nEvaluating S-Parameters')
    extract_sparams(cg)
    print('Done extracting S-parameters! The touchstone file is in {}'.format(cg.output_dir))
    print('\n\n\n')
    print('To continue with equivalent circuit synthesis and passivity enforcement:')
    print('1. Copy {}.s{}p from the folder ./{} to the folder SROPEE/Input'.format(cg.sparam_file, cg.num_lines*2, cg.output_dir))
    print('2. Follow the directions in SROPEE/Instructions.pdf for further instructions on continuing with equivalent circuit synthesis and passivity enforcement')
    file = open('./{}/NEXT_STEPS_INSTRUCTIONS.txt'.format(cg.output_dir), mode='w')
    file_lines = ['To continue with equivalent circuit synthesis and passivity enforcement:\n1. Copy {}.s{}p from the folder ./{} to the folder SROPEE/Input\n2. Follow the directions in SROPEE/Instructions.pdf for further instructions on continuing with equivalent circuit synthesis and passivity enforcement'.format(cg.sparam_file, cg.num_lines*2, cg.output_dir)]
    file.writelines(file_lines)
    file.close()

else:
    print('Test Environment')