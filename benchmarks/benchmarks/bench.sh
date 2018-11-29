#!/bin/bash

############################################################
#    Copyright (C) 2018 by
#    Sergiy Gogolenko <gogolenko@hlrs.de>   HLRS
#    Fabio Saracco    <fabio@imt.it>        IMT
#    All rights reserved.
#
# Authors:      Sergiy Gogolenko <gogolenko@hlrs.de>
############################################################
# qsub   -l nodes=1,walltime=1:30:00
# sbatch --ntasks=24 --time==1:30:00

# Dafault input
IN_FILES=${2:-{"synthetic_population_ppd.h5",}}
PROCESSES=${1:-"2 4 6 8 12 16 24 32 48"}
OUT_WORKSPACE=sn4sp-bench-${PBS_JOBID}

ws_allocate ${OUT_WORKSPACE} 2>/dev/null
OUT_FOLDER=`ws_find ${OUT_WORKSPACE} 2>/dev/null`
OUT_FOLDER=${OUT_FOLDER:-.}

SRUN=`which srun 2>/dev/null`
APRUN=`which aprun 2>/dev/null`
MPIEXEC=${APRUN:-${SRUN:-mpiexec}}

cd $PBS_O_WORKDIR
export HDF5_USE_FILE_LOCKING=FALSE

. ~/opt/pyenv/hazelhen/coegss/2.7/bin/activate

for IN_FILE in ${IN_FILES}
do
    for i in ${PROCESSES}
    do
        RESULTS_FILE=${OUT_FOLDER}/${IN_FILE}${i}.csv
	${MPIEXEC} -n $i python ./benchmarks.py  -o ${OUT_FOLDER} -hss 5000 -d 0 -p 0.01 > ${RESULTS_FILE}
    done
done

deactivate

ws_release ${OUT_WORKSPACE} 
