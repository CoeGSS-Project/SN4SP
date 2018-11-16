#!/bin/bash
#PBS -N network_reconstruction
#PBS -l nodes=2:ppn=24
#PBS -l walltime=12:00:00

############################################################
## @file
## @copyright (C) 2018
##    High Performance Computing Center Stuttgart (HLRS)
##    http://www.hlrs.de
##    All rights reserved.
##
## Use, modification, and distribution is subject to the HLRS License.
##
## @author Sergiy Gogolenko <gogolenko@hlrs.de>
##
## Run network reconstruction scripts on Cray systems
############################################################

# ws_allocate network_reconstruction 1

cd $PBS_O_WORKDIR

export HDF5_USE_FILE_LOCKING=FALSE

. ~/opt/pyenv/hazelhen/coegss/2.7/bin/activate \
    && aprun -n 48 -N 24 python ../../SiNe4SyPo_piedmont.py -o `ws_find network_reconstruction` -hss 5000 -d 0 -p 0.01 \
    && deactivate

# ls `ws_find network_reconstruction`
# ws_list -a
# ws_release network_reconstruction
