"""
.. module:: piedmont
   :platform: Unix, Windows
   :synopsis: Similarity Network 4 Synthetic Population : Network reconstruction with Lin similarity
"""

import os
import sys
import logging
import datetime
import argparse

import psutil
import platform

from mpi4py import MPI
import numpy
# from scipy import linalg as la
# import math
import h5py

source=MPI.ANY_SOURCE
GLOBAL_SIM_TH=10**-6
r_earth=6.3781*10**6    # Earth radius in meters

# ----------------------------------------------------------------------------------------
# Interface routines
# ----------------------------------------------------------------------------------------
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

def preprocessing(synpop_file):
    """ Preprocessing.
    Note that this code should be problem dependend.
    So far, it reads synthetic population files.
    :results vertex_attrs: data (attribute values for each agent)
    :results attr_types:   types of attributes: 'c' -- categorical, 'o' - ordinal,'g' - geographic (latitude/longitude)
    :results attr_names:   names of attributes
    """
    with h5py.File(synpop_file, 'r') as fp:
        vertex_attrs=numpy.array(fp['SPP10pc'].get('ppd'))
        attr_types=numpy.array(fp['SPP10pc'].get('da'))
        attr_names=numpy.array(vertex_attrs.dtype.names)

        # Log info
        if MPI.COMM_WORLD.Get_rank() == 0:
            logging.debug( 'attr_names=[{0}]'.format(','.join(map(str,attr_names))) )
            logging.debug( 'attr_types=[{0}]'.format(','.join(map(str,attr_types))) )
            logging.debug( 'num_agents={0}'.format(vertex_attrs.shape[0]) )

            for attr_name, attr_type in zip(attr_names, attr_types):
                if attr_type == 'c':
                    logging.debug( 'categorie codes for {0}=[{1}]'.format(attr_name, ','.join(map(str,numpy.unique(vertex_attrs[attr_name])))) )
        # exit(-1)
        return vertex_attrs, attr_types, attr_names
    raise InputError('cannot read input file')

# ----------------------------------------------------------------------------------------
#        geographic routines
# ----------------------------------------------------------------------------------------

def GeoDist(lat1, lon1, lat2, lon2):
    """ Calculate the geographical distance between two points.
    """

    # @TODO: convert to radians outside the loop
    lat1 = numpy.radians(lat1)
    lon1 = numpy.radians(lon1)
    lat2 = numpy.radians(lat2)
    lon2 = numpy.radians(lon2)

    dlon = lon1 - lon2

    y = numpy.sqrt((numpy.cos(lat2)*numpy.sin(dlon))**2 + (numpy.cos(lat1)*numpy.sin(lat2) - numpy.sin(lat1)*numpy.cos(lat2)*numpy.cos(dlon))**2)
    x = numpy.sin(lat1)*numpy.sin(lat2) + numpy.cos(lat1)*numpy.cos(lat2)*numpy.cos(dlon)
    c = numpy.arctan2(y, x)
    # @TODO: scale by r_earth outside the loop
    return r_earth*c

def GeoSim(hss_0, pow_law_exp, lat1, lon1, lat2, lon2):
    """ In order to make the Similarity adimensional I have to add a scale to the game.
    This scale is hss, i.e. the scale after which the similairty is damped by a factor 2.

    :param pow_law_exp: is the exponent of the power law
    """
    # @TODO: measure power operator performance vs `math.pow`
    return (float(hss_0)/(hss_0 + GeoDist(lat1, lon1, lat2, lon2)))**pow_law_exp

def GeoExpDamp(hss_0, lat1, lon1, lat2, lon2):
    """Geo-similarity function with exponential damping.

    :param hss_0: works as in the routine before
    """
    # @TODO: measure performance vs math.exp
    return 2**(-GeoDist(lat1, lon1, lat2, lon2)/hss_0)

