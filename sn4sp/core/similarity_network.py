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

from sn4sp import parallel

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
from itertools import islice
from itertools import islice
import sys
if sys.version_info[0] >= 3:
    izip=zip
else:
    from itertools import izip

class SimilarityGraph:
    """
    Class for probabilistic (undirected) graph model based on Lin similarity
    with geo-spatial damping.

    Parameters
    ----------
    attr_table : numpy.array or pandas.table
        Table (or numpy array) with attribute values
    attr_types : list
        Attribute types
    attr_names : list
        Names of the attributes
    comm : mpi4py.MPI.Intracomm object
        MPI communicator
    hss : float
        Half-similarity scale
    damping : float
        Damping coefficient (if 0 use exponential damping)
    sample_fraction : float
        Percentage of the population
    """
    R_EARTH=6.3781*10**6    # Earth radius in meters
    def __init__(self, attr_table, attr_types, attr_names=None, comm=MPI.COMM_WORLD, hss=5000, damping=0, sample_fraction=1e-1):
        """
        Initialize a probabilistic (undirected) graph model based on Lin similarity
        with geo-spatial damping.

        Parameters
        ----------
        attr_table : numpy.array or pandas.table
            Table (or numpy array) with attribute values
        attr_types : list
            Attribute types
        attr_names : list
            Names of the attributes
        comm : mpi4py.MPI_Comm
            MPI communicator
        hss : float
            Half-similarity scale
        damping : float
            Damping coefficient (if 0 use exponential damping)
        sample_fraction : float
            Percentage of the population
        """
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
        attr_names=numpy.array(attr_names or attr_table.dtype.names)
        attr_types=numpy.array(attr_types)
        attr_name_groups={ attr_type : attr_names[numpy.where(attr_types == attr_type)[0]] \
                           for attr_type in ('g', 'o', 'c') }
        logging.debug( 'attribute names: {0}'.format(attr_name_groups) )

        # Store categorical and ordinal attributes as-is
        nongeo_attr_names=numpy.hstack((attr_name_groups['c'], attr_name_groups['o']))
        self.num_categorical=len(attr_name_groups['c'])
        self.num_ordinal=len(attr_name_groups['o'])
        self.nongeo_attrs=attr_table[nongeo_attr_names]

        # Convert attributes from degrees to radians
        if len(attr_name_groups['g']) % 2 != 0:
            raise ValueError( "number of geo-attributes must be odd to hold (longitude,latitude) pairs,"\
                              " whereas we have {0} geo-attributes".format(len(attr_name_groups['g'])) )

        self.geo_attrs=numpy.array( [numpy.radians(attr_table[attr_name]) \
                                     for attr_name in attr_name_groups['g']] ).T
        # logging.debug( 'geo-attributes: [{0}] [shape={1}]'.\
        #                format(",".join(attr_name_groups['g']), self.geo_attrs.shape) )

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
            self.sampled_nongeo_attrs=self.nongeo_attrs[sampled_indices]
            self.sampled_geo_attrs=self.geo_attrs[sampled_indices]
            self.sample_mask=numpy.zeros(num_vertices, bool)
            self.sample_mask[sampled_indices]=True
        else:  # Since population size is small, use the whole population as sample
            # NOTE: no need to make deep copy of vertex_attrs with numpy.copy
            #       since sampled_vertex_attrs is not modified further in algorithm
            self.sampled_nongeo_attrs=self.nongeo_attrs
            self.sampled_geo_attrs=self.geo_attrs
            self.sample_mask=numpy.ones(num_vertices, bool)

        self.sampled_nongeo_attrs=[self.sampled_nongeo_attrs[attr_name] \
                                   for attr_name in nongeo_attr_names]

        # TODO: remove when not needed
        self.sampled_vertex_attrs=attr_table[self.sample_mask]
        self.vertex_attrs=attr_table

    @property
    def sample_size(self):
        return len(self.sampled_geo_attrs)

    def edge_probability(self, u, v):
        """ Probability of edge in the similarity graph based on geo-damped Lin similarity.

        Edge probability consists of two independent contributions:
        - probability induced by graphical distance between agents
        - probability induced by similarity between agents

        Parameters
        ----------
        u, v : int
            Indices of vertices
        """

        # Compute contribution of geo-attributes to the edge probability.

        # Get vectors with (lon,lat)-pairs of all locations for 2 nodes.
        geo_attrs_u=self.geo_attrs[u]
        geo_attrs_v=self.geo_attrs[v]
        # Compute minimum geo-distance between locations of a and b
        # NOTE: For the moment, it selects the closest distance for 
        #       matching types of locations (e.g., between 2 households,
        #       but not between household of `a` and workplace of `b`)
        min_dist=numpy.PINF
        for i in xrange(0, len(geo_attrs_u), 2):
            dlon=geo_attrs_u[i] - geo_attrs_v[i]
            # TODO: precompute sines and cosines before computing individual edge probabilities
            lat1, lat2=geo_attrs_u[i+1], geo_attrs_v[i+1]
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
        # Since attributes are dependent, one must estimate the probability (get frequency)
        # of observing all different attributes at the same time. If they were independent,
        # one might handle attributes independently by computing their contributions separately
        # and summing up.

        attrs_u, attrs_v = self.nongeo_attrs[u], self.nongeo_attrs[v]
        # Select nodes as similar if categorical attributes are the same to `a` and `b`
        # If vertices share categorical attribute, the number of agents sharing this attribute is considered.
        # TODO: ensure that we do not have to cut of by categorical_attrs
        similar_nodes=True  # start with all sampled items as similar
        for sample, attr_u, attr_v in islice(izip(self.sampled_nongeo_attrs, attrs_u, attrs_v), self.num_categorical):
            if attr_u == attr_v:
                # filter out indices of samples with the same attribute
                similar_nodes &= sample == attr_u
        # logging.debug( "similar categorical attributes in the sample: {0} out of {1}".\
        #                format(numpy.sum(similar_nodes) if not isinstance(similar_nodes, bool) else "all",
        #                       self.sample_size) )

        # Select nodes as similar if ordinal attributes are between values for `a` and `b`.
        # If vertices do not share an attribute and the attribute is ordinal,
        # the number of agents sharing attributes between the two values is considered.
        for sample, attr_u, attr_v in islice(izip(self.sampled_nongeo_attrs, attrs_u, attrs_v), self.num_categorical, self.num_categorical+self.num_ordinal):
            attr_min, attr_max=min(attr_u, attr_v), max(attr_u, attr_v)
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
        num_equal_u=numpy.sum(self.sampled_vertex_attrs==self.vertex_attrs[u])
        num_equal_v=numpy.sum(self.sampled_vertex_attrs==self.vertex_attrs[v])
        # logging.debug( "similar attributes (in the sample) to the 1st vertex: {0}, to the 2nd vertex: {1}".\
        #                format(num_equal_u, num_equal_v) )

        # Compute Lin similarity (use inverses of frequencies estimated above)
        num_sample=float(self.sample_size)
        num_total=len(self)
        prob_lin=log2(num_sample/num_similar)
        if num_equal_u == 0:  # there is no agents as `a`
            # We make assumption that `a` is the only one with this characteristic in the whole dataset.
            if num_equal_v == 0:  # the same thing for `b`
                prob_lin /= log2(num_total)
            else:  # `a` is unique, but `b` has similar vertices (agents) in the dataset (population)
                prob_lin /= 0.5*log2(num_sample*num_total/num_equal_v)
        elif num_equal_v == 0: # `b` is unique, but `a` has similar vertices (agents) in the dataset (population)
            prob_lin /= (log2(num_sample*num_total/num_equal_u))
        else:  # both `a` and `b` have similar vertices (agents) in the dataset (population)
            prob_lin /= log2(num_sample*num_sample/(num_equal_u*num_equal_v))

        return prob_geo*prob_lin

    def edges_probabilities(self, *args, **kwargs):
        """Iterator over upper triangular part of the edge "probability" matrix.

        Returns
        -------
        edges : iterator
            Edge iterator, which iterates over (u, v, p) tuples of edges,
            where p is a probability of edge.

        Notes
        -----
        Do not confuse this upper triangular matrix with upper triangular part of 
        a graph probability matrix where each element (i,j) corresponds to probability
        of edge existence. In our matrix, edge probabilities are not normalized.

        Examples
        --------
        >>> [(i,j,p) for i,j,p in G.edges_probabilities()]

        """
        # TODO: replace `edges_probabilities` with edge view

        # Estimate number of potential edges (couples)
        for i, j in parallel.triu_index(len(self), self.comm, *args, **kwargs):
            yield i, j, self.edge_probability(i,j)

    def __len__(self):
        """ Return the number of nodes. Use: `len(G)`.

        Returns
        -------
        length : int
            The number of nodes in the graph.

        Examples
        --------
        >>> len(sim_net)
        """
        return len(self.vertex_attrs)
