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

# Identity type to be used (RAX)
IDENTITY_TYPE = "rackspace"

def main():
    """
    Challenge 3
    -- Write a script that accepts a directory as an argument as well as a
       container name. The script should upload the contents of the specified
       directory to the container (or create it if it doesn't exist). The
       script should handle errors appropriately. (Check for invalid paths,
       etc.)
    """
    # Parse script parameters
    parser = argparse.ArgumentParser(description=("Push local objects "
                                                   "to Cloud Files"))
    parser.add_argument("-d", "--directory", action="store",
                        required=True, type=str, metavar="LOCAL_DIR",
                        help="Local directory to upload content from")
    parser.add_argument("-c", "--container", action="store",
                        required=True, type=str, metavar="CONTAINER_NAME",
                        help=("Container name where content should "
                              "be uploaded"))
    parser.add_argument("-r", "--region", action="store", required=False,
                            metavar="REGION", type=str,
                            help=("Region where container should be created"
                                  " (defaults to 'ORD'"),
                                  choices=["ORD", "DFW", "LON"],
                                  default="ORD")
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
        sys.exit(2)
    except e.FileNotFound:
        print "ERROR: Credentials file '%s' not found" % (creds_file)
        sys.exit(3)

    # Use a shorter Cloud Files class reference string
    # This simplifies invocation later on (less typing)
    cf = pyrax.cloudfiles

    # Determine if container already exists, otherwise create it
    try:
        print "Checking if container already exists..."
        cont = cf.get_container(args.container)
    except:
        cont = None

    # Container not found, create it
    if cont is None:
        try:
            print ("Container '%s' not found, creating..."
                   % (args.container))
            cont = cf.create_container(args.container)
        except:
            print "ERROR: Could not create container", args.container
            sys.exit(4)
    # Otherwise inform the user/client that the directory exists and
    # determine if we can proceed (is the overwrite flag set)
    else:
        print "Container '%s' found" % (cont.name)
        if args.force:
            print "Proceeding as upload has been forced"
        else:
            print "Force flag not set, exiting..."
            sys.exit(5)

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

    # Upload completed, confirm/print object count
    objs = cf.get_container_object_names(cont)
    print "Number of objects uploaded: %d\nUpload complete" % (len(objs))


if __name__ == '__main__':
    main()
