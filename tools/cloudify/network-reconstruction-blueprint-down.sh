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
## Remove network reconstruction blueprint from Cloudify
############################################################

cd blueprint
echo "Uninstalling deployment.."
cfy executions start -d network-reconstruction-sbatch-job uninstall
echo "Deleting deployment.."
cfy deployments delete network-reconstruction-sbatch-job
echo "Deleting blueprint.."
cfy blueprints delete network-reconstruction-sbatch-job
