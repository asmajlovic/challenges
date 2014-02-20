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

# Minimum TTL (in seconds) for a CDN enabled container
MIN_TTL = 900

# Location of pyrax configuration file
CONFIG_FILE = "~/.rackspace_cloud_credentials"

# Identity type to be used (RAX)
IDENTITY_TYPE = "rackspace"

def main():
    """
    Challenge 6
    -- Write a script that creates a CDN-enabled container in Cloud Files
    """
    # Parse script parameters
    p = argparse.ArgumentParser(description=("Push local objects "
                                                   "to Cloud Files"))
    p.add_argument("directory", action="store", type=str,
                   metavar="[local dir]",
                   help="Local directory to upload content from")
    p.add_argument("container", action="store", type=str,
                   metavar="[container name]",
                   help="Container name where content should be uploaded")
    p.add_argument("-r", "--region", action="store", required=False,
                   metavar="[region]", type=str,
                   help=("Region where container should be created"
                         " (defaults to 'ORD'"),
                   choices=["ORD", "DFW", "LON", "IAD", "HKG", "SYD"],
                   default="ORD")
    p.add_argument("-t", "--ttl", action="store", required=False, type=int,
                   help=("CDN TTL for the container (default '%d seconds')" %
                          (MIN_TTL)), default=MIN_TTL)
    p.add_argument("-f", "--force", action="store_true",
                   required=False, help=("Permit upload to an "
                   "existing container"))

    args = p.parse_args()

    # Determine if the upload directory exists
    if not os.path.isdir(args.directory):
        print ("ERROR: Specified directory (%s) does not exist, please check "
               "the path and try again)" % (args.directory))
        sys.exit(1)

    # Determine if TTL is at least the minimum value permitted
    if args.ttl < MIN_TTL:
        print "ERROR: Minimum TTL permitted is %ds" % (MIN_TTL)
        sys.exit(2)

    # Define the authentication credentials file location and request that
    # pyrax makes use of it. If not found, let the client/user know about it.

    # Use a credential file in the following format:
    # [rackspace_cloud]
    # username = myusername
    # api_key = 01234567890abcdef
    # region = LON

    try:
        creds_file = os.path.expanduser(CONFIG_FILE)
        pyrax.set_setting("identity_type", IDENTITY_TYPE)
        pyrax.set_credential_file(creds_file, args.region)
    except e.AuthenticationFailed:
        print ("ERROR: Authentication failed. Please check and confirm "
               "that the API username, key, and region are in place "
               "and correct.")
        sys.exit(3)
    except e.FileNotFound:
        print "ERROR: Credentials file '%s' not found" % (creds_file)
        sys.exit(4)

    # Use a shorter Cloud Files class reference string
    # This simplifies invocation later on (less typing)
    cf = pyrax.cloudfiles

    # Determine if container already exists, otherwise create it
    try:
        print "INFO: Checking if container already exists..."
        cont = cf.get_container(args.container)
    except:
        cont = None

    # Container not found, create it and CDN enable
    if cont is None:
        try:
            print ("INFO: Container '%s' not found, creating with TTL set "
                   "to %d..." % (args.container, args.ttl))
            cont = cf.create_container(args.container)
            cont.make_public(ttl=args.ttl)
        except:
            print "ERROR: Could not create container", args.container
            sys.exit(5)
    # Otherwise inform the user/client that the directory exists and
    # determine if we can proceed (is the overwrite flag set)
    else:
        print ("INFO: Container '%s' found with TTL set to %d"
               % (cont.name, cont.cdn_ttl))
        if args.force:
            print "INFO: Proceeding as force flag is set"
        else:
            print "INFO: Force flag not set, exiting..."
            sys.exit(6)

    # Start the upload
    print "INFO: Beginning directory/folder upload"
    (upload_key, total_bytes) = cf.upload_folder(args.directory, cont)

    # Inform the user of the total upload size
    print ("INFO: Total upload size: %d bytes (%.2f MB)"
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
    print "INFO: Number of objects uploaded: %d" % (len(objs))
    print ("\nCDN links:\n\tHTTP: %s\n\tHTTPS: %s\n\tStreaming: %s\n\tiOS "
           "streaming: %s\n" % (cont.cdn_uri, cont.cdn_ssl_uri,
                                  cont.cdn_streaming_uri, cont.cdn_ios_uri))
    print "INFO: Upload completed successfully"


if __name__ == '__main__':
    main()
