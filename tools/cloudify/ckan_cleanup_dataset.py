#!/usr/bin/env python

############################################################
## @file
## @copyright (C) 2018
##    High Performance Computing Center Stuttgart (HLRS)
##    http://www.hlrs.de
##    All rights reserved.
##
## Use, modification, and distribution is subject to the HLRS License.
##
## @author Sergiy Gogolenko <gogolenko@hlrs.de>
##
## Upload resources to CKAN providing metadata
############################################################

import os
import sys
import argparse
import requests

default_datacatalogue_entrypoint = 'https://coegss1.man.poznan.pl'

default_dataset_name = 'synthetic-network-example'

extra_args = {}

def main():

    parser = argparse.ArgumentParser(description="Upload resources to CKAN providing metadata")
    parser.add_argument("skip", metavar="RESOURCE_NAMES", type=str, nargs='*',
                        help="names of resources to skip when make dataset clean up",
                        default=[])
    parser.add_argument("-ip",
                        "--datacatalogue-entrypoint",
                        dest="datacatalogue_entrypoint",
                        help="Datacatalogue entrypoint",
                        default=default_datacatalogue_entrypoint)
    parser.add_argument("-k",
                        "--datacatalogue-key",
                        dest="datacatalogue_key",
                        help="Datacatalogue key",
                        default=None)
    parser.add_argument("-d",
                        "--dataset-name",
                        dest="dataset_name",
                        help="Dataset name",
                        default=default_dataset_name)
    args = parser.parse_args()

    if args.datacatalogue_key is not None:
        extra_args['headers'] = {'Authorization': args.datacatalogue_key}

    # Get dataset resources list
    response = requests.get( r'{0}/api/rest/dataset/{1}'.format(args.datacatalogue_entrypoint, args.dataset_name),
                             **extra_args )
    assert response.status_code == requests.codes.ok

    for resource in response.json()['resources']:
        if resource['name'] not in args.skip:
            print( '-- remove resource id="{0}" "{1}"'.format(resource['id'], resource['name']) )
            assert requests.codes.ok == \
                requests.post( '{0}/api/action/resource_delete'.format(args.datacatalogue_entrypoint),
                               data={'id': resource['id'], 'package_id': args.dataset_name}, **extra_args )
        
if __name__ == "__main__":
    main()
