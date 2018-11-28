# SN4SP

**SN4SP** is a basic Python package for reconstructing synthetic networks from limited data
about node attributes (synthetic population).

- **Source:** https://github.com/CoeGSS-Project/SN4SP
- **Bug reports:** https://github.com/CoeGSS-Project/SN4SP/issues
- **Documentation**: https://sn4sp.readthedocs.io

It provides:
  1. a similarity network object which partially reproduce interface of `networkX` graphs
  2. functions to load synthetic population and store similarity graph in [HDF5][HDF5] format
  3. API to synthetize networks on parallel and distributed facilities with [MPI](https://www.mpi-forum.org/).
  4. preprocessing script (in order to provide the proper file structure to the main script)
  5. similarity network script, which produces a [HDF5][HDF5] file containing the (weighted)
     influence matrix based on the [Lin similarity](http://dl.acm.org/citation.cfm?id=645527.657297). 
  6. Cloudify blueprint for submitting network reconstruction scripts to HPC clusters.

More details can be found in CoeGSS deliverables
([D3.4](http://coegss.eu/wp-content/uploads/2018/11/D3.4.pdf)
and [D3.7](http://coegss.eu/wp-content/uploads/2018/11/D3.7.pdf)).

[HDF5]: https://support.hdfgroup.org/HDF5/

## Install

Basic installation via `setup-tools`:
```sh
mpiexec -n 1 python setup.py install
```
For additional details, please see [`INSTALL.rst`](INSTALL.rst).

## Simple example

```python
import sn4sp
G = sn4sp.readwrite.read_attr_table_h5("synthetic_population.h5")
G = sn4sp.readwrite.write_edges_probabilities_h5(G, "synthetic_network.h5")
```

## Bugs

Please report any bugs that you find [here](https://github.com/CoeGSS-Project/SN4SP/issues).
Or, even better, fork the repository on [GitHub](https://github.com/CoeGSS-Project/SN4SP)
and create a pull request (PR). We welcome all changes, big or small.

## License

Released under the Creative Commons Attribution 4.0 International license (see `LICENSE.txt`):

    Copyright (C) 2018 SN4SP Developers
    Sergiy Gogolenko <gogolenko@hlrs.de>
    Fabio Saracco    <fabio@imt.it>
