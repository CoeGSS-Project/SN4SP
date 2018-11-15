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

# Go to the work directory
cd ${CURRENT_WORKDIR}

# # Skip first 8 arguments required for job bootstrapping
# shift;shift;shift;shift;shift;shift;shift;shift

FILE="coegss_network_sampler_submit.sh"

if [ -f $FILE ]; then
    rm $FILE
fi

# TODO: move ERR/OUT concatenation to script
ERR_FILE=`find . -name "*.err" | head -n 1`
[[ ! -z "${ERR_FILE}" ]] && cat ${ERR_FILE} >> ./stderr_sampler.txt

OUT_FILE=`find . -name "*.out" | head -n 1`
[[ ! -z "${OUT_FILE}" ]] && cat ${OUT_FILE} >> ./stdout_sampler.txt

# @TODO: use workspace
SYNNET_FILE=`find . -name "Synthetic network_hss*h5" | head -n 1`

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
	    \"description\" : \"Synthetic network with hss=$3 and dump=$4 produced by job $(basename ${CURRENT_WORKDIR})\"
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
	    \"description\" : \"Synthetic network with hss=$3 and dump=$4 produced by job $(basename ${CURRENT_WORKDIR})\"
	}
    ]
]""" | python $2/tools/cloudify/ckan_upload_data.py \
       -ip "$7" -k "$8" -d "$9-output" 2> xyz2.err

# # Clean up data
# rm -rf ./'Synthetic population_ppd.h5' $FILE \
#    ${CURRENT_WORKDIR}/stderr_sampler.txt  ${CURRENT_WORKDIR}/stdout_sampler.txt ${ERR_FILE} ${OUT_FILE}

# Release workspaces created by bootstrap
# TODO: test with ws_find
# NOTE: this code produces error if workspace is already released
[[ ! -z "`which ws_allocate 2>/dev/null`" ]] && ws_release $(basename ${CURRENT_WORKDIR}) #${CURRENT_WORKDIR}

echo ""
