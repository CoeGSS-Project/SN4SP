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

# Input parameters:
#   $1 - half-similarity scale
#   $2 - damping Function
#   $3 - percentage of the sample for the similarity calculation
#   $4 - number of MPI processes
#   $5 - Python virtual environment
#   $6 - repository with CoeGSS tools
#   $7 - CKAN entrypoint
#   $8 - CKAN API key
#   $9 - CKAN input dataset
#  $10 - CKAN output dataset

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

. $5/bin/activate
\${MPIEXEC} -n $4 python $6/simnet4synpop.py ${CURRENT_WORKDIR}/synthetic_population_ppd.h5 -o ${WS_PREFIX:-${CURRENT_WORKDIR}}/synthetic_network.h5 -hss $1 -d $2 -p $3
deactivate
EOM
