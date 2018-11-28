#!/bin/bash

#    Copyright (C) 2018 by
#    Sergiy Gogolenko <gogolenko@hlrs.de>   HLRS
#    All rights reserved.
#
# Authors:      Sergiy Gogolenko <gogolenko@hlrs.de>

# module load cray-hdf5-parallel/1.10.2.0
export HDF5_VERSION=1.10.2.0
#export TARGET_PYTHON_VERSION=3.6.1.1
export TARGET_PYTHON_VERSION=2.7.13.1

case "$(hostname --fqdn)" in
'cl3fr2-int') # this is HLRS/Laki
    . ~/.bashrc

    export HPC_CLUSTER_NAME='cl3fr2-int'
    export HDF5_VERSION=1.10.1
    #export TARGET_PYTHON_VERSION=3.6.1.1
    export TARGET_PYTHON_VERSION=2.7.13
    export PIP_COMPILER=mpicc

    module load python/${TARGET_PYTHON_VERSION}
    module load compiler/gnu/6.3.0
    module load mpi/openmpi/2.1.1-gnu-6.3.0
    module load tools/hdf5/${HDF5_VERSION}-openmpi-2.1.1-gnu-6.3.0

    export HDF5_DIR=/opt/tools/hdf5/1.10.1-openmpi-2.1.1-gnu-6.3.0
    mkdir -p ~/opt/pyenv/${HPC_CLUSTER_NAME}/coegss
    python /sw/laki-SL6x/hlrs/python/2.7.13/lib/python2.7/site-packages/virtualenv.py --system-site-packages --never-download \
	   ~/opt/pyenv/${HPC_CLUSTER_NAME}/coegss/`echo $TARGET_PYTHON_VERSION | cut -d. -f1-2` -p `which python`
    ;;
'eagle.man.poznan.pl') # otherwise, assume that this is HLRS/Hazelhen
    # If you work on Eagle, login to the work node first with `srun --pty /bin/bash`
    export HPC_CLUSTER_NAME='eagle.man.poznan.pl'
    export HDF5_VERSION=1.10.1
    export TARGET_PYTHON_VERSION=2.7.14
    export PIP_COMPILER=mpicc

    # echo "DONE: set which modules to use for ${HPC_CLUSTER_NAME}"
    module load python/${TARGET_PYTHON_VERSION}
    module load gcc/6.2.0
    module load openmpi/2.1.2_gcc620
    module load hdf5/${HDF5_VERSION}_openmpi-2.1.2_gcc620

    export HDF5_DIR=$hdf5_root
    mkdir -p ~/opt/pyenv/${HPC_CLUSTER_NAME}/coegss
    virtualenv --system-site-packages --never-download ~/opt/pyenv/${HPC_CLUSTER_NAME}/coegss/`echo $TARGET_PYTHON_VERSION | cut -d. -f1-2` -p `which python`

    # The following code works if virtualenv is not installed
    # curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    # python get-pip.py --user
    # pip install virtualenv --user
    # ~/.local/bin/pip install virtualenv --user
    ;;
*) # otherwise, assume that this is HLRS/Hazelhen
    export HPC_CLUSTER_NAME=hazelhen
    export HDF5_VERSION=1.10.2.0
    #export TARGET_PYTHON_VERSION=3.6.1.1
    export TARGET_PYTHON_VERSION=2.7.13.1
    export PIP_COMPILER=cc

    module switch PrgEnv-cray PrgEnv-gnu
    module load cray-python/${TARGET_PYTHON_VERSION}
    module load cray-hdf5-parallel/${HDF5_VERSION}

    mkdir -p ~/opt/pyenv/${HPC_CLUSTER_NAME}/coegss
    pip install virtualenv --user
    pip install --install-option="--prefix=${HOME}/opt/pyenv/${HPC_CLUSTER_NAME}" virtualenv
    export PYTHONPATH = ~/opt/pyenv/${HPC_CLUSTER_NAME}/lib/python`echo $TARGET_PYTHON_VERSION | cut -d. -f1-2`/site-packages:$PYHTONPATH
    ~/opt/pyenv/${HPC_CLUSTER_NAME}/bin/virtualenv --system-site-packages \
		~/opt/pyenv/${HPC_CLUSTER_NAME}/coegss/`echo $TARGET_PYTHON_VERSION | cut -d. -f1-2` -p `which python`
    ;;
esac

echo "Differences between default and new virtual environments:"
diff <(echo "$(python -c 'import sys; print("\n".join(sys.path))')") \
     <(echo "$(. ~/opt/pyenv/${HPC_CLUSTER_NAME}/coegss/`echo $TARGET_PYTHON_VERSION | cut -d. -f1-2`/bin/activate && python -c 'import sys; print("\n".join(sys.path))' && deactivate)")

read -p "Are you sure? " -n 1 -r; echo ""
if [[ $REPLY =~ ^[Yy]$ ]]
then
    # python -c 'import sys; print("\n".join(sys.path))'
    . ~/opt/pyenv/${HPC_CLUSTER_NAME}/coegss/`echo $TARGET_PYTHON_VERSION | cut -d. -f1-2`/bin/activate
    # python -c 'import sys; print("\n".join(sys.path))'
    CC=${PIP_COMPILER} pip install mpi4py

    CC=${PIP_COMPILER} HDF5_MPI="ON" HDF5_DIR=$HDF5_DIR HDF5_VERSION=`echo $HDF5_VERSION | cut -d. -f1-3` python -m pip install --no-binary=h5py h5py
    CC=${PIP_COMPILER} python -m pip install matplotlib
    CC=${PIP_COMPILER} python -m pip install scipy
    CC=${PIP_COMPILER} python -m pip install pandas
    CC=${PIP_COMPILER} python -m pip install argparse
    CC=${PIP_COMPILER} python -m pip install psutil
    CC=${PIP_COMPILER} python -m pip install datetime
    CC=${PIP_COMPILER} python -m pip install geopandas
    CC=${PIP_COMPILER} python -m pip install numpy

    deactivate
fi

ENVPYTHON_VERSION=`echo $TARGET_PYTHON_VERSION | cut -d. -f1-2`
echo """Installation succeeded.
Usage::

    . ~/opt/pyenv/${HPC_CLUSTER_NAME}/coegss/${ENVPYTHON_VERSION}/bin/activate
    aprun -n 1 python ~/test.py
    deactivate
    
"""