# ----------------------------------------------------------------------------------------
#        Lin similarity
# ----------------------------------------------------------------------------------------
def Lin_Sim(i, j, non_geo_attr_names, non_geo_attr_types, vertex_attrs, num_total, sampled_vertex_attrs, num_sample):
    """ Compute Lin similarity.
    Lin similarity works on non-geographic attributes.

    Lin similarity handles categorical ('c') and ordinal ('o') attributes
    (while geographic ('g') attributes are subject of geo-damping).
    """
    # In order to reduce calculation time, this routine evaluates
    # the similarity between node i and node j on the sampled matrix sampled_vertex_attrs.

    # Find how many agents share the same attributes as the selected pair of vertices
    similar_nodes=numpy.copy(sampled_vertex_attrs)
    for attr_name, attr_type in zip(non_geo_attr_names, non_geo_attr_types):
        check=vertex_attrs[attr_name][i]-vertex_attrs[attr_name][j]
        if check == 0:
            # select nodes as similar if cardinal attribute values are the same
            similar_nodes=similar_nodes[similar_nodes[attr_name]==vertex_attrs[attr_name][i]]
        else:
            # select nodes as similar if ordinal attribute values are between i and j
            if attr_type == 'o':
                if check > 0:
                    similar_nodes=similar_nodes[vertex_attrs[attr_name][i]>=similar_nodes[attr_name]]
                    similar_nodes=similar_nodes[similar_nodes[attr_name]>=vertex_attrs[attr_name][j]]
                else:
                    similar_nodes=similar_nodes[vertex_attrs[attr_name][j]>=similar_nodes[attr_name]]
                    similar_nodes=similar_nodes[similar_nodes[attr_name]>=vertex_attrs[attr_name][i]]

    # Since attributes are dependent, the only way to handle this thing is
    # to consider the frequence of agents sharing all attributes shared by the two analysed here.
    # If they do not share an attribute and the attribute is ordinal,
    # the number of agents sharing attributes between the two values are considered.
    # Otherwise, if the attribute is a categorical datum, no selection is considered.
    # The idea is that the lowest the number of agents sharing the same attribute,
    # the most information this shared attribute it contains about the two agents.
    # If attributes were independent, I could have had considered attributes independently
    # and then sum different contribution.
    # Since they are not, I have to consider the probability of observing at the same time all different attributes.
    num_similar=len(similar_nodes)
    num_equal_i=sum(sampled_vertex_attrs==vertex_attrs[i])
    num_equal_j=sum(sampled_vertex_attrs==vertex_attrs[j])

    # @TODO: reduce number of log calls, compute log of commonality once
    if num_similar == 0:
        # if the superposition is zero on the sample, then there is not even any agent with the same characteristic of either i or j (is it true?).
        # In this sense, the probability of finding something with the same feature of both i and j
        # is really small on the whole set and thus not jsut they are unlikely but their superposition is too.
        # Think that if they are really different, the probability of their superposition is going to be higher (thus the information carried smaller).
        return 1.
    elif num_equal_i == 0 and num_equal_j != 0:
        # if there is not any agent as i, we can assume that is the only one with this characteristic in the whole set.
        # It is a strong assumption, but it is more conservative:
        # the information carried by her/him is going to be overestimated, thus making the similarity underestimated (in a sense we are limiting false positives).
        # If a is the only one, then numpy.log(num_equal_i_{over the whole set}=1)=0
        return 2.*(-numpy.log2(num_similar)+numpy.log2(num_sample))/(numpy.log2(num_sample)+numpy.log2(num_total)-numpy.log2(num_equal_j))
    elif num_equal_j == 0 and num_equal_i != 0:
        # the same thing for j
        return 2.*(-numpy.log2(num_similar)+numpy.log2(num_sample))/(numpy.log2(num_sample)+numpy.log2(num_total)-numpy.log2(num_equal_i))
    elif num_equal_j == 0 and num_equal_i == 0:
        # the same thing for j
        return (-numpy.log2(num_similar)+numpy.log2(num_sample))/numpy.log2(num_total)
    else:
        return 2.*(-numpy.log2(num_similar)+numpy.log2(num_sample))/(2.*numpy.log2(num_sample)-numpy.log2(num_equal_i)-numpy.log2(num_equal_j))

