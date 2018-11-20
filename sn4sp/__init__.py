#    Copyright (C) 2018 by
#    Sergiy Gogolenko <gogolenko@hlrs.de>   HLRS
#    Fabio Saracco    <fabio@imt.it>        IMT
#    All rights reserved.
#
# Authors:      Sergiy Gogolenko <gogolenko@hlrs.de>
#               Fabio Saracco <fabio@imt.it>
"""
SN4SP
=====

This package implements classes fro reconstructing synthetic networks from limited data
about agent (node) attributes.

Provides:
  1. a similarity network object which partially reproduce interface of `networkX` graphs
  2. functions to load synthetic population and store similarity graph in HDF5 format
  3. ability to synthetize networks on parallel and distributed facilities with MPI.

"""
from __future__ import division, absolute_import, print_function

import sys
# TODO: switch from logging to warnings in library core
import warnings

from .version import vcs_revision as __vcs_revision__
from .version import version as __version__

__all__ = []

from . import core
from . import parallel
from . import readwrite

# # Make these accessible from sn4py namespace
# # but not imported in from sn4py import *
# if sys.version_info[0] >= 3:  # TODO: Use when implement full Pyhton3 support
#     from builtins import bool, int, float, complex, object, str
#     unicode = str
# else:
#     from __builtin__ import bool, int, float, complex, object, unicode, str

__all__.extend(['__version__',])
__all__.extend(core.__all__)
__all__.extend(['readwrite', 'parallel'])

# def _sanity_check():
#     """
#     Quick sanity checks (implement if needed it).
#     """
#     try:
#         G = SimilarityGraph(...)
#         if not ...:
#             raise AssertionError()
#         except AssertionError:
#             raise RuntimeError( "The current SN4SP installation ({!r}) fails to pass simple sanity checks."\
#                                 .format(__file__) )

# _sanity_check()
# del _sanity_check
