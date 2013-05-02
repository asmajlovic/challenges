#!/usr/bin/env python

# Copyright 2013 Adnan Smajlovic

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import os
import sys
from math import ceil
from time import sleep

import pyrax
from pyrax import exceptions as e

# Set progress toolbar width (used with image and server creation progress)
TOOLBAR_WIDTH = 50

# Location of pyrax configuration file
CONFIG_FILE = "~/.rackspace_cloud_credentials"

# Minimum TTL (in seconds) for a CDN enabled container
MIN_TTL = 900

# Default TTL (in seconds) for a Cloud DNS record
DEFAULT_TTL = 300

def zone_list(obj):
    """
    Return all zones under an account
    """
    # Get and return the zone list
    doms = obj.list()
    return doms


def main():
    """
    Challenge 8
    -- Write a script that will create a static webpage served out of
       Cloud Files. The script must create a new container, CDN enable it,
       enable it to serve an index file, create an index file object,
       upload the object to the container, and create a CNAME record
       pointing to the CDN URL of the container.
    """
    # Parse script parameters
    parser = argparse.ArgumentParser(description=("Create a Cloud Files "
                                                  "static web site from a "
                                                  "local folder/directory"))
    parser.add_argument("-d", "--directory", action="store",
                        required=True, type=str, metavar="SRC_DIRECTORY",
                        help="Local directory to upload content from")
    parser.add_argument("-c", "--container", action="store",
                        required=True, type=str, metavar="CONTAINER_NAME",
                        help=("Container name where content should be "
                              "uploaded"))
    parser.add_argument("-q", "--fqdn", action="store",
                        required=True, type=str, metavar="CDN_URL_CNAME",
                        help="Fully qualified domain name for CDN CNAME")
    parser.add_argument("-r", "--region", action="store", required=False,
                            metavar="REGION", type=str,
                            help=("Region where container should be created"
                                  " (defaults to 'ORD'"),
                                  choices=["ORD", "DFW", "LON"],
                                  default="ORD")
    parser.add_argument("-t", "--cdn-ttl", action="store",
                        required=False, metavar="CDN_TTL",
                        type=int, help=(("CDN TTL (in seconds) for the "
                              "container (default %d seconds)") % (MIN_TTL)),
                               default=MIN_TTL)
    parser.add_argument("-i", "--index", action="store",
                        required=False, metavar="STATIC_WEB_INDEX",
                        type=str, help=("Static web index file (default "
                                  "'index.html')"), default="index.html")
    parser.add_argument("-l", "--cname-ttl", action="store",
                        required=False, type=int, metavar="CNAME_TTL",
                        help=(("CNAME record TTL (in seconds) for the CDN "
                              "URI (default %d seconds)") % (DEFAULT_TTL)),
                               default=DEFAULT_TTL)
    parser.add_argument("-f", "--force", action="store_true",
                        required=False, help=("Permit upload to an "
                        "existing container"))

    # Parse arguments (validate user input)
    args = parser.parse_args()

    # Determine if the upload directory exists
    if not os.path.isdir(args.directory):
        print ("ERROR: Specified directory (%s) does not exist, please check "
               "the path and try again)" % (args.directory))
        sys.exit(1)

    # Determine if CDN TTL is at least the minimum value permitted
    if args.cdn_ttl < MIN_TTL:
        print "ERROR: Minimum CDN TTL permitted is %ds" % (MIN_TTL)
        sys.exit(2)

    # Same again for the CNAME record
    if args.cname_ttl < DEFAULT_TTL:
        print "ERROR: Minimum CNAME TTL permitted is %ds" % (DEFAULT_TTL)
        sys.exit(3)

    # Determine if the FQDN is correctly formated (at least three segments
    # separated by '.' are required).
    #    NOTE: This can be improved since we're not checking whether or not
    #          the zone in question is a valid TLD or if the string only has
    #          valid (alphanumeric) characters
    segments = args.fqdn.split('.')
    if len(segments) < 3:
        print ("ERROR: FQDN string is incorrectly formatted, please check "
               "and try again")
        print ("Base zone/domain in the format 'example.com' will not be "
               "accepted")
        sys.exit(4)
    # All is apparently well, define the zone/domain using the FQDN string
    else:
        zone_name = '.'.join(segments[-(len(segments)-1):])

    # Define the authentication credentials file location and request that
    # pyrax makes use of it. If not found, let the client/user know about it.

    # Use a credential file in the following format:
    # [rackspace_cloud]
    # username = myusername
    # api_key = 01234567890abcdef
    # region = LON

    try:
        creds_file = os.path.expanduser(CONFIG_FILE)
        pyrax.set_credential_file(creds_file, args.region)
    except e.AuthenticationFailed:
        print ("ERROR: Authentication failed. Please check and confirm "
               "that the API username, key, and region are in place "
               "and correct.")
        sys.exit(5)
    except e.FileNotFound:
        print "ERROR: Credentials file '%s' not found" % (creds_file)
        sys.exit(6)

    # Use a shorter Cloud Files and Cloud DNS class reference strings
    # This simplifies invocation later on (less typing)
    cf = pyrax.cloudfiles
    dns = pyrax.cloud_dns

    # Grab zone list
    domains = zone_list(dns)

    # No zones found, inform that one needs to be created and exit
    if len(domains) == 0:
        print "ERROR: You have no domains/zones at this time"
        print "Please create one first then try again"
        sys.exit(7)

    # Attempt to locate the zone extracted from FQDN string
    try:
        zone = [i for i in domains if zone_name in i.name][0]
    except:
        print "ERROR: Zone '%s' not found" % (zone_name)
        print "Please check/create and try again"
        sys.exit(8)

    # Determine if container already exists, otherwise create it
    try:
        print "Checking if container already exists..."
        cont = cf.get_container(args.container)
    except e.NoSuchContainer:
        cont = None

    # Container not found, create it
    if cont is None:
        try:
            print ("Container '%s' not found, creating with TTL set to %d..."
                   % (args.container, args.cdn_ttl))
            cont = cf.create_container(args.container)
            cont.make_public(ttl=args.cdn_ttl)
        except e.CDNFailed:
            print "ERROR: Could not CDN enable the container"
            sys.exit(9)
        except:
            print "ERROR: Could not create container", args.container
            sys.exit(10)

    # Otherwise inform the user/client that the directory exists and
    # determine if we can proceed (is the overwrite flag set)
    else:
        print ("Container '%s' found with TTL set to %d"
               % (cont.name, cont.cdn_ttl))
        if args.force:
            print "Proceeding as upload has been forced"
        else:
            print "Force flag not set, exiting..."
            sys.exit(11)

    # Set the static web index file (metadata/header)
    print "Setting static web index file to", args.index
    meta = {"X-Container-Meta-Web-Index": args.index}
    cf.set_container_metadata(cont, meta)

    # Check and confirm if the index file exists, otherwise create a
    # placeholder and inform/warn the client of the action
    index_file = args.directory + "/" + args.index
    if not os.path.isfile(index_file):
        print ("Index file '%s' not found, creating a placeholder"
               % (index_file))
        f = open(index_file,'w')
        f.write("Index page placeholder\n")
        f.close()

    # Start the upload
    print "Beginning directory/folder upload"
    (upload_key, total_bytes) = cf.upload_folder(args.directory, cont)

    # Inform the user of the total upload size
    print ("Total upload size: %d bytes (%.2f MB)"
           % (total_bytes, total_bytes / 1024.0 / 1024))

    # Prepare progress toolbar
    sys.stdout.write("[%s]" % (" " * TOOLBAR_WIDTH))
    sys.stdout.flush()
    # Return to start of line, after '['
    sys.stdout.write("\b" * (TOOLBAR_WIDTH + 1))

    # Print the upload progress (1 second interval)
    uploaded = 0
    while uploaded < total_bytes:
        uploaded = cf.get_uploaded(upload_key)
        progress = int(ceil((uploaded * 100.0) / total_bytes / 2))
        sys.stdout.write("%s" % ("=" * progress))
        sys.stdout.flush()
        sys.stdout.write("\b" * (progress)) # Reset progress bar
        sleep(1)
    print

    # Upload completed, print object count and CDN URIs
    objs = cf.get_container_object_names(cont)
    print "Number of objects uploaded: %d" % (len(objs))

    # Attempt to create the new CNAME record
    cname_rec = {"type": "CNAME",
            "name": args.fqdn,
            "data": cont.cdn_uri.replace("http://", ""),
            "ttl": args.cname_ttl}

    try:
        rec = zone.add_record(cname_rec)
        print "Successfully added"
        print ("-- Record details\n\tName: %s\n\tType: %s\n\tIP address: "
               "%s\n\tTTL: %s") % (rec[0].name, rec[0].type, rec[0].data,
               rec[0].ttl)
    except e.DomainRecordAdditionFailed as err:
        print "ERROR: Record addition request failed:", err
        sys.exit(12)


if __name__ == '__main__':
    main()
