"""
@author: Carla Kolze

Acknowledgement
This project is part of my senior capstone project at the University of Idaho, working with Brian Guiana's code under Professor Ata Zadehgol's request
"""

import numpy as np
import matplotlib.pyplot as plt
import pickle
import sys
import fdtd_auto_setup as cfg
#import user_config as usr
from scipy import fft
import skrf as rf
import aux_funcs as aux

from IV_2DTE_sparameter import InitialValues_2DTE_SParameter

def extract_sparams(cfg: InitialValues_2DTE_SParameter):
    if cfg.precision == np.float32:
        cprec = np.complex64
    elif cfg.precision == np.float64:
        cprec = np.complex128

    num_ports = 2 * cfg.num_lines

    S_mat = np.zeros([cfg.sparam_num_freqs, num_ports, num_ports], dtype=cprec)

    for i in range(num_ports):
        for j in range(i, num_ports):
            iline = i//2 + 1
            jline = j//2 + 1
            if j % 2 == 0:
                ey_inc = np.load('{}/ey_fi_l{}.npy'.format(cfg.output_dir, jline))
                hz_inc = np.load('{}/hz_fi_l{}.npy'.format(cfg.output_dir, jline))
            elif j % 2 == 1:
                ey_inc = np.load('{}/ey_bi_l{}.npy'.format(cfg.output_dir, jline))
                hz_inc = np.load('{}/hz_bi_l{}.npy'.format(cfg.output_dir, jline))

            if i % 2 == j % 2:
                if i % 2 == 0:
                    ey_ref = np.load('{}/ey_ft_l{}.npy'.format(cfg.output_dir, jline))
                    hz_ref = np.load('{}/hz_ft_l{}.npy'.format(cfg.output_dir, jline))
                elif i % 2 == 1:
                    ey_ref = np.load('{}/ey_bt_l{}.npy'.format(cfg.output_dir, jline))
                    hz_ref = np.load('{}/hz_bt_l{}.npy'.format(cfg.output_dir, jline))
            elif i % 2 != j % 2:
                if i % 2 == 0:
                    ey_ref = np.load('{}/ey_fr_l{}.npy'.format(cfg.output_dir, jline))
                    hz_ref = np.load('{}/hz_fr_l{}.npy'.format(cfg.output_dir, jline))
                elif i % 2 == 1:
                    ey_ref = np.load('{}/ey_br_l{}.npy'.format(cfg.output_dir, jline))
                    hz_ref = np.load('{}/hz_br_l{}.npy'.format(cfg.output_dir, jline))

            if i == j:
                if i % 2 == 0:
                    ey_inc_cor = np.load('{}/ey_fi_l{}.npy'.format(cfg.output_dir, iline))
                    hz_inc_cor = np.load('{}/hz_fi_l{}.npy'.format(cfg.output_dir, iline))
                elif i % 2 == 1:
                    ey_inc_cor = np.load('{}/ey_bi_l{}.npy'.format(cfg.output_dir, iline))
                    hz_inc_cor = np.load('{}/hz_bi_l{}.npy'.format(cfg.output_dir, iline))
                ey_ref -= ey_inc_cor
                hz_ref -= hz_inc_cor

            sav_inc = 0.5*(ey_inc * np.conjugate(hz_inc))
            sav_ref = 0.5*(ey_ref * np.conjugate(hz_ref))
            start_inc = cfg.by+cfg.cy_swg-cfg.ph + cfg.pp*(jline-1)
            end_inc = start_inc + cfg.pp
            start_ref = cfg.by+cfg.cy_swg-cfg.ph + cfg.pp*(iline-1)
            end_ref = start_ref + cfg.pp

            Pinc = np.zeros(cfg.sparam_num_freqs, dtype=cprec)
            Pref = np.zeros(cfg.sparam_num_freqs, dtype=cprec)

            for p in range(start_inc, end_inc):
                Pinc += sav_inc[:, p]
            for p in range(start_ref, end_ref):
                Pref += sav_ref[:, p]

            S_mat[:, i, j] = np.sqrt(Pref / Pinc)
            S_mat[:, j, i] = np.sqrt(Pref / Pinc)

    freq = rf.Frequency.from_f(cfg.sparam_freqs, unit='Hz')
    net = rf.Network(frequency=freq, s=S_mat, z0=50, name='Interconnects')

    net.write_touchstone(cfg.sparam_file, cfg.output_dir, write_z0=True, skrf_comment=True, form='ri')
    file = open('{}/{}.s{}p'.format(cfg.output_dir, cfg.sparam_file, num_ports), mode='r')
    file_lines = file.readlines()
    file_ack = '!This S-parameter file was generated as part of the OIDT. This project was completed as part of research conducted with my major professor and advisor, Prof. Ata Zadehgol, at the Applied and Computational Electromagnetics Signal and Power Integrity (ACEM-SPI) Lab while working toward the Ph.D. in Electrical Engineering at the University of Idaho, Moscow, Idaho, USA. This project was funded, in part, by the National Science Foundation (NSF); award #1816542 [1].\n'
    file_lines.insert(0, file_ack)

    file = open('{}/{}.s{}p'.format(cfg.output_dir, cfg.sparam_file, num_ports), mode='w')
    file.writelines(file_lines)
    file.close()

    print('Saving S-parmeter dB plot')
    plt.figure()
    net.plot_s_db()
    plt.savefig('{}/{}_db_plot.pdf'.format(cfg.output_dir, cfg.sparam_file))
    print('Saving S-parameter angle (degrees) plot')
    plt.figure()
    net.plot_s_deg()
    plt.savefig('{}/{}_angle_plot.pdf'.format(cfg.output_dir, cfg.sparam_file))
    plt.close()
