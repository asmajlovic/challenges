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
from sys import exit
from time import sleep

import pyrax
from pyrax import exceptions as e

# Flag to signify if build errors were encountered
errors = False

# Add a preceding '0' to server hostnames ("prettyfication")
def pretty_hostname(value):
    if value < 10:
        return "0" + str(value)
    else:
        return str(value)

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
    exit(1)
except e.FileNotFound:
    print "ERROR: Credentials file '%s' not found" % (creds_file)
    exit(1)

# Use a shorter Cloud Servers class reference string
# This simplifies invocation later on (less typing)
cs = pyrax.cloudservers

# Compile a list of available RAM sizes for use in argument parsing
# later on. The choices permitted will be made up of this list.
flavor_list = []
for flavor in cs.flavors.list():
    flavor_list.append(flavor.ram)

# Define the script parameters (all are optional for the time being)
parser = argparse.ArgumentParser(description=("Cloud Server provisioning "
                                              "application"))
parser.add_argument("-p", "--prefix", action="store", required=False,
                    metavar="SERVER_NAME_PREFIX", type=str,
                    help=("Server name prefix (defaults to 'server' e.g. "
                          "server01, server02, ...)"), default="server")
parser.add_argument("-s", "--size", action="store", required=False,
                    metavar="SERVER_RAM_SIZE", type=int,
                    help=("Server flavor (RAM size in megabytes, defaults "
                          "to '512')"), choices=flavor_list, default=512)
parser.add_argument("-c", "--count", action="store", required=False,
                    metavar="SERVER_COUNT", type=int,
                    help="Number of servers to build (defaults to 3)",
                    choices=range(1,21), default=3)

# Parse arguments (validate user input)
args = parser.parse_args()

print ("Cloud Server build request initiated\n"
       "TIP: You may wish to check available options by issuing the -h flag")
       
# Locate the image to build from.
# Debian 6 images appear to lead to quickest build time completions (for now)
image = [i for i in cs.images.list() if "Squeeze" in i.name][0]

# Grab the flavor ID from the RAM amount selected by the user.
# The server create request requires the ID rather than RAM amount.
flavor = [f for f in cs.flavors.list() if args.size == f.ram][0]

# Print the image ID and name selected, as well as server count
print "Image ID: %s\nImage name: %s" % (image.id, image.name)
print "Server size: %d MB" % (args.size)
print "Number of servers to be created:", args.count

# Server list definition to be used in tracking build status/comletion
ids = []

# Iterate through the server count specified, sending the build request
# for each one in turn (concurrent builds)
count = 1
while count <= args.count:
    # Issue the server creation request
    server = cs.servers.create(args.prefix + pretty_hostname(count),
                               image.id, flavor.id)
    # Add the server ID from the create request output to the tracking list
    ids.append(server.id)
    count += 1

# Check on the status of the server builds. Completed or error/unknown
# states are removed from the list until nothing remains.
while ids:
    # Track the element position for easier/efficient removal
    count = 0
    for id in ids:
        # Get the server details for the ID in question
        server = cs.servers.get(id)
        # Should it meet the necessary criteria, provide extended info
        # and remove from the list
        if server.status in ["ACTIVE", "ERROR", "UNKNOWN"]:
            print "Server name: %s, Status: %s" % (server.name, server.status)
            if server.status == "ACTIVE":
                print "Networks: %s" % (server.networks)
            else:
                errors = True
                print "WARNING: Something went wrong with the build request"
                print "Please review the server state"
            del ids[count]
        count += 1
    # Reasonable wait period between checks
    sleep(15)

# All done
exit_msg = "Build requests completed"
if errors:
    print "%s - with errors (see above for details)" % (exit_msg)
else:
    print "%s" % (exit_msg)
