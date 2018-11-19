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
## Cleaning up for network reconstruction execution
############################################################

# Store similarity network parameters
SN4SP_SAMPLING_PARAMS="half-similarity scale: $1, dumping: $2, sampling fraction: $3"

# Skip first 4 arguments required for job bootstrapping ONLY
# Remaining arguments:
#   $1 - Python virtual environment
#   $2 - repository with CoeGSS tools
#   $3 - CKAN entrypoint
#   $4 - CKAN API key
#   $5 - CKAN dataset with input files
#   $6 - CKAN dataset with output files
shift;shift;shift;shift

# Go to the work directory
cd ${CURRENT_WORKDIR}

SBATCH_FILE="coegss_network_sampler_submit.sh"
WS_PREFIX=`ws_find $(basedir ${CURRENT_WORKDIR}) 2>/dev/null`

rm -rf ${SBATCH_FILE}

# TODO: move ERR/OUT concatenation to script
ERR_FILE=`find . -name "*.err" | head -n 1`
[[ ! -z "${ERR_FILE}" ]] && cat ${ERR_FILE} >> ./stderr_sampler.txt

OUT_FILE=`find . -name "*.out" | head -n 1`
[[ ! -z "${OUT_FILE}" ]] && cat ${OUT_FILE} >> ./stdout_sampler.txt

SYNNET_FILE=${WS_PREFIX:-${CURRENT_WORKDIR}}/synthetic_network.h5

# TODO: remove debugging
echo """[
    [
        \"stderr_sampler.txt\",
	{
	    \"name\" : \"Sampler job error file\",
	    \"description\" : \"Error file for network sampling job $(basename ${CURRENT_WORKDIR})\"
	}
    ],
    [
        \"stdout_sampler.txt\",
	{
	    \"name\" : \"Sampler job output file\",
	    \"description\" : \"Console output for network sampling job $(basename ${CURRENT_WORKDIR})\"
	}
    ],
    [
        \"${SYNNET_FILE}\",
	{
	    \"name\" : \"Synthetic network\",
	    \"description\" : \"Synthetic network (${SN4SP_SAMPLING_PARAMS}) produced by job $(basename ${CURRENT_WORKDIR})\"
	}
    ]
]""" >> ./stdout_sampler.txt

# Upload results to CKAN
echo """[
    [
        \"stderr_sampler.txt\",
	{
	    \"name\" : \"Sampler job error file\",
	    \"description\" : \"Error file for network sampling job $(basename ${CURRENT_WORKDIR})\"
	}
    ],
    [
        \"stdout_sampler.txt\",
	{
	    \"name\" : \"Sampler job output file\",
	    \"description\" : \"Console output for network sampling job $(basename ${CURRENT_WORKDIR})\"
	}
    ],
    [
        \"${SYNNET_FILE}\",
	{
	    \"name\" : \"Synthetic network\",
	    \"description\" : \"Synthetic network (${SN4SP_SAMPLING_PARAMS}) produced by job $(basename ${CURRENT_WORKDIR})\"
	}
    ]
]""" | python $2/tools/cloudify/ckan_upload_data.py \
       -ip "$3" -k "$4" -d "$6" 2> xyz2.err

# # Clean up data
# rm -rf ./synthetic_population_ppd.h5 $FILE \
#    ${CURRENT_WORKDIR}/stderr_sampler.txt  ${CURRENT_WORKDIR}/stdout_sampler.txt ${ERR_FILE} ${OUT_FILE}

# Release workspaces created by bootstrap
# TODO: test with ws_find
# NOTE: this code produces error if workspace is already released
[[ ! -z "`which ws_allocate 2>/dev/null`" ]] && ws_release $(basename ${CURRENT_WORKDIR}) #${CURRENT_WORKDIR}
echo '' # avoid error status if workspace was already released
