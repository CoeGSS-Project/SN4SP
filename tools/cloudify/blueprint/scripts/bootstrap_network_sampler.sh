#!/bin/bash -l

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
## Bootstrapping for network reconstruction execution
############################################################

FILE="coegss_network_sampler_submit.sh"

# Create workspace for extra-large output files
WS_PREFIX=`ws_allocate $(basedir ${CURRENT_WORKDIR}) 1 2>/dev/null` #${CURRENT_WORKDIR}

touch ${CURRENT_WORKDIR}/stdout_sampler.txt
touch ${CURRENT_WORKDIR}/stderr_sampler.txt

# Create script for putting in HPC cluster queue
cat > $FILE <<- EOM
#!/bin/bash -l

# SBATCH -p fast
# PBS -q test

cd ${CURRENT_WORKDIR}

# Workaround to get a correct MPI executable name
# Test all popular options: aprun/srun/mpiexec and select available
module load mpi 2>/dev/null
SRUN=\`which srun 2>/dev/null\`
APRUN=\`which aprun 2>/dev/null\`
MPIEXEC=\${APRUN:-\${SRUN:-mpiexec}}

# Launch script in virtual environment
module load python/2.7.14
module load hdf5/1.10.1_openmpi-2.1.2_gcc620

. $1/bin/activate
\${MPIEXEC} -n $6 python $2/SiNe4SyPo_piedmont.py ${CURRENT_WORKDIR}/synthetic_population_ppd.h5 -o ${WS_PREFIX:-${CURRENT_WORKDIR}}/synthetic_network.h5 -hss $3 -d $4 -p $5
deactivate
EOM
