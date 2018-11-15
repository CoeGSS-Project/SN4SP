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

FILE="coegss_preprocess_submit.sh"

if [ -f $FILE ]; then
    rm $FILE
fi

# TODO: move ERR/OUT concatenation to script
ERR_FILE=`find . -name "*.err" | head -n 1`
[[ ! -z "${ERR_FILE}" ]] && cat ${ERR_FILE} >> ./stderr_preprocessor.txt

OUT_FILE=`find . -name "*.out" | head -n 1`
[[ ! -z "${OUT_FILE}" ]] && cat ${OUT_FILE} >> ./stdout_preprocessor.txt

# Upload results to CKAN
echo """[
    [
        \"stderr_preprocessor.txt\",
	{
	    \"name\" : \"Preprocessing job error file\",
	    \"description\" : \"Error file for preprocessing job $(basename ${CURRENT_WORKDIR})\"
	}
    ],
    [
        \"stdout_preprocessor.txt\",
	{
	    \"name\" : \"Preprocessing job output file\",
	    \"description\" : \"Console output for preprocessing job $(basename ${CURRENT_WORKDIR})\"
	}
    ],
    [
        \"Synthetic population_ppd.h5\",
	{
	    \"name\" : \"Spatially distributed synthetic population\",
	    \"description\" : \"Spatially distributed synthetic population produced by job $(basename ${CURRENT_WORKDIR})\"
	}
    ]
]""" | python $2/cloudify_blueprint_0_1/ckan_upload_data.py \
       -ip "$7" -k "$8" -d "$9-output" 2> xyz0.err

# Upload stderr and stdout files
# curl -H"Authorization: $2" $1/api/action/resource_create \
#      --form upload=@./stderr_preprocessor.txt \
#      --form package_id=$3 \
#      --form name=stderr_preprocessor.txt \
#      --form description='Standard error file'

# curl -H"Authorization: $2" $1/api/action/resource_create \
#      --form upload=@./stdout_preprocessor.txt \
#      --form package_id=$3 \
#      --form name=stdout_preprocessor.txt \
#      --form description='Standard output file'

# # Clean up data
# rm -rf ./'Synthetic population.h5' ./'Synthetic population_ppd.h5' ./'Geodata.gz' \
#    $FILE ${CURRENT_WORKDIR}/stderr_preprocessor.txt  ${CURRENT_WORKDIR}/stdout_preprocessor.txt ${ERR_FILE} ${OUT_FILE}

# Release workspaces created by bootstrap
# TODO: test with ws_find
# NOTE: this code produces error if workspace is already released
[[ ! -z "`which ws_allocate 2>/dev/null`" ]] && ws_release $(basename ${CURRENT_WORKDIR})

echo ""
