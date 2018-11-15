# Cloudify blueprint for running HPC jobs

This folder contains blueprint and auxiliary files for running SN4SP scripts 
on HPC clusters under supervision of [Cloudify](https://cloudify.co/) orchestration toolchain (HPCaaS). 
It includes:

- subfolder `blueprint` containing sources of the blueprint
- template for the blueprint inputs `local-blueprint-inputs.template.yaml`
- auxiliary scripts that help to communicate with CKAN
  - `ckan_download_data.py` downloads CKAN datasets
  - `ckan_upload_data.py` uploads files to CKAN
- scripts for fast 

Blueprint files are YAML files written in accordance with [OASIS TOSCA](http://docs.oasis-open.org/tosca/TOSCA/v1.0/os/TOSCA-v1.0-os.pdf) standard that
describe the execution plans for the lifecycle of the application including installing,
starting, terminating, orchestrating, and monitoring steps.
Our blueprint allows to submit network reconstruction jobs to HPC clusters.
It makes use of [Cloudify HPC plugin](https://github.com/MSO4SC/cloudify-hpc-plugin).

## Inputs 

This blueprint defines the inputs that specify arguments of the script and the inputs that specify details of the application lifecycle.
The first group includes the following inputs:

- `half_similarity` which defines half-similarity scale. The default value is 5000.
- `damping` which defines geo-damping in similarity network model. By default, it is set to 0.
- `stripe_size` which defines fraction of the sample used in computing Lin similarity. The default value is 0.1.

The second group contains the following inputs:

- `hpc_configuration` which defines workload manager information and credentials to the remote HPC system.
  This input does not have a default value and, thus, must be specifies in inputs when the blueprint is deployed.
- `num_tasks` which defines the number of MPI processes.
- `python_module` which defines . By default, we assume that the name of the module is `tools/python/coegss/2.7`.
- `job_prefix` which contains job name prefix on HPC. Default prefix is `coegss`.

## Usage 

### Cloudify CLI

In order to run application with the Cloudify manager, the user must do the following steps:

- upload the blueprint to the manager:
  
- deploy the blueprint:
  At this step, the user must specify blueprint inputs.
- run `install` execution
  `install` execution launches bootstrapping scripts with the blueprint inputs as arguments,
  which produces batch scripts for the workload manager. 
- launch `job_run` execution
  `job_run` execution put the batch scripts into the workload manager queue.

As soon as, the parallel job is finished, the user must uninstall blueprint from Cloudify manager
if there are no plans for running HPC jobs once again:
- call `uninstall` execution
  This execution launches job reversion scripts.
- deletes blueprint deployment
- uninstall blueprint

## Interaction with CKAN 

1. Script `ckan_download_data.py`

**Example:** Format for Json specification of resources to upload in CKAN dataset
```{json}
[
    [
        "synthpop_piedmont.h5",
        { "name" : "Synthetic population", "description" : "Synthetic population of Piedmont, Italy" }
    ],
    [
        "piemonte_gdf.pkl.gz",
        { "name" : "Geodata", "description" : "GZipped PKL file with serialized geodata" }
    ]
]
```

## Testing

In order to test this blueprint, one needs access to Cloudify manager. 
In case, you do not have access to Cloudify manager, you can deploy manager locally.
There are 2 fast options for deployment:

- use Cloudify manager VM
- use Cloudify manager Docker image

### VM

1. Download official Cloudify manager VM distribution:

   $ wget http://repository.cloudifysource.org/cloudify/18.9.13/community-release/cloudify-manager-community-18.9.13.qcow2

2. Run this VM in VM-manager
3. Identify IP of this VM:

   $ nmap -sP 192.168.122.0/24
   >>> 111.222.333.444

4. Use this IP to create profile on Cloudify VM:

   $ cfy profiles use 111.222.333.444 -u admin -p admin -t default_tenant

5. Run parallel job using the blueprint:

   $ ./network-reconstruction-sbatch-up.sh

6. Uninstall blueprint:

   $ ./network-reconstruction-sbatch-down.sh

Read more about installation [here](https://cloudify.co/guide/3.1/installation-cli.htm)

### Docker

1. :
   $ sudo docker run --name cfy_manager_local -d --restart unless-stopped -v /sys/fs/cgroup:/sys/fs/cgroup:ro --tmpfs /run --tmpfs /run/lock --security-opt seccomp:unconfined --cap-add SYS_ADMIN -p 80:80 -p 8000:8000 cloudifyplatform/community:18.7.23
   $ docker exec -it cfy_manager_local /bin/bash

2. Use this IP to create profile on Cloudify VM:

   $ cfy profiles use 192.168.122.22 -u admin -p admin -t default_tenant
   $ cfy status

3. Copy blueprint to docker image:

   $ docker cp ./tools/cloudify cfy_manager_local:/target
   $ cd ./tools/cloudify/

4. Run parallel job using the blueprint:

   $ ./network-reconstruction-sbatch-up.sh

5. Uninstall blueprint:

   $ ./network-reconstruction-sbatch-down.sh

Read more about installation with Docker [here](https://cloudify.co/getting-started/)
