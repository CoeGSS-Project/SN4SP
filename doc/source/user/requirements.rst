
.. Contents::

Building and Installing Prerequisites
=====================================

The following steps are required to be done on the compute nodes of clusters
in order to satisfy ``sn4sp`` prerequisites.

1) Set up environment variables and load modules for pre-installed third-party libraries.

   The following code snippet illustrates how to do it on Cray platforms.

   .. code-block:: bash

      export HPC_CLUSTER_NAME=hazelhen
      export TARGET_PYTHON_VERSION=2.7.13.1
      export HDF5_VERSION=1.10.2.0
      export PIP_COMPILER=cc

      module switch PrgEnv-cray PrgEnv-gnu
      module load cray-python/${TARGET_PYTHON_VERSION}
      module load cray-hdf5-parallel/${HDF5_VERSION}

2) Create `virtual environment <https://virtualenv.pypa.io/>`_ (install ``virtualenv`` if it is not available).

   The following code snippet illustrates how to do it on Cray platforms.

   .. code-block:: bash

      mkdir -p ~/opt/pyenv/${HPC_CLUSTER_NAME}/coegss
      pip install virtualenv --user
      pip install --install-option="--prefix=${HOME}/opt/pyenv/${HPC_CLUSTER_NAME}" virtualenv
      export PYTHONPATH = ~/opt/pyenv/${HPC_CLUSTER_NAME}/lib/python`echo $TARGET_PYTHON_VERSION | cut -d. -f1-2`/site-packages:$PYHTONPATH
      ~/opt/pyenv/${HPC_CLUSTER_NAME}/bin/virtualenv --system-site-packages \
           ~/opt/pyenv/${HPC_CLUSTER_NAME}/coegss/`echo $TARGET_PYTHON_VERSION | cut -d. -f1-2` -p `which python`

3) Revise the difference between default and virtual Python environments.

   The following code snippet illustrates how to do it on Cray platforms.

   .. code-block:: bash

      echo "Differences between default and new virtual environments:"
      diff <(echo "$(python -c 'import sys; print("\n".join(sys.path))')") \
         <(echo "$(. ~/opt/pyenv/${HPC_CLUSTER_NAME}/coegss/`echo $TARGET_PYTHON_VERSION | cut -d. -f1-2`/bin/activate && python -c 'import sys; print("\n".join(sys.path))' && deactivate)")

4) Install missing Python libraries in the created Python environment.

   The following code snippet illustrates how to do it on Cray platforms.

   .. code-block:: bash

      . ~/opt/pyenv/${HPC_CLUSTER_NAME}/coegss/`echo $TARGET_PYTHON_VERSION | cut -d. -f1-2`/bin/activate

      CC=${PIP_COMPILER} python -m pip install mpi4py
      CC=${PIP_COMPILER} HDF5_MPI="ON" HDF5_DIR=$HDF5_DIR HDF5_VERSION=`echo $HDF5_VERSION | cut -d. -f1-3` \
          python -m pip install --no-binary=h5py h5py
      CC=${PIP_COMPILER} python -m pip install matplotlib
      CC=${PIP_COMPILER} python -m pip install scipy
      CC=${PIP_COMPILER} python -m pip install pandas
      CC=${PIP_COMPILER} python -m pip install argparse
      CC=${PIP_COMPILER} python -m pip install psutil
      CC=${PIP_COMPILER} python -m pip install datetime
      CC=${PIP_COMPILER} python -m pip install geopandas
      CC=${PIP_COMPILER} python -m pip install numpy

      deactivate

You can find examples for deployment of prerequisites on different platforms
in file :download:`this example script <deployment_example.sh>`.
