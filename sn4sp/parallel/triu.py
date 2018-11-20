#    Copyright (C) 2018 by
#    Sergiy Gogolenko <gogolenko@hlrs.de>   HLRS
#    Fabio Saracco    <fabio@imt.it>        IMT
#    All rights reserved.
#
# Authors:      Sergiy Gogolenko <gogolenko@hlrs.de>
#               Fabio Saracco <fabio@imt.it>
"""
****************
Upper triangular 
****************
Provides parallel iterators for iterating over upper triangular
part of the matrix
"""
from __future__ import division, absolute_import, print_function

__author__ = '\n'.join(['Sergiy Gogolenko <gogolenko@hlrs.de>',
                        'Fabio Saracco <fabio@imt.it>'])

__all__ = [ 'triu_index',
            'triu_round_robin_index',
            'triu_even_index' ]

import logging

from math import sqrt

def triu_even_index(dims, comm):
    """ An iterator for upper triangular part of 2D matrix.
    Distributes upper triangular matrix elements evenly between processes
    as if it were stored densely in a flat 1D array row-by-row (row major way). 
    Parameters
    ----------
    dims : int
        dimensionality of the matrix
    comm : mpi4py.MPI.Comm
        MPI communicator
    See Also
    --------
    triu_round_robin_index
    Examples
    --------
    >>> for index in triu.triu_even_index():
    ...     print(index)
    """

    comm_rank=comm.Get_rank()
    comm_size=comm.Get_size()

    # Estimate number of potential edges (couples)
    num_couples=int((dims - 1)*dims/2)  # total number of couples (potential edges) in the graph.
    def pos2ij(pos):
        """Convert position in an upper triangular matrix to a pair of indices (i,j)."""
        i=int(dims - sqrt((dims-.5)**2 - 2.*pos) - 0.5) # take floor with `int`
        j=int(pos + i*(i + 1)/2 - i*(dims - 1) + 1)
        return i,j
    def ij2pos(i,j):
        """Convert pair of indices (i,j) to a position in an upper triangular matrix."""
        return int(i*dims - i*(i + 3)/2 + j)

    # Distribute computational work (couples) between MPI process.
    couples_per_process=num_couples // comm_size  # ceil(num_couples/num_processes)
    couples_remainder=num_couples % comm_size
        
    # (i0,j0) - indices of the first couple to handle in the current process.
    # (ie,je) - indices of the last couple to handle in the current process
    #           (if the process is last use the next after the last valid couple of indices).
    if comm_rank < couples_remainder:
        i0,j0=pos2ij((couples_per_process+1)*comm_rank)
        ie,je=pos2ij((couples_per_process+1)*(comm_rank + 1))
    else:
        i0,j0=pos2ij(couples_per_process*comm_rank + couples_remainder)
        ie,je = (dims - 1, dims) if comm_rank + 1 == comm_size else \
                pos2ij(couples_per_process*(comm_rank + 1) + couples_remainder)

    # logging.info( 'Iterate over couples between {0} and {1}, number of couples {2}'.\
    #               format((i0,j0), (ie,je), ij2pos(ie,je)-ij2pos(i0,j0)) )

    # Iterate over couples
    i, j = i0, j0
    while i!=ie or j!=je:
        yield i, j

        j+=1
        if j == dims:  # move to the next row
            i+=1
            j=i+1

def triu_round_robin_index(dims, comm):
    """ An iterator for upper triangular part of 2D matrix.
    Iterates by rows in a Round-Robin fasion.
    Parameters
    ----------
    dims : int
        dimensionality of the matrix
    comm : MPI_Communicator
        MPI communicator
    See Also
    --------
    triu_even_index
    Examples
    --------
    >>> for index in triu.triu_round_robin_index(comm):
    ...     print(index)
    """

    for i in xrange(comm.Get_rank(), dims, comm.Get_size()):
        for j in xrange(i+1, dims):
            yield i, j

def triu_index(dims, comm, scheduning='even'):
    """ An iterator for upper triangular part of 2D matrix.
    Parameters
    ----------
    dims : int
        dimensionality of the matrix
    comm : MPI_Communicator
        MPI communicator
    scheduning : str
        type of iteration:
        - ``even`` Distributes upper triangular matrix elements evenly between processes
          as if it were stored densely in a flat 1D array row-by-row (row major way). 
        - ``round_robin`` Iterates by rows in a Round-Robin fasion.
    See Also
    --------
    triu_even_index
    Examples
    --------
    >>> for index in triu.triu_round_robin_index(comm):
    ...     print(index)
    """
    if scheduning not in ('even', 'round_robin'):
        raise ValueError('Unknown scheduling type "{0}"'.format(scheduning))
    return eval('sn4sp.parallel.triu.triu_{0}_index(dims, comm)'.format(scheduning))