def Net_ij(i, j, hss_0, damping, non_geo_attr_names, non_geo_attr_types, vertex_attrs, num_vertices, sampled_vertex_attrs, num_sample):
    """ Compute geo-damped Lin similarity.
    The input data are structured.
    """
    # @TODO: Get rid of if-statement
    if damping > 0:
        sim_geo_hh=GeoSim(hss_0, damping, vertex_attrs['hh_lat'][i], vertex_attrs['hh_lon'][i], vertex_attrs['hh_lat'][j], vertex_attrs['hh_lon'][j])
        sim_geo_wp=GeoSim(hss_0, damping, vertex_attrs['wp_lat'][i], vertex_attrs['wp_lon'][i], vertex_attrs['wp_lat'][j], vertex_attrs['wp_lon'][j])
    else:
        sim_geo_hh=GeoExpDamp(hss_0, vertex_attrs['hh_lat'][i], vertex_attrs['hh_lon'][i], vertex_attrs['hh_lat'][j], vertex_attrs['hh_lon'][j])
        sim_geo_wp=GeoExpDamp(hss_0, vertex_attrs['wp_lat'][i], vertex_attrs['wp_lon'][i], vertex_attrs['wp_lat'][j], vertex_attrs['wp_lon'][j])
    # For the moment, it selects the greater between the workplace and the household distance
    sim_geo=max(sim_geo_hh, sim_geo_wp)
    # if the distance is less than a certain threshold, the Lin value is calculated, otherwise it is disregarded
    if sim_geo > GLOBAL_SIM_TH:
        return sim_geo*Lin_Sim(i, j, non_geo_attr_names, non_geo_attr_types, vertex_attrs, num_vertices, sampled_vertex_attrs, num_sample)
    else:
        return 0.

