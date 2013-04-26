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
from sys import exit
from time import sleep

import pyrax
from pyrax import exceptions as e

# Set upload progress toolbar width
toolbar_width = 50

# Parse script parameters
parser = argparse.ArgumentParser(description=("Push local directories/objects "
                                               "to Cloud Files"))
parser.add_argument("-d", "--directory", action="store",
                    required=True, type=str,
                    help="Local directory to upload content from")
parser.add_argument("-c", "--container", action="store",
                    required=True, type=str,
                    help="Container name where content should be uploaded")

args = parser.parse_args()

# Determine if the upload directory exists
if not os.path.isdir(args.directory):
    print ("ERROR: Specified directory (%s) does not exist, please check "
           "the path and try again)" % (args.directory))
    exit(1)

# Define the authentication credentials file location and request that pyrax
# makes use of it. If not found, let the client/user know about it.

# Use a credential file in the following format:
# [rackspace_cloud]
# username = myusername
# api_key = 01234567890abcdef
# region = LON

try:
    creds_file = os.path.expanduser("~/.rackspace_cloud_credentials")
    pyrax.set_credential_file(creds_file, "LON")
except e.AuthenticationFailed:
    print ("ERROR: Authentication failed. Please check and confirm "
           "that the API username, key, and region are in place and correct.")
    sys.exit(1)
except e.FileNotFound:
    print "ERROR: Credentials file '%s' not found" % (creds_file)
    sys.exit(1)

# Use a shorter Cloud Files class reference string
# This simplifies invocation later on (less typing)
cf = pyrax.cloudfiles

# Determine if container already exists, otherwise create it
try:
    print "Checking if container exists..."
    cont = cf.get_container(args.container)
except:
    cont = None

# Container not found, create it
if cont is None:
    try:
        print ("Container '%s' does not exist, creating"
               % (args.container))
        cont = cf.create_container(args.container)
    except:
        print "ERROR: Could not create container", args.container
        exit(1)
# Otherwise print the current CDN TTL associated with the existing container
else:
    print ("Container '%s' already exists - continuing with upload" %
           (cont.name))

# Start the upload
print "Beginning directory/folder upload"
(upload_key, total_bytes) = cf.upload_folder(args.directory, cont)

# Inform the user of the total upload size
print ("Total upload size: %d bytes (%.2f MB)"
       % (total_bytes, total_bytes / 1024.0 / 1024))

# Prepare progress toolbar
sys.stdout.write("[%s]" % (" " * toolbar_width))
sys.stdout.flush()
sys.stdout.write("\b" * (toolbar_width+1)) # return to start of line, after '['

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
nms = cf.get_container_object_names(cont)
print "Number of objects uploaded: %d\nUpload complete" % (len(nms))
