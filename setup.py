#!/usr/bin/env python
""" SN4SP is the package for reconstructing synthetic networks from limited data about agent (node) attributes with Python.

It provides:
- a similarity network object which partially reproduce interface of `networkX` graphs
- functions to load synthetic population and store similarity graph in HDF5 format
- ability to synthetize networks on parallel and distributed facilities with MPI.
"""
from __future__ import division, absolute_import, print_function

SN4SP_DOCLINES = (__doc__ or '').split("\n")

import os
import sys
import subprocess


# Check Python version
if sys.version_info[:2] < (2, 7) or sys.version_info[0] >= 3:
    # import warnings
    # warnings.warn( "Current release of SN4SP requires Python 2.7+, but NOT Python 3+ ({}.{} detected).".\
    #                format(*sys.version_info[:2]) )
    # sys.exit(-1)
    raise RuntimeError( "Current release of SN4SP requires Python 2.7+, but NOT Python 3+ ({}.{} detected).".\
                        format(*sys.version_info[:2]) )

SN4SP_VERSION_MAJOR = 0
SN4SP_VERSION_MINOR = 1
SN4SP_VERSION_PATCH = 3
SN4SP_VERSION       = '{}.{}.{}'.format(SN4SP_VERSION_MAJOR, SN4SP_VERSION_MINOR, SN4SP_VERSION_PATCH)
SN4SP_ISRELEASED    = False

SN4SP_LICENSE = None # TODO
SN4SP_AUTHORS = { 'Sergiy': ('Sergiy Gogolenko', 'gogolenko@hlrs.de'),
                  'Fabio' : ('Fabio Saracco', 'fabio@imt.it'), }
SN4SP_MAINTAINER = "SN4SP Developers"
SN4SP_MAINTAINER_EMAIL = "gogolenko@hlrs.de"
SN4SP_URL = None # TODO
SN4SP_DOWNLOAD_URL = None # TODO
SN4SP_PLATFORMS = ['Linux', 'Mac OSX', 'Windows', 'Unix']
SN4SP_KEYWORDS = ['Networks', 'Graph Theory', 'Network Sampling', 'Complex Systems',
                  'Synthetic Networks', 'Probabilistic Graph Models',
                  'Social Sciences', 'Systems Sciences', 'math']
SN4SP_CLASSIFIERS = """\
Development Status :: 2 - Pre-Alpha
Intended Audience :: Science/Research
Intended Audience :: Developers
License :: TODO
Programming Language :: C
Programming Language :: Python
Programming Language :: Python :: 2
Programming Language :: Python :: 2.7
Programming Language :: Python :: Implementation :: CPython
Topic :: Software Development
Topic :: Scientific/Engineering
Operating System :: Microsoft :: Windows
Operating System :: POSIX
Operating System :: Unix
Operating System :: MacOS
"""

# BEFORE importing setuptools, remove MANIFEST.
if os.path.exists('MANIFEST'):
    os.remove('MANIFEST')

def get_version_info():
    """ Appends VCS revision number to version string.
    Revision is obtained dynamically. Only Git is supported.
    This function is used when generate `version.py`.
    """
    full_version = SN4SP_VERSION
    if not SN4SP_ISRELEASED:
        git_revision = "Unknown"
        if os.path.exists('.git'):
            # try to get git revision from git itself
            try:
                env = {}
                for k in ('SYSTEMROOT', 'PATH', 'HOME'):
                    v = os.environ.get(k)
                    if v is not None:
                        env[k] = v
                env['LANGUAGE'] = 'C'
                env['LANG'] = 'C'
                env['LC_ALL'] = 'C'
                cmd_out = subprocess.Popen( ['git', 'rev-parse', 'HEAD'],
                                            stdout=subprocess.PIPE, env=env).communicate()[0]
                git_revision = cmd_out.strip().decode('ascii')
            except OSError:
                pass
        elif os.path.exists('sn4sp/version.py'):
            # look up in version file from source distribution
            try:
                from sn4sp.version import vcs_revision as git_revision
            except ImportError:
                pass

        full_version += '.dev0+' + git_revision[:7]

    return full_version, git_revision


def write_version_py(filename='sn4sp/version.py'):
    """ Generate `version.py`. """
    content_fmt = """\
############################################################
# THIS FILE IS GENERATED FROM SN4SP SETUP.PY
# DO NOT ADD THIS FILE TO THE REPOSITORY.
############################################################
short_version = '{version}'
version = '{version}'
full_version = '{full_version}'
vcs_revision = '{git_revision}'
release = {isrelease}
if not release:
    version = full_version
"""
    SN4SP_FULL_VERSION, SN4SP_GIT_REVISION = get_version_info()

    a = open(filename, 'w')
    try:
        a.write( content_fmt.format( version=SN4SP_VERSION,
                                     full_version=SN4SP_FULL_VERSION,
                                     git_revision=SN4SP_GIT_REVISION,
                                     isrelease=str(SN4SP_ISRELEASED)) )
    finally:
        a.close()

# TODO: Cythonize sources for performance

def check_setuppy_arguments():
    """ Check the commands and respond appropriately. """
    # import textwrap
    # TODO: detail this function
    args = sys.argv[1:]

    if sys.argv[-1] == 'setup.py':
        import warnings
        warnings.warn("To install, run 'python setup.py install'")
        return False

    if not args:
        # User forgot to give an argument probably, let setuptools handle that.
        return False
    return True

def setup_package():

    # Fix system paths
    src_path = os.path.dirname( os.path.abspath(sys.argv[0]) )
    old_path = os.getcwd()
    os.chdir(src_path)
    sys.path.insert(0, src_path)

    # Rewrite the version file
    write_version_py()

    packages = ["sn4sp",
                "sn4sp.readwrite"]
    data = [] # TODO: specify
    package_data = {} # TODO: specify

    # from distutils.command.sdist import sdist
    # TODO: Use distutils
    setup_settings = dict(
        name = 'sn4sp',
        version = get_version_info()[0],
        maintainer = SN4SP_MAINTAINER,
        maintainer_email = SN4SP_MAINTAINER_EMAIL,
        description = SN4SP_DOCLINES[0],
        long_description = "\n".join(SN4SP_DOCLINES[2:]),
        keywords=SN4SP_KEYWORDS,
        url = SN4SP_URL,
        author = ', '.join(_author[0] for _author in SN4SP_AUTHORS),
        author_email = SN4SP_AUTHORS['Sergiy'][1],
        download_url = SN4SP_DOWNLOAD_URL,
        license = SN4SP_LICENSE,
        classifiers=[_cfr for _cfr in SN4SP_CLASSIFIERS.split('\n') if _cfr],
        platforms = ["Linux", "Unix", "Mac OS-X", "Windows",],
        packages = packages,
        data_files = data,
        package_data = package_data,
        install_requires = ["mpi4py", "numpy"],
        extras_require = {
            "all"     : ["argparse", "h5py", "logging", "psutil"],
            "hdf5"    : ["h5py"],
            "utils"   : ["argparse", "h5py", "logging"],
            "logging" : ["logging", "psutil"],
        },
        # test_suite='nose.collector',
        # cmdclass={"sdist": sdist},
        python_requires='>=2.7,!=3.*',
        zip_safe=False,
    )

    # Raise errors for unsupported commands, improve help output, etc.
    check_setuppy_arguments()

    from setuptools import setup
    # from sn4sp.distutils.core import setup
    try:
        setup(**setup_settings)
    finally:
        del sys.path[0]
        os.chdir(old_path)

if __name__ == '__main__':
    setup_package()
