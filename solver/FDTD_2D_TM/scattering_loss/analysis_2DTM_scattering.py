"""
@author: Carla Kolze

Acknowledgement
This project is part of my senior capstone project at the University of Idaho, working with Brian Guiana's code under Professor Ata Zadehgol's request

"""

import numpy as np
from . import aux_funcs as aux

from .IV_2DTM_scattering import InitialValues_2DTM_Scattering

def grab_sim_results(A, sig, lc):
    B = np.zeros(A.shape[0])
    for n in range(A.shape[1]):
        if A[0, n] == sig and A[1, n] == lc:
            B = np.vstack([B, A[:, n]])
    return B.T[:, 1:]


def grab_some_results(A, sig, lc, length, res, max_results):
    B = np.zeros(A.shape[0])
    i = 0
    for n in range(A.shape[1]):
        if A[0, n] == sig and A[1, n] == lc and A[2, n] == length and A[3, n] == res and i < max_results:
            B = np.vstack([B, A[:, n]])
            i += 1
    return B.T[:, 1:]


def find_alpha(sigma, Lc, f0):
    n1 = 3.5
    n2 = 1.5
    d = 100e-9
    k0 = 2 * np.pi * f0 / 3e8

    neff = aux.find_neff(n1, n2, d, k0, mode='te')
    beta = neff * k0
    kappa = np.sqrt( ( n1 * k0 )**2 - beta**2 )
    gamma = np.sqrt( beta**2 - ( n2 * k0 )**2 )

    phi = np.cos( kappa * d )
    MW = ( n1**2 - n2**2 )**2 * k0**3 / ( 4 * np.pi * n2 )

    theta = np.linspace(0, np.pi, num=3142)
    k = beta - n2 * k0 * np.cos( theta )
    RXX = 2 * Lc * sigma**2 / ( 1 + Lc**2 * k**2 )
    SW = 0
    for t in range(len(theta)):
        SW += RXX[t] * theta[1]

    Prad = phi**2 * MW * SW
    Pg = ( d + 1 / gamma )
    alpha_base = Prad / Pg
    return n2/n1*alpha_base, n2/neff*alpha_base

def analysis(cfg: InitialValues_2DTM_Scattering):
    fdtd = np.load('results_emode.npy')
    sigma_corners = [15]
    lc_corners = [700]

    for kind in range(2):
        if kind == 0:
            print('Core Impedance Style')
        if kind == 1:
            print('Effective Impedance Style')
        for s in sigma_corners:
            print('sigma = {:} nm'.format(s))
            sigma_offsets = np.array([])
            overall_errors = np.array([])
            for l in lc_corners:
                this_set = grab_sim_results(fdtd, s, l)
                set_alpha = this_set[4]
                set_dbcm = set_alpha * 8.686/100
                set_sigma = np.mean(this_set[2])
                f0 = cfg.f0
                analytic = find_alpha(s*1e-9, l*1e-9, f0)[kind]
                error = 100 * (analytic - np.mean(set_alpha))/analytic
                sigma_offsets = np.append(sigma_offsets, analytic/np.mean(set_alpha))
                overall_errors = np.append(overall_errors, error)
                print('Lc: {:} nm,\t samples: {:},\tset sd: {:.0f},\tset mean: {:.0f},\t set BW: +/-{:.3f}%,\terror: {:.2f}%'.format(l, this_set.shape[1], np.std(set_alpha), np.mean(set_alpha), 100*np.std(set_alpha)/np.mean(set_alpha), error))
            print('Error mean across LCs for this sigma is:\t{:.3f}'.format(np.mean(overall_errors)))
            print('Error dev. across LCs for this sigma is:\t{:.3f}\n\n'.format(np.std(overall_errors)))
