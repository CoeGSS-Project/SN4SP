#!/usr/bin/env python2

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
## Get resources with particular names from CKAN
##
## Usage:
##    python2 download_data.py  -ip 'https://coegss1.man.poznan.pl' -d 'synthetic-network-example' "Synthetic population" "Geodata"
##
## Further info:
##    https://docs.ckan.org/en/2.8/api/legacy-api.html
##    https://docs.ckan.org/en/ckan-1.7.4/api-tutorial.html
##    https://docs.ckan.org/en/2.8/api/
##    https://docs.python.org/2/howto/urllib2.html
##    https://stackoverflow.com/questions/32899459/obtain-a-dataset-id-name-of-a-resource-in-ckan-via-a-single-api-call
############################################################

import os
import urllib2
import urllib
import json
import zipfile

import argparse

default_datacatalogue_entrypoint = 'https://coegss1.man.poznan.pl'

default_dataset_name = 'synthetic-network-example'

extra_args = {}

def main():

    parser = argparse.ArgumentParser(description="Upload resources to CKAN providing metadata")
    parser.add_argument("resources", metavar="RESOUCE_NAMES", type=str, nargs="+",
                        help="json file with list of files to upload and metadata")
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
    parser.add_argument("-o",
                        "--output-folder",
                        dest="output_folder",
                        help="Output folder",
                        default=".")
    args = parser.parse_args()

    if not os.path.exists(args.output_folder):
        os.makedirs(args.output_folder)
    assert os.path.isdir(args.output_folder)

    dataset_dict = {
        'name': args.dataset_name,
        }

    # Get dataset
    request = urllib2.Request('{0}/api/rest/dataset/{1}'.\
                                  format(args.datacatalogue_entrypoint, args.dataset_name))

    if args.datacatalogue_key is not None:
        request.add_header('Authorization', args.datacatalogue_key)

    # print(urllib.quote(json.dumps(dataset_dict)))

    # Make the HTTP request
    response = urllib2.urlopen(request)#,
    # urllib.quote(json.dumps(dataset_dict)))
    assert response.code == 200

    # Use the json module to load CKAN's response into a dictionary.
    response_dict = json.loads(response.read())
    assert response_dict['type'] == 'dataset'
    # print(response_dict['resources'])

    for resource in response_dict['resources']:
        if resource['name'] in args.resources: 
            basename = resource['url'].rsplit('/', 1)[-1]
            fileextension = str(os.path.splitext(basename)[1]).lower()
            filename = os.path.join(args.output_folder, "{0}{1}".format(resource['name'].lower().replace(' ', '_'), fileextension))
            urllib.urlretrieve (resource['url'], filename)
            print("-- fetched {0}".format(filename))
            if resource['format'] == 'ZIP' or \
                    fileextension in (".zip",):
                urllib.urlretrieve (resource['url'], filename)
                # zipfile #io.BytesIO
                zip_file = zipfile.ZipFile(filename, 'r')
                zip_file.printdir()
                zip_file.extractall()

if __name__ == "__main__":
    main()
