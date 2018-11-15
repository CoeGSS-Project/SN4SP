# Integration of the network reconstruction tool with the portal

The portal enables launching applications on the remote HPC systems with aid of Cloudify [1]. For each application launched remotely, Cloudify requires configuration files called blueprints. Blueprint files are YAML files written in accordance with OASIS TOSCA standard [2]. They describe the execution plans for the lifecycle of the application including installing, starting, terminating, orchestrating, and monitoring steps.

In our case, the network reconstruction algorithm is implemented as a Python script. The blueprint for this script makes use of Cloudify HPC plugin presented in D5.11 [3].

This blueprint defines the inputs that specify arguments of the script and the inputs that specify details of the application lifecycle. The first group includes the following inputs:
- `synpop_path` which contains the path to the input HDF5 file with the synthetic population. It does not have a default value and, thus, must be specified in inputs when the blueprint is deployed.
- `synnet_path` which contains the name to the output HDF5 file with the synthesized network. By default, we use the name of the synthetic population input file suffixed with `_network`.
- `half_similarity` which defines half-similarity scale. The default value is 5000.
- `damping` which defines damping. By default, it is set to 0.
- `stripe_size` which represents percentage of the sample for the similarity calculation. The default value is 0.1.
The second group contains the following inputs:
- `hpc_configuration` which defines workload manager information and credentials of the remote HPC system to run the script on. This parameter does not have a default value and, thus, must be specifies in inputs when the blueprint is deployed.
- `num_tasks` which defines the number of MPI processes.
- `monitor_entrypoint` which specifies IP of the external task monitoring server. By default, we use the simple Python monitor implemented directly into Cloudify HPC plugin.
- `python_module` which defines name of the module that must be loaded on the target HPC to get access to Python 2.7 environment with libraries that network reconstruction script dependences on. In particular, this environment must include mpi4py>=2.0, H5py>=2.8, DateTime>=4.2, psutil>=5.4.7, matplotlib>=2.2.3, numpy>=1.11.3 scipy>=0.19, pandas>=0.23.4, geopandas>=0.4 . By default, we assume that the name of the module is `tools/python/coegss/2.7`.
- `job_prefix` which contains job name prefix on HPC. Default prefix is "coegss".

In order to make things run smoothly on different HPC clusters, we accompany the blueprint file with job bootstrapping and reversion bash scripts. The bootstrapping script creates batch script for the workload manager (TORQUE or SLURM) and allocates workspace for the network reconstruction output file if the latter is supported by the target HPC cluster. Note that workspace allocation helps to avoid IO problems since the output files require $O(n^2)$ disk space and may easily overcome limits for the user’s home folder. The reversion script takes care of uploading output file to CKAN, releases workspace, and removes batch script for the workload manager.

In order to run application with the Cloudify manager, the user must do the following steps: upload the blueprint to the manager, deploy this blueprint, launch "install" and `job_run`  executions. Since the network reconstruction script is a part of CoeGSS toolchain, its blueprint is already uploaded to our Cloudify manager VMs manually. So, in contrast to the other steps, blueprint uploading step does not require interaction with the portal.  For the remaining three steps, the portal interacts with the Cloudify managers via Cloudify REST client API [4]. In particular, in the blueprint deployment step, we convey blueprint inputs from the portal Web GUI to the Cloudify manager and the Cloudify manager copies application bootstrapping and reversion scripts to the target HPC cluster. After the blueprint deployment, we run the `install` execution which launches bootstrapping scripts with the blueprint inputs as arguments. As a result, we obtain a  batch script for the workload manager. Finally, we put this batch script into the workload  manager queue via calling the `job_run` execution in the Cloudify manager. As soon as, the parallel job is finished and the portal get informed about it by the Cloudify manager, the portal calls `uninstall` execution which launches job reversion script. Afterwards, the portal deletes blueprint deployment.

# VM

```
wget http://repository.cloudifysource.org/cloudify/18.9.13/community-release/cloudify-manager-community-18.9.13.qcow2
nmap -sP 192.168.122.0/24
cfy profiles use 192.168.122.22 -u admin -p admin -t default_tenant
virtualenv ~/py27cloudify -p `which python`
```

Read more about installation [here](https://cloudify.co/guide/3.1/installation-cli.htm)

# Docker

```
sudo docker run --name cfy_manager_local -d --restart unless-stopped -v /sys/fs/cgroup:/sys/fs/cgroup:ro --tmpfs /run --tmpfs /run/lock --security-opt seccomp:unconfined --cap-add SYS_ADMIN -p 80:80 -p 8000:8000 cloudifyplatform/community:18.7.23
docker exec -it cfy_manager_local /bin/bash

cfy profiles use 192.168.122.22 -u admin -p admin -t default_tenant
cfy status

docker cp ./cloudify_blueprint_0_1 cfy_manager_local:/target
cd ./cloudify_blueprint_0_1/

cfy blueprints upload -b network-reconstruction-sbatch-job blueprint.yaml
cfy deployments create -b network-reconstruction-sbatch-job -i ../local-blueprint-inputs.yaml --skip-plugins-validation network-reconstruction-sbatch-job

python ./network-reconstruction-sbatch-up.py
```

Read more about installation with Docker [here](https://cloudify.co/getting-started/)

# Authentification to remote clusters with keys from Cloudify

1. Admin should generating a new SSH key pair and distribute public key between users
```
	ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
```
2. Users must add this public key to `known_hosts` on HPCs they want to access via Cloudify HPC plugin
```
    ssh-copy-id hpcgogol@hazelhen.hww.hlrs.de
```

# Interaction with CKAN 

1. `upload_data.py`

Example: Format for Json specification of resources to upload in CKAN dataset
```{json}
[
    [
        "synthPop_Piedmont_10pc_2011.h5",
        { "name" : "Synthetic population", "description" : "Synthetic population of Piedmont, Italy" }
    ],
    [
        "Piemonte_NUTS3_to_LAU2_gdf.pkl.gz",
        { "name" : "Geodata", "description" : "GZipped PKL file with serialized geodata" }
    ]
]
```

# References

[1] Cloudify documentation / URL https://docs.cloudify.co/4.4.0/
[2] Topology and Orchestration Specification for Cloud Applications Version 1.0 OASIS Standard, 2013, 114 p. URL: http://docs.oasis-open.org/tosca/TOSCA/v1.0/os/TOSCA-v1.0-os.pdf
