#! /usr/bin/env python
# -*- coding: utf-8 -*-

#    Copyright (C) 2018 by
#    Sergiy Gogolenko <gogolenko@hlrs.de>   HLRS
#    Fabio Saracco    <fabio@imt.it>        IMT
#    All rights reserved.
#
# Authors:      Sergiy Gogolenko <gogolenko@hlrs.de>

from __future__ import division, absolute_import, print_function

__author__ = '\n'.join( ['Sergiy Gogolenko <gogolenko@hlrs.de>',] )

import os
import sys
import logging
import datetime
import argparse

from mpi4py import MPI

# TODO: analyse tools
# from guppy import hpy
import cProfile

# Profiling decorator for ``cProfile`` suggested in
# https://stackoverflow.com/questions/33503176/profile-parallelized-python-script-with-mpi4py
def profile(filename=None, comm=MPI.COMM_WORLD):
    def prof_decorator(f):
        def wrap_f(*args, **kwargs):
            prof = cProfile.Profile()
            prof.enable()
            result = f(*args, **kwargs)
            prof.disable()

            if filename is None:
                prof.print_stats()
            else:
                prof.dump_stats( "{0}.{1}".fortmat(filename, comm.rank) )

            return result
        return wrap_f
    return prof_decorator

# TODO: remove in alpha release
sys.path.insert( 0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0])))) )
import sn4sp
from sn4sp import readwrite
from sn4sp import parallel

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
    logger = logging.getLogger()
    logger.propagate = False

    # Handle command line arguments
    args=get_arguments()

    # Read input synthetic population and produce similarity network object out of it
    sim_net=readwrite.read_attr_table_h5(args.input, hss=args.hss, damping=args.damping, sample_fraction=args.sample_fraction)

    # Compute similarity network edge probabilities and store in HDF5 edgelist file
    scheduling_types = parallel.triu._scheduling_types
    elapsed_times = [0]*len(scheduling_types)
    for no, scheduling_type in enumerate(scheduling_types):
        start_time=MPI.Wtime()
        k = 0
        for i, j, p in sim_net.edges_probabilities(scheduning=scheduling_type):
            if k > 1000000: break
            k += 1
        elapsed_times[no] = MPI.Wtime() - start_time
    print( '{2},time,{1},{0}'.format(len(sim_net), ','.join(map(str, elapsed_time/1000000)), MPI.COMM_WORLD.Get_rank()) )

    return 0

if __name__ == "__main__":
    main()
