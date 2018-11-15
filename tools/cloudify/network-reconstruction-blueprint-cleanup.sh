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
## Remove network reconstruction blueprint if failed
############################################################

# Requires "run_job" execution ID. E.g., "9613d0c1-ec87-4acf-baf0-bcd90744ee7a"
cfy executions cancel -f $1
echo "Deleting deployment.."
cfy deployments delete -f network-reconstruction-sbatch-job
echo "Deleting blueprint.."
cfy blueprints delete network-reconstruction-sbatch-job
