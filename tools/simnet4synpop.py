#! /usr/bin/env python
# -*- coding: utf-8 -*-

#    Copyright (C) 2018 by
#    Sergiy Gogolenko <gogolenko@hlrs.de>   HLRS
#    Fabio Saracco    <fabio@imt.it>        IMT
#    All rights reserved.
#
# Authors:      Sergiy Gogolenko <gogolenko@hlrs.de>
#               Fabio Saracco <fabio@imt.it>
"""
.. module:: sn4sp
   :platform: Unix, Windows
   :synopsis: Similarity Network 4 Synthetic Population : Network reconstruction with Lin similarity and geo-damping
"""
from __future__ import division, absolute_import, print_function

__author__ = '\n'.join( ['Sergiy Gogolenko <gogolenko@hlrs.de>',
                         'Fabio Saracco <fabio@imt.it>'] )

import os
import sys
import logging
import datetime
import argparse

from mpi4py import MPI

# TODO: remove in alpha release
sys.path.insert( 0, os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))) )
import sn4sp
from sn4sp import readwrite

def get_arguments():
    """ Get the argument from the command line.
    By default, we use exponential damping and half-length scale set to 5 km.
    """
    parser = argparse.ArgumentParser(description="Similarity Network 4 Synthetic Population calculator")
    parser.add_argument( "input", metavar="HDF5_FILE",
                         nargs='?', type=str,
                         help="input HDF5 file with synthetic population",
                         default=os.path.join(os.getcwd(), 'synthetic_population_ppd.h5') )
    parser.add_argument( "-o", "--output",
                         dest="output", type=str,
                         help="output HDF5 file with synthesized network",
                         default=os.getcwd() )

    parser.add_argument( "-hss", "--half-sim-scale",
                         dest="hss", type=float,
                         help="half-similarity scale",
                         default=5000 )
    parser.add_argument( "-d", "--damping",
                         dest="damping", type=float,
                         help="damping function",
                         default=0.0 )
    parser.add_argument( "-p", "--sampling-percentage",
                         dest="sample_fraction", type=float,
                         help="fraction of the sample (stripe size) for the parallel similarity calculation",
                         default=0.1 )
    return parser.parse_args()

def main():
    # Set up logger
    logger_fmt='%(asctime)s [process_id={0:03}:{1}] %(message)s'.format(MPI.COMM_WORLD.Get_rank(), MPI.COMM_WORLD.Get_size())
    if True:    # use stdout logger
        log_root=logging.getLogger()
        log_root.setLevel(logging.DEBUG)
        log_channel=logging.StreamHandler(sys.stdout)
        log_channel.setLevel(logging.DEBUG)
        log_channel.setFormatter(logging.Formatter(fmt=logger_fmt, datefmt=':%Y-%m-%d %H:%M:%S'))
        log_root.addHandler(log_channel)
    else:       # use stderr logger
        logging.basicConfig(format=logger_fmt, datefmt=':%Y-%m-%d %H:%M:%S', level=logging.INFO)

    # Handle command line arguments
    args=get_arguments()

    # Read input synthetic population and produce similarity network object out of it
    sim_net=readwrite.read_attr_table_h5(args.input, hss=args.hss, damping=args.damping, sample_fraction=args.sample_fraction)

    # Compute similarity network edge probabilities and store in HDF5 edgelist file
    start_time=MPI.Wtime()
    readwrite.write_edges_probabilities_h5( sim_net, os.path.join(args.output, 'synthetic_network_hss_{0}_d_{1}.h5'.format(args.hss,args.damping)),
                                            chunk_len=int(1e4) )
    elapsed_time=MPI.Wtime() - start_time
    logging.info( 'total elapsed time={0}. # {1}'.format(datetime.timedelta(seconds=elapsed_time), MPI.COMM_WORLD.Get_rank()) )

    return 0

if __name__ == "__main__":
    main()
