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
import json
import requests

default_datacatalogue_entrypoint = 'https://coegss1.man.poznan.pl'

default_dataset_name = 'synthetic-network-example'
file_records = [
    [
        "synthPop_Piedmont_10pc_2011.h5",
        {
            "name" : "Synthetic population",
            "description" : "Synthetic population of Piedmont, Italy" }
        ],
    [
        "Piemonte_NUTS3_to_LAU2_gdf.pkl.gz",
        {
            "name" : "Geodata",
            "description" : "GZipped PKL file with serialized geodata" }
        ]
    ]

extra_args = {}

def main():

    parser = argparse.ArgumentParser(description="Upload resources to CKAN providing metadata")
    parser.add_argument("json", metavar="JSON", type=argparse.FileType('r'), nargs='?',
                        help="json file with list of files to upload and metadata",
                        default=sys.stdin)
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
    parser.add_argument("-c",
                        "--create",
                        dest="create",
                        type=bool,
                        help="Create new resources even if dataset contains resources with the same names",
                        default=None)
    args = parser.parse_args()

    file_records = json.load(args.json)

    # Creating a dataset if it does not exist yet
    if False:
        dataset_dict = {
            'title': args.dataset_name,
            'notes': 'A long description of my dataset',
            # 'license_id': None,
            # reliability source: None,
            'owner_org': 'HLRS',
            }
        dataset_dict['name'] = dataset_dict['title'].lower().replace(' ', '-')
        req = requests.post( '{0}/api/action/package_create'.format(args.datacatalogue_entrypoint),
                             data=dataset_dict, **extra_args )

    if args.datacatalogue_key is not None:
        extra_args['headers'] = {'Authorization': args.datacatalogue_key}

    resources_ids = {}
    if not args.create:
        # Get resources list for the given dataset
        response = requests.get( r'{0}/api/rest/dataset/{1}'.format(args.datacatalogue_entrypoint, args.dataset_name),
                                 **extra_args )
        assert response.status_code == requests.codes.ok
        resources_ids = dict( (resource['name'], resource['id']) for resource in response.json()['resources'] )

    # Upload resources to the given dataset
    for [filename, metadata] in file_records:
        resource_id = resources_ids.get(metadata['name'], None)
        if resource_id is None:
            ckap_op = 'resource_create'
            metadata['package_id'] = args.dataset_name.lower().replace(' ', '-')
        else:
            ckap_op = 'resource_update'
            metadata['id'] = resource_id
        response = requests.post( '{0}/api/action/{1}'.format(args.datacatalogue_entrypoint, ckap_op),
                                  data=metadata,
                                  files=[('upload', file(os.path.join('.', filename)))], **extra_args )
        assert response.status_code == requests.codes.ok

if __name__ == "__main__":
    main()
