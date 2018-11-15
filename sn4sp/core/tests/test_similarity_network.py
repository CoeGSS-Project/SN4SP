#! /usr/bin/env python
# -*- coding: utf-8 -*-

#    Copyright (C) 2018 by
#    Sergiy Gogolenko <gogolenko@hlrs.de>   HLRS
#    Fabio Saracco    <fabio@imt.it>        IMT
#    All rights reserved.
#
# Authors:      Sergiy Gogolenko <gogolenko@hlrs.de>
#               Fabio Saracco <fabio@imt.it>
""" Unit tests for SimilarityGraph
"""

from __future__ import division, absolute_import, print_function
import unittest
import numpy

# TODO: remove in alpha release
import os
import sys
sys.path.insert( 0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(sys.argv[0]))))) )
from sn4sp.core import SimilarityGraph

class TestStringMethods(unittest.TestCase):
    """ Tests for data-structure SimilarityGraph."""

    def setUp(self):
        dt = numpy.dtype({
            'names'   : ["sex", "age", "role", "edu", "employed", "income",
                         "wp_lon", "wp_lat", "hh_lon", "hh_lat", "wp_hh"],
            'formats' : [numpy.bool, numpy.int8, numpy.int8, numpy.int8, numpy.int8, numpy.int16,
                         numpy.float32, numpy.float32, numpy.float32, numpy.float32, numpy.int8]
        })

        vertex_attrs=numpy.array( [
            (1, 75, 1, 0, -1, 15, 45.0723, 7.6859, 45.0723, 7.6859, 0),
            (0, 42, 1, 1, 10, 31, 45.0539, 7.6613, 45.0661, 7.6964, 3),
            (1, 57, 1, 1, 10, 28, 45.0661, 7.6887, 45.0661, 7.6964, 1),
            (1, 15, 0, 1,  2,  0, 45.0392, 7.7168, 45.0661, 7.6964, 3),
            (0,  0, 0, 0,  0,  0, 45.0661, 7.6964, 45.0661, 7.6964, 0),
            (1, 13, 0, 0,  2,  0, 45.0385, 7.7023, 45.0661, 7.6964, 3),
            (1, 21, 1, 2, -1,  0, 45.0558, 7.6605, 45.0558, 7.6605, 0),
            (1, 64, 1, 0, -1,  0, 45.0679, 7.6640, 45.0679, 7.6640, 0),
            (0, 62, 1, 1, 10, 28, 45.0530, 7.7068, 45.0679, 7.6640, 4),
            (0, 64, 1, 1, 10, 32, 45.0317, 7.6323, 45.0636, 7.6971, 6),
        ], dtype=dt )

        self.sim_net = SimilarityGraph( vertex_attrs, list("cocccoggggo"),
                                        hss=5000, damping=0., sample_fraction=1.0)

    def tearDown(self):
        del self.sim_net

    @unittest.skip("must be fixed in the next version of lib")
    def test_self_similarity(self):
        self.assertEqual(self.sim_net.edge_probability(0,0), 1.)

    def test_similarity(self):
        self.assertTrue(self.sim_net.edge_probability(0,1) <= 1.)

    def test_num_items_per_process(self):
        n=0
        for edge in self.sim_net.edges_probabilities(): n+=1
        self.assertTrue(n > 0)

    def test_similarity(self):
        for i, j, p in self.sim_net.edges_probabilities():
            self.assertTrue(p <= 1.)

if __name__ == '__main__':
    unittest.main()
