#    Copyright (C) 2018 by
#    Sergiy Gogolenko <gogolenko@hlrs.de>   HLRS
#    Fabio Saracco    <fabio@imt.it>        IMT
#    All rights reserved.
#
# Authors:      Sergiy Gogolenko <gogolenko@hlrs.de>
#               Fabio Saracco <fabio@imt.it>
"""Base class for similarity networks.
"""
from __future__ import division, absolute_import, print_function

# TODO: switch from logging to warnings in library core
import warnings
import logging

from mpi4py import MPI
import numpy

# NOTE: `math.log` has better performance than `numpy.log` and `numpy.log2`.
#       In our codes we operate with fractions of the logarithms,
#       so log and log2 are interchangeable.
from math import log as log2
from math import sqrt
from math import atan2 as arctan2

class SimilarityGraph:
    """
    Class for probabilistic (undirected) graph model based on Lin similarity
    with geo-spatial damping.

    Args:
        attr_table:          table (or numpy array) with attribute values
        attr_types:          attribute types
        attr_names:          names of the attributes
        comm:                MPI communicator
        hss:                 half-similarity scale
        damping:             damping coefficien (if 0 use exponential damping)
        sample_fraction:     percentage of the population
    """
    R_EARTH=6.3781*10**6    # Earth radius in meters
    def __init__(self, attr_table, attr_types, attr_names=None, comm=MPI.COMM_WORLD, hss=5000, damping=0, sample_fraction=1e-1):
        self.comm=comm
        comm_rank=self.comm.Get_rank()

        num_vertices=len(attr_table)

        self.damping=damping
        self.hss=hss

        self.similarity_threshold=1e-6

        # Normalization constant (half-similarity scale)
        hss_0=float(hss)/(numpy.power(2, self.damping)-1) \
               if 0 < self.damping and self.damping < 1 else hss
        self.geo_scaling=self.R_EARTH/hss_0

        # Group attribute names by types
        if attr_names is None:
            attr_names=attr_table.dtype.names
        attr_names=numpy.array(attr_names)
        attr_types=numpy.array(attr_types)
        attr_name_groups={ attr_type : attr_names[numpy.where(attr_types == attr_type)[0]] \
                           for attr_type in ('g', 'o', 'c') }
        logging.debug( 'attribute names: {0}'.format(attr_name_groups) )

        # Store ordinal attributes as-is
        self.ordinal_attrs=attr_table[attr_name_groups['o']]

        # Convert attributes from degrees to radians
        if len(attr_name_groups['g']) % 2 != 0:
            raise ValueError( "number of geo-attribuets must be odd to hold (longitude,lattitude) pairs,"\
                              " whereas we have {0} geo-attributes".format(len(attr_name_groups['g'])))

        self.geo_attrs=numpy.array( [numpy.radians(attr_table[attr_name]) \
                                     for attr_name in attr_name_groups['g']] ).T
        # logging.debug( 'geo-attributes: [{0}] [shape={1}]'.\
        #                format(",".join(attr_name_groups['g']), self.geo_attrs.shape) )

        # # Merge categorical attributes to a single one
        # # NOTE: this conversion code assumes that all values of categorical variables are numeric 
        # self._categories={ attr_name : (attr_table[attr_name].min(), attr_table[attr_name].max()) \
        #                    for attr_name in attr_name_groups['c'] }
        # self.categorical_attr=numpy.zeros(len(attr_table))
        # shift=0
        # for attr_name, minmax in self._categories.items():
        #     attr_min, attr_max=minmax

        #     self.categorical_attr*=shift
        #     self.categorical_attr+=attr_table[attr_name]-attr_min

        #     shift=attr_max-attr_min+1
        self.categorical_attrs=attr_table[attr_name_groups['c']]

        # Prepare representative sample of the original synthetic population
        # in order to reduce time to compute Lin similarity.
        # Take the sample to be a `sample_fraction` fraction of the original dataset.
        sample_size=max(100, int(num_vertices*sample_fraction))
        if sample_size < num_vertices:
            if comm_rank==0:
                sampled_indices=numpy.random.choice(num_vertices, sample_size, replace=False)
            else:
                sampled_indices=numpy.empty(sample_size, dtype='i') #numpy.int
            # Broadcast the list of the sampled agents between all processes.
            self.comm.Bcast([sampled_indices, sample_size, MPI.INT], root=0)
            # Select sampled attributes
            self.sampled_categorical_attrs=self.categorical_attrs[sampled_indices]
            self.sampled_ordinal_attrs=self.ordinal_attrs[sampled_indices]
            self.sampled_geo_attrs=self.geo_attrs[sampled_indices]
            self.sample_mask=numpy.zeros(num_vertices, bool)
            self.sample_mask[sampled_indices]=True
        else:  # Since population size is small, use the whole population as sample
            # NOTE: no need to make deep copy of vertex_attrs with numpy.copy
            #       since sampled_vertex_attrs is not modified further in algorithm
            self.sampled_categorical_attrs=self.categorical_attrs
            self.sampled_ordinal_attrs=self.ordinal_attrs
            self.sampled_geo_attrs=self.geo_attrs
            self.sample_mask=numpy.ones(num_vertices, bool)

        self.sampled_categorical_attrs=[self.sampled_categorical_attrs[attr_name] \
                                        for attr_name in attr_name_groups['c']]
        self.sampled_ordinal_attrs=[self.sampled_ordinal_attrs[attr_name] \
                                    for attr_name in attr_name_groups['o']]

        # TODO: remove when not needed
        self.sampled_vertex_attrs=attr_table[self.sample_mask]
        self.vertex_attrs=attr_table

    @property
    def sample_size(self):
        return len(self.sampled_geo_attrs)

    def edge_probability(self, a, b):
        """ Probability of edge in the similarity graph based on geo-damped Lin similarity.

        Edge probability consistes of two independent contributions:
        - probability induced by graphical distance between agents
        - probability induced by similarity between agents
        """

        # Compute contribution of geo-attributes to the edge probability.

        # Get vectors with (lon,lat)-pairs of all locations for 2 nodes.
        geo_attrs_a=self.geo_attrs[a]
        geo_attrs_b=self.geo_attrs[b]
        # Compute minimum geo-distance between locations of a and b
        # NOTE: For the moment, it selects the closest distance for 
        #       matching types of locations (e.g., between 2 households,
        #       but not between household of `a` and workplace of `b`)
        min_dist=numpy.PINF
        for i in xrange(0, len(geo_attrs_a), 2):
            dlon=geo_attrs_a[i] - geo_attrs_b[i]
            # TODO: precompute sines and cosines before computing individual edge probabilities
            lat1, lat2=geo_attrs_a[i+1], geo_attrs_b[i+1]
            cos_lat1, cos_lat2, cos_dlon=numpy.cos(lat1), numpy.cos(lat2), numpy.cos(dlon)
            sin_lat1, sin_lat2, sin_dlon=numpy.sin(lat1), numpy.sin(lat2), numpy.sin(dlon)
            y=sqrt((cos_lat2*sin_dlon)**2 + (cos_lat1*sin_lat2 - sin_lat1*cos_lat2*cos_dlon)**2)
            x=sin_lat1*sin_lat2 + cos_lat1*cos_lat2*cos_dlon
            # TODO: clarify about negative distances
            min_dist=min(min_dist, arctan2(y, x))

        if self.damping > 0.:
            # Scale distance by half-similarity scale to make it adimensional and damp by a factor 2.
            prob_geo=(1. + self.geo_scaling*min_dist)**(-self.damping)
        else:
            # Compute geo-similarity with exponential damping.
            prob_geo=2**(-self.geo_scaling*min_dist)
        # logging.debug( "minimum distance rho({0},{1})={2}; geo-induced probability Pr({0},{1})={3}".\
        #                format(a, b, min_dist, prob_geo) )

        # If probability induced by the geo-attributes is smaller than a certain lower bound threshold,
        # the Lin similarity contribution is disregarded.
        if prob_geo <= self.similarity_threshold:
            return 0.

        # Compute contribution of non-geographic attributes to the edge probability.
        # This contribution is based on Lin similarity metric.
        # Lin similarity handles categorical ('c') and ordinal ('o') attributes
        # (while geographic ('g') attributes are subject of geo-damping).
        # In order to reduce calculation time, code below evaluates
        # the similarity between node `a` and node `b` on the sampled attributes.

        # First, find the frequency of agents sharing all attributes shared by the two analysed nodes.
        # The idea is that the lower the number of agents sharing the same attribute,
        # the more information this shared attribute contains about the two agents.
        # Since attributes are dependent, one must estimete the probability (get frequency)
        # of observing all different attributes at the same time. If they were independent,
        # one might handle attributes independently by computing their contributions separately
        # and suming up.

        # if self.categorical_attr[a] == self.categorical_attr[b]:
        #     similar_nodes=self.sampled_ordinal_attrs[self.categorical_attr[a] == self.sampled_ordinal_attrs]
        # else:
        #     similar_nodes=self.sampled_ordinal_attrs

        # Select nodes as similar if cardinal attributes are the same to `a` and `b`
        # If vertices share cardinal attribute, the number of agents sharing this attribute is considered.
        # TODO: ensure that we do not have to cut of by categorical_attrs
        attrs_a, attrs_b = self.categorical_attrs[a], self.categorical_attrs[b]
        similar_nodes=True  # start with all sampled items as similar
        for sample, attr_a, attr_b in zip(self.sampled_categorical_attrs, attrs_a, attrs_b):
            if attr_a == attr_b:
                # filter out indices of samples with the same attribute
                similar_nodes &= sample == attr_a
        # logging.debug( "similar categorical attributes in the sample: {0} out of {1}".\
        #                format(numpy.sum(similar_nodes) if not isinstance(similar_nodes, bool) else "all",
        #                       self.sample_size) )

        # Select nodes as similar if ordinal attributes are between values for `a` and `b`.
        # If vertices do not share an attribute and the attribute is ordinal,
        # the number of agents sharing attributes between the two values is considered.
        attrs_a, attrs_b=self.ordinal_attrs[a], self.ordinal_attrs[b]
        for sample, attr_a, attr_b in zip(self.sampled_ordinal_attrs, attrs_a, attrs_b):
            attr_min, attr_max=min(attr_a, attr_b), max(attr_a, attr_b)
            # filter out indices of samples with the attribute in the range of values between `a` and `b`
            similar_nodes &= (attr_min <= sample) & (sample <= attr_max)

        num_similar=numpy.sum(similar_nodes) if not isinstance(similar_nodes, bool) else self.sample_size
        # logging.debug( "similar attributes in the sample after ordinal attributes filtering: {0} out of {1}".\
        #                format(num_similar, self.sample_size) )

        # If the superposition is zero on the sample, then there is no agents with the same characteristics.
        # The probability of finding something with the same feature of both `a` and `b` is really small.
        if num_similar == 0:
            return prob_geo # TODO: consult why not zero

        # Second, find the frequency of agents sharing all attributes with each analysed node separately.
        # TODO: clarify whether we need to take geo-filtering into account as in original script
        # NOTE: `numpy.sum` performs better than `sum` on numpy-arrays
        num_equal_a=numpy.sum(self.sampled_vertex_attrs==self.vertex_attrs[a])
        num_equal_b=numpy.sum(self.sampled_vertex_attrs==self.vertex_attrs[b])
        # logging.debug( "similar attributes (in the sample) to the 1st vertex: {0}, to the 2nd vertex: {1}".\
        #                format(num_equal_a, num_equal_b) )

        # Compute Lin similarity (use inverses of frequencies estimated above)
        num_sample=float(self.sample_size)
        num_total=len(self)
        prob_lin=log2(num_sample/num_similar)
        if num_equal_a == 0:  # there is no agents as `a`
            # We make assumption that `a` is the only one with this characteristic in the whole dataset.
            if num_equal_b == 0:  # the same thing for `b`
                prob_lin /= log2(num_total)
            else:  # `a` is unique, but `b` has similar vertices (agents) in the dataset (population)
                prob_lin /= 0.5*log2(num_sample*num_total/num_equal_b)
        elif num_equal_b == 0: # `b` is unique, but `a` has similar vertices (agents) in the dataset (population)
            prob_lin /= (log2(num_sample*num_total/num_equal_a))
        else:  # both `a` and `b` have similar vertices (agents) in the dataset (population)
            prob_lin /= log2(num_sample*num_sample/(num_equal_a*num_equal_b))

        return prob_geo*prob_lin

    def edges_probabilities(self):
        """Iterator over upper triangular part of the edge "probability" matrix.

        Returns
        -------
        edges : 
            Edge iterator, which iterates over (u, v, p) tuples of edges,
            where p is a probability of edge.
        Notes
        -----
        Do not conucse this upper triangular matrix with upper triangular part of 
        a graph probability matrix where each element (i,j) corresponds to probability
        of edge existance. In our matrix, edge probabilities are not normalized.
        Examples
        --------
        >>> [(i,j,p) for i,j,p in G.edges_probabilities()]
        """
        # TODO: replace `edges_probabilities` with edge view

        comm_rank=self.comm.Get_rank()
        comm_size=self.comm.Get_size()

        # Estimate number of potential edges (couples)
        num_vertices=len(self)
        num_couples=int((num_vertices - 1)*num_vertices/2)  # total number of couples (potential edges) in the graph.
        def pos2ij(pos):
            """Convert position in an upper triangular matrix to a pair of indices (i,j)."""
            i=int(num_vertices - sqrt((num_vertices-.5)**2 - 2.*pos) - 0.5) # take floor with `int`
            j=int(pos + i*(i + 1)/2 - i*(num_vertices - 1) + 1)
            return i,j
        def ij2pos(i,j):
            """Convert pair of indices (i,j) to a position in an upper triangular matrix."""
            return int(i*num_vertices - i*(i + 3)/2 + j)

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
            ie,je = (num_vertices - 1, num_vertices) if comm_rank + 1 == comm_size else \
                    pos2ij(couples_per_process*(comm_rank + 1) + couples_remainder)
        logging.info( 'Iterate over couples between {0} and {1}, number of couples {2}'.\
                      format((i0,j0), (ie,je), ij2pos(ie,je)-ij2pos(i0,j0)) )

        # Iterate over couples
        i, j = i0, j0
        while i!=ie or j!=je:
            yield i, j, self.edge_probability(i,j)

            j+=1
            if j == num_vertices:  # move to the next row
                i+=1
                j=i+1

    def __len__(self):
        """Return the number of nodes. Use: `len(G)`.

        Returns:
            The number of nodes in the graph.

        Examples
        --------
        >>> len(sim_net)
        """
        return len(self.vertex_attrs)
