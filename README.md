# SrDesign_PyWave_F2025_S2026
This is a Public repo for the Sr. Design Team, PyWave, during Fall 2025 and Spring 2026.

# Motivation
Modern electronic systems rely on increasingly complex microchips whose performance depends on accurate understanding and modeling of electromagnetic wave propagation. Although commercial electromagnetic simulation tools exist, they are often expensive, restrictive, or insufficiently flexible for specialized research and educational applications. To address these limitations, this Capstone Design team developed an open-source graphical user interface (GUI), released under the GNU GPL v3 license, that enables users to configure, execute, and visualize finite-difference time-domain (FDTD) electromagnetic simulations through an intuitive and customizable environment. This project was completed as part of the University of Idaho CS Senior Capstone Design I (CS 4800, Fall 2025) and CS Senior Capstone Design II (CS 4810, Spring 2026) courses. 

# Acknowledgement
The project was sponsored by Ata Zadehgol of the Department of Electrical and Computer Engineering, who provided the project definition, goals, objectives, and technical guidance in computational electromagnetics and optical interconnects. We also thank Terence Soule of the Department of Computer Science, instructor for the Senior Capstone Design sequence, for his insights on the computer science aspects of the project and for his reviews and feedback throughout the project. This work was supported in part by the National Science Foundation under Award No. 2421919.


# Dev Setup
To get your environment setup for development run the bellow commands.

## Front End
### Assumptions
* You are using a Linux/Windows/MacOS system.
* [Poetry](https://python-poetry.org/docs/) is setup
   * Version 1.8.4 is prefered since that is what our assigned Lab Computer uses,
     but later versions can be used too.
* Python 3.8 is installed on your system

### Instructions
Run the following commands:
``` bash
poetry env use 3.8
poetry install
```

## Backend (FDTD)
### Assumptions
* Using Ubuntu 20.04 or newer
* Python 3.8.10 environment has been setup
* An Nvidia gpu is availabe that can run driver version 470 or newer

### Instructions
#### Cuda Setup
* Install the drivers with the following, then reboot the system.
``` bash
sudo apt isntall gcc-10
sudo apt install nvidia-utils-470
sudo apt install nvidia-driver-470 #or sudo ubuntu-drivers autoinstall
```
* After rebooting install the cuda toolkit with
``` bash
sudo apt install nvidia-cuda-toolkit
```

