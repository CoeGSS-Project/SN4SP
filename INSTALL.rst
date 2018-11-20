Building and installing SN4SP
+++++++++++++++++++++++++++++

**IMPORTANT**: the below notes are about building SN4SP, which is
the only way to install SN4SP for this moment.
``pip`` support is not implemented yet.

.. Contents::

Prerequisites
=============

Building SN4SP requires the following software installed:

1) Python 2, Python__ 2.7.x or newer.

   On Debian and derivative (Ubuntu): python python-dev

   On Windows: the official python installer is enough

   Make sure that the Python package distutils is installed before
   continuing. For example, in Debian GNU/Linux, distutils is included
   in the python-dev package.

   Python must also be compiled with the zlib module enabled.

2) ``numpy >= 0.14``

3) ``mpi4py``

4) ``h5py``, parallel version

   This is required for both testing and using ``sn4sp``.

Python__ http://www.python.org


Basic Installation
==================

To install ``sn4sp`` run::

    $ python setup.py build -j 2 install --prefix $HOME/.local

This will compile ``sn4sp`` on 2 CPU cores and install it into the specified prefix.
To perform an inplace build that can be run from the source folder run::

    $ python setup.py build_ext --inplace -j 2

Note that the ``python`` command here is the system default Python. Use 
``python2`` if your default environment is set for python 3.
See `Requirements for Installing Packages <https://packaging.python.org/tutorials/installing-packages/>`_
for more details.

Building on HPC clusters
========================

Cray Clusters
-------------

TODO

   Execution on Cray clusters requires to disable HDF5 file locking ``export HDF5_USE_FILE_LOCKING=FALSE`` if use ``h5py``.

Build issues
============

If you run into build issues and you clearly see a bug in SN4SP, please file an issue
(or even better, a pull request) at https://github.com/CoeGSS-Project/sn4sp.
