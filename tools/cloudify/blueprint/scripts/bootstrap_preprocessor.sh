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

FILE="coegss_preprocess_submit.sh"

# Create workspace for extra-large output files
# @TODO: maybe it makes sense to replace 'coegss_preprocess' with jobID specific name
WS_PREFIX=`ws_allocate $(basedir ${CURRENT_WORKDIR}) 1 2>/dev/null` #${CURRENT_WORKDIR}

touch ${CURRENT_WORKDIR}/stdout_preprocessor.txt
touch ${CURRENT_WORKDIR}/stderr_preprocessor.txt

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
\${MPIEXEC} -n $6 python $2/preprocesser_piedmont_4_1.py
deactivate
EOM

# Get data
# @TODO: download everything from dataset if requested
# curl https://coegss1.man.poznan.pl/api/search/dataset?q=piedimont
# curl https://coegss1.man.poznan.pl/api/rest/dataset/piedimont-synthetic-population
# wget https://coegss1.man.poznan.pl/dataset/66c7fd31-1fd4-49c9-a1bb-9ed5698765c0/resource/f9c74228-ab35-4ef9-8620-b07407b49b83/download/synthpop_piedimont_10pc_2011.h5.zip \
#     && unzip ./synthpop_piedimont_10pc_2011.h5.zip && rm -rf ./synthpop_piedimont_10pc_2011.h5.zip 2>${CURRENT_WORKDIR}/stderr_preprocessor.txt
# wget https://coegss1.man.poznan.pl/dataset/66c7fd31-1fd4-49c9-a1bb-9ed5698765c0/resource/d6780c78-638d-4240-b8de-ae6c691f88dc/download/resources.zip \
#     && unzip ./resources.zip && rm -rf ./__MACOSX ./resources.zip 2>>${CURRENT_WORKDIR}/stderr_preprocessor.txt

python $2/cloudify_blueprint_0_1/ckan_download_data.py \
       -ip $7 -d $9 -o ${CURRENT_WORKDIR} \
       'Synthetic population' 'Geodata' \
       >>${CURRENT_WORKDIR}/stdout_preprocessor.txt 2>>${CURRENT_WORKDIR}/stderr_preprocessor.txt