# ----------------------------------------------------------------------------------------
#        the LS4HD class BEGINS
# ----------------------------------------------------------------------------------------
class LS4HD:
    """
    Lin Similarity 4 Heterogeneous Data

    In this code we assume (implicitly) that rows are agents and columns are features,
    such that

    >>> len(description_array)==lc
    True

    :param data:                attribute values
    :param attr_types:          attribute types
    :param attr_names:          type names
    :param hss:                 half-similarity scale
    :param damping:             damping coefficien (if 0 use exponential damping)
    :param chunk_dim:           chunk size
    :param sample_fraction:     percentage of the population
    """
    def __init__(self, o_path, comm, data, attr_types, attr_names, hss=5000, damping=0, chunk_dim=int(1e3), sample_fraction=1e-1):
        self.comm=comm
        self.comm_rank=comm.Get_rank()
        self.comm_size=comm.Get_size()

        if self.comm_rank==0:
            # processor 0 is the root
            logging.info( 'Have a nice day from processor # {0}'.format(self.comm_rank) )
            # sys.stdout.flush()

        self.o_path=o_path

        self.vertex_attrs=data
        self.num_vertices=len(self.vertex_attrs)

        self.attr_types=attr_types
        self.attr_names=attr_names

        # compute indices of geo and non-geo attributes
        non_geo=numpy.where(self.attr_types != 'g')[0]
        geo=numpy.where(self.attr_types == 'g')[0]
        # select non-geo attributes
        self.non_geo_attr_names=self.attr_names[non_geo]
        self.non_geo_attr_types=self.attr_types[non_geo]

        self.chunk_dim=min(int(chunk_dim), self.num_vertices)
        self.damping=damping
        self.hss=hss
        # compute normalization constant (half-similarity scale)
        self.hss_0= float(hss)/(numpy.power(2, self.damping)-1) \
                    if self.damping!=1 and self.damping!=0 else hss

        # ---------------------------------------------------------------------
        # Prepare sample
        # ---------------------------------------------------------------------
        # Prepare representative sample of the original synthetic population
        # in order to reduce time to compute Lin similarity

        # take the sample to be a `sample_fraction` fraction of the original dataset
        self.num_sample=max(100, int(self.num_vertices*sample_fraction))
        if self.num_sample < self.num_vertices:
            if self.comm_rank==0:
                sampled_rows=numpy.random.choice(self.num_vertices, self.num_sample, replace=False)
            else:
                sampled_rows=numpy.empty(self.num_sample, dtype='i') #numpy.int
            # send  the list of the sampled agents to all processors
            self.comm.Bcast([sampled_rows, self.num_sample, MPI.INT], root=0)
            # select sampled rows in sampled_vertex_attrs
            self.sampled_vertex_attrs=self.vertex_attrs[sampled_rows]
        else:
            # Note: no need to make deep copy of vertex_attrs with numpy.copy
            #       since sampled_vertex_attrs is not modified further in algorithm
            self.sampled_vertex_attrs=self.vertex_attrs

        # ---------------------------------------------------------------------
        # Distribute computational work between MPI process
        # ---------------------------------------------------------------------

        start_end=None
        # This is set to None since it is going to be calcualted by the root only and the send in the self.start_end of each processor by root
        self.start_end=numpy.zeros(2, dtype='i8')

        # report total number of nodes and the total number of couples (potential edges)
        num_couples=(self.num_vertices-1)*self.num_vertices/2 # total size of the graph edge probabilities
        logging.info( 'nodes={1}, couples(potential edges)={2} #{0}'.format(self.comm_rank, self.num_vertices, num_couples) )
        # sys.stderr.flush()

        # @TODO: here we estimate the effort taken by process for load balancing
        # efforts are appropriately distributed
        self.effort=int(num_couples // self.comm_size)*numpy.ones(self.comm_size)
        for i in xrange(num_couples % self.comm_size):
            self.effort[i]+=1
        logging.info( 'efforts={1} #{0}'.format(self.comm_rank, self.effort[self.comm_rank]) )
        # sys.stdout.flush()

        # root calculates the efforts per processor and the starting and ending couple
        if self.comm_rank==0:
            start_end=numpy.zeros((self.comm_size, 2), dtype='i8')
            # starting point
            start_end[i, :2]=[0,1]
            for i in xrange(1,self.comm_size):
                start_end[i, 0]=start_end[i-1,0]
                start_end[i, 1]=start_end[i-1,1]+1
                aux=numpy.copy(self.effort[i])
                while aux>0:
                    if aux>self.num_vertices-start_end[i, 1]:
                        aux-=self.num_vertices-start_end[i, 1]
                        start_end[i, 0]+=1
                        start_end[i, 1]=start_end[i, 0]+1
                    else:
                        start_end[i, 1]+=aux-1
                        aux=0
        self.comm.Scatter(start_end, self.start_end, root=0)
        # The previous command gives all process its starting point. It is going to be crucial in the end

        logging.info( 'initialisation ended. Process {0} out of {1}'.format(self.comm_rank, self.comm_size) )
        # sys.stdout.flush()

        self.Sim_master()

    def Sim_master(self):

        with h5py.File( self.o_path, 'w', driver='mpio', comm=self.comm, libver='latest' ) as output_file:
            network_group=output_file.create_group('SimNet')
            adj_list=network_group.create_dataset( 'adj_list', (self.num_vertices*(self.num_vertices-1)/2,),\
                                                   dtype=[('src_node','i8'), ('trg_node','i8'), ('weight','f8')], chunks=True )

            logging.info( 'output file is created. Process {0} out of {1} starts the calculation'.format(self.comm_rank, self.comm_size) )
            # sys.stdout.flush()

            idx_pair=self.start_end[:2]
            # counter=0 # unused
            offset=0

            for i in xrange(self.comm_rank):
                offset+=int(self.effort[i]) # offset in HDF5
            # offset count how many entries in the dataset I have to skip to put data in the right place

            # add a buffer for data.
            edge_buffer=numpy.zeros(self.chunk_dim, dtype=[('src_node','i8'), ('trg_node','i8'), ('weight','f8')])

            start_time=datetime.datetime.now()
            for i in xrange(int(self.effort[self.comm_rank])):
                # when chunk size is reached, the data is copied to file
                idx_in_chunk=i % self.chunk_dim
                edge_probability=Net_ij( int(idx_pair[0]), int(idx_pair[1]), self.hss_0, self.damping, self.non_geo_attr_names, self.non_geo_attr_types,\
                                         self.vertex_attrs, self.num_vertices, self.sampled_vertex_attrs, self.num_sample )
                edge_buffer[idx_in_chunk]=(int(idx_pair[0]), int(idx_pair[1]), edge_probability)

                # Log progress in computing similarity matrix.
                # The ETA is estimated from the calculation time so far.
                if i==0:
                    logging.info( 'Started! # {0}'.format(self.comm_rank) )
                    # sys.stdout.flush()
                elif i==2000:
                    current_elapsed_time=datetime.datetime.now()-start_time
                    # TODO? tpe eta_h/eta_m
                    tpe=float(current_elapsed_time.seconds)/(i+1)
                    # time per evaluation
                    eta_h=int(tpe*(self.effort[self.comm_rank]-i)/3600)
                    eta_m=int(((tpe*(self.effort[self.comm_rank]-i))%3600)/60)
                    logging.info( 'first 2000 couples processed. ETA {0:0>2}:{1:0>2} # {2}'.format(eta_h, eta_m, self.comm_rank) )
                    # sys.stdout.flush()
                elif i % int(self.effort[self.comm_rank]/10)==0:
                    current_elapsed_time=datetime.datetime.now()-start_time
                    tpe=1.*current_elapsed_time.seconds/(i+1)
                    # time per evaluation
                    eta_h=int(tpe*(self.effort[self.comm_rank]-i)/3600)
                    eta_m=int(((tpe*(self.effort[self.comm_rank]-i))%3600)/60)
                    logging.info( '{3}%. ETA {0:0>2}:{1:0>2} # {2}'.format(eta_h, eta_m, self.comm_rank, 10*i/int(self.effort[self.comm_rank]/10)) )

                # checking memory usage
                if psutil.virtual_memory().available <= 104857600: # 100MB
                    #100 MB
                    logging.warning( 'we are running out of memory! # {0}'.format(self.comm_rank) )
                    # sys.stdout.flush()

                # checking swap memory
                if psutil.swap_memory().percent > .9:
                    logging.warning( 'the swap is occupied at the 90%! # {0}'.format(self.comm_rank) )
                    # sys.stdout.flush()

                # it goes to following item in edge probability matrix
                if idx_pair[1] < self.num_vertices-1:
                    idx_pair[1]+=1
                else:
                    idx_pair[0]+=1
                    idx_pair[1]=idx_pair[0]+1

                # if the chunk is full copies it to file
                if idx_in_chunk == self.chunk_dim-1:
                    adj_list[offset:offset+int(self.chunk_dim)]=edge_buffer
                    # it resets the buffer to an empty vector
                    edge_buffer=numpy.zeros(self.chunk_dim, dtype=[('src_node','i8'), ('trg_node','i8'), ('weight','f8')])
                    # it updates the offset. it is necessary for the last saving
                    offset=+int(self.chunk_dim)
                    idx_in_chunk=0
            # the last saving
            adj_list[offset:offset+idx_in_chunk]=edge_buffer[:idx_in_chunk]

        logging.info( 'file closed. # {0}'.format(self.comm_rank) )
        # sys.stdout.flush()


#----------------------------------------------------------------------------------------
#        the LS4HD class ENDS
#----------------------------------------------------------------------------------------
def main():
    # Set up logger
    if True:    # use stdout logger
        log_root=logging.getLogger()
        log_root.setLevel(logging.DEBUG)
        log_channel=logging.StreamHandler(sys.stdout)
        log_channel.setLevel(logging.DEBUG)
        log_channel.setFormatter(logging.Formatter(fmt='%(asctime)s %(message)s', datefmt=':%Y-%m-%d %H:%M:%S'))
        log_root.addHandler(log_channel)
    else:       # use stderr logger
        logging.basicConfig(format='%(asctime)s %(message)s', datefmt=':%Y-%m-%d %H:%M:%S', level=logging.INFO)

    # Handle command line arguments
    args=get_arguments()

    # Prepare input synthetic population
    data, attr_types, attr_names=preprocessing(args.input)

    # Compute similarity network edge probabilities
    start_time=MPI.Wtime()
    LS4HD( os.path.join(args.output,'synthetic_network_hss_{0}_d_{1}.h5'.format(args.hss,args.damping)),
           MPI.COMM_WORLD, hss=args.hss, damping=args.damping, chunk_dim=int(1e3), \
           data=data, attr_types=attr_types, attr_names=attr_names, sample_fraction=args.sample_fraction )
    elapsed_time=MPI.Wtime() - start_time
    logging.info( 'total elapsed time={0}. # {1}'.format(datetime.timedelta(seconds=elapsed_time), MPI.COMM_WORLD.Get_rank()) )

    return 0

if __name__ == "__main__":
    main()
