#!/bin/bash
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
## Run network reconstruction job on HPC via Cloudify
############################################################

cd blueprint
cfy blueprints upload -b network-reconstruction-sbatch-job blueprint.yaml
# read -n 1 -s -p "Press any key to continue"
# echo ''
cfy deployments create -b network-reconstruction-sbatch-job -i ../local-blueprint-inputs.yaml --skip-plugins-validation network-reconstruction-sbatch-job
# read -n 1 -s -p "Press any key to continue"
# echo ''
cfy executions start -d network-reconstruction-sbatch-job install

read -p "Press Y to run job " -n 1 -r; echo ""
if [[ $REPLY =~ ^[Yy]$ ]]
then
    cfy executions start -d network-reconstruction-sbatch-job run_jobs
fi
