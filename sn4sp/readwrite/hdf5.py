#    Copyright (C) 2018 by
#    Sergiy Gogolenko <gogolenko@hlrs.de>   HLRS
#    Fabio Saracco    <fabio@imt.it>        IMT
#    All rights reserved.
#
# Authors:      Sergiy Gogolenko <gogolenko@hlrs.de>
#               Fabio Saracco <fabio@imt.it>
"""
****
HDF5
****
Read synthetic population to similarity network niodes from HDF5 file
and writes similarity network as edge lists to HDF5 file.
"""
__author__ = '\n'.join(['Sergiy Gogolenko <gogolenko@hlrs.de>',
                        'Fabio Saracco <fabio@imt.it>'])
__all__ = ['write_edges_probabilities_h5',
           'read_attr_table_h5']

import logging
import datetime
import psutil

from mpi4py import MPI
import numpy
import h5py

from sn4sp.core import SimilarityGraph

def read_attr_table_h5(path, attr_types=None, attr_group='SPP10pc', attr_values_dataset='ppd', attr_types_dataset='da', **kwargs):
    """ Read node (agent) attributes in HDF5 format.

    Args:
        path:        path to HDF5 file with node attributes
        attr_types:  sequence (list) of characters that helps to distinguish between attribute types:
                     'c' -- categorical, 'o' - ordinal,'g' - geographic (latitude/longitude)

    Returns:
        Similarity network object initialized with the node attributes from file `path`.

    Raises:
        IOError:    An error occurred accessing the HDF5 input file.
        ValueError: An error occurred in characterization of attribute types.

    Examples
    --------
    >>> read_attr_table_h5(filename)
    >>> read_attr_table_h5(filename, list("cocccoggggo"), attr_group="attributes")
    See Also
    --------
    write_edges_probabilities_h5
    """
    with h5py.File( path, 'r' ) as fp:
        try:
            if attr_types is None:
                attr_types=numpy.array(fp[attr_group].get(attr_types_dataset))
            if not hasattr(attr_types, '__iter__'):
                raise ValueError( r'List of attribute types "attr_types" is not iterable (type={0})'.format(type(attr_types)) )

            vertex_attrs=numpy.array(fp[attr_group].get(attr_values_dataset))[:1000]
            # numpy.savetxt('test_data.csv', vertex_attrs, fmt='%3.4f', delimiter=', ', newline='],\n[',
            #               header=','.join(vertex_attrs.dtype.names), footer='', comments='# ')
            if len(attr_types) != len(vertex_attrs.dtype.names):
                raise ValueError( r'List of attribute types [{0}] is incompatible with attribute data [{1}]'.\
                                  format( ','.join(map(str,attr_types)),
                                          ','.join(vertex_attrs.dtype.names)) )
        finally:
            fp.close()
            #raise IOError('cannot read input file "{0}"'.format(path))
    # Log data about node attributes (synthetic population)
    if MPI.COMM_WORLD.Get_rank() == 0:
        logging.debug( 'attr_names=[{0}]'.format(','.join(vertex_attrs.dtype.names)) )
        logging.debug( 'attr_types=[{0}]'.format(','.join(map(str,attr_types))) )
        logging.debug( 'num_agents={0}'.format(vertex_attrs.shape[0]) )

        for attr_name, attr_type in zip(vertex_attrs.dtype.names, attr_types):
            if attr_type == 'c':
                logging.debug( 'categorie codes for {0}=[{1}]'.format(attr_name, ','.join(map(str, numpy.unique(vertex_attrs[attr_name])))) )
    return SimilarityGraph(vertex_attrs, attr_types, **kwargs)

def write_edges_probabilities_h5(G, path, network_group="SimNet", edges_dataset="edge_list", chunk_len=int(1e4)):
    """Write edge probabilities of the similarity network G in edge-list format to HDF5 file.
    Parameters
    ----------
    G : similarity network
    path : string or file
       Filename (or file handle) for data output.
    chunk_len: int
       Size of chunks for writting to HDF5 file
    Examples
    --------
    >>> write_edges_probabilities_h5(G,"test.h5")
    See Also
    --------
    read_attr_table_h5
    """
    # chunk_dim=min(int(chunk_dim), num_vertices)

    edge_list_type=[('src_node','i8'), ('trg_node','i8'), ('weight','f8')]
    with h5py.File( path, 'w', driver='mpio', comm=G.comm, libver='latest' ) as output_file:
        network_group=output_file.create_group(network_group)

        # TODO: Think of how to write data in a single dataset
        for rank in xrange(G.comm.Get_size()):
            grp = network_group.create_group(str(rank))
            # 'adj_list'
            grp.create_dataset( edges_dataset, shape=(chunk_len,), maxshape=(None,),
                                chunks=True, dtype=edge_list_type )
        process_group=network_group[str(G.comm.Get_rank())]
        edge_list=process_group[edges_dataset]

        logging.info( 'Output file is created. Process {0} starts the calculation'.format(G.comm.Get_rank()) )
        start_time=datetime.datetime.now()

        # k - index in edge_buffer
        # offset - position in the dataset to write new data
        k, offset=0, 0
        edge_buffer=numpy.zeros(chunk_len, dtype=edge_list_type)
        for i, j, edge_prob in G.edges_probabilities():
            if edge_prob > 0.:  # store only non-zero entries
                edge_buffer[k]=(i, j, edge_prob)
                k+=1
                # when chunk size is reached, the data is copied to file
                if k == chunk_len:
                    edge_list[offset:offset+chunk_len]=edge_buffer
                    k=0
                    offset+=chunk_len

                    # Log progress
                    # TODO: improve log to show percentage of processed entries
                    logging.info( 'Current position {0}. Elapsed time={1}.'.\
                                  format((i,j), (datetime.datetime.now()-start_time)) )
                    # # Checking memory usage
                    # if psutil.virtual_memory().available <= 104857600:  # 100MB
                    #     #100 MB
                    #     logging.warning( 'we are running out of memory! Remains {0}KB'.format(psutil.virtual_memory().available/1024) )
                    # # Checking swap memory
                    # if psutil.swap_memory().percent > .9:
                    #     logging.warning( 'the swap is occupied at the {0}%!'.format(psutil.swap_memory().percent*100) )

        # Store the last portion of edges to dataset
        if k != 0:
            edge_list[offset:offset+k]=edge_buffer[:k]
            offset+=k

        # Fix size of the dataset and close file
        edge_list.resize((offset,))
        output_file.close()

        logging.info( 'file "{0}" is closed'.format(path) )
