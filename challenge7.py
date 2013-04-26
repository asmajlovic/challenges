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
from time import sleep

import pyrax
from pyrax import exceptions as e

# Basic image selection/definition string (Debian) to be used in builds
preferred_image = "Squeeze"

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
    sys.exit(1)
except e.FileNotFound:
    print "ERROR: Credentials file '%s' not found" % (creds_file)
    sys.exit(1)

# Use a shorter Cloud Servers and LB class reference strings
# This simplifies invocation later on (less typing)
cs = pyrax.cloudservers
clb = pyrax.cloud_loadbalancers

# Compile a list of available RAM sizes for use in argument parsing
# later on. The choices permitted will be made up of this list.
flavor_list = []
for flavor in cs.flavors.list():
    flavor_list.append(flavor.ram)

# Complile a list of available LB algorithms for use in argument parsing.
# Similar to above
alg_list = []
for alg in clb.algorithms:
    alg_list.append(alg)

# Define the script parameters (all are optional for the time being)
parser = argparse.ArgumentParser(description=("Cloud Servers behind HTTP LB - "
                                              "Provisioning application"))
parser.add_argument("-x", "--prefix", action="store", required=False,
                    metavar="SERVER_NAME_PREFIX", type=str,
                    help=("Server name prefix (defaults to 'server' e.g. "
                          "server01, server02, ...)"), default="server")
parser.add_argument("-s", "--size", action="store", required=False,
                    metavar="SERVER_RAM_SIZE", type=int,
                    help=("Server flavor (RAM size in megabytes, defaults "
                          "to '512')"), choices=flavor_list, default=512)
parser.add_argument("-c", "--count", action="store", required=False,
                    metavar="SERVER_COUNT", type=int,
                    help="Number of servers to build (defaults to 2)",
                    choices=range(1,21), default=2)
parser.add_argument("-n", "--lb-name", action="store", required=False,
                    metavar="LB_NAME", type=str,
                    help="Preferred LB name (defaults to random string)",
                    default=pyrax.utils.random_name(length=8, ascii_only=True))
parser.add_argument("-t", "--lb-vip-type", action="store", required=False,
                    metavar="LB_VIP_TYPE", type=str,
                    help=("Virtual IP address type - PUBLIC or SERVICENET "
                          "(defaults to PUBLIC)"),
                          choices=["PUBLIC","SERVICENET"], default="PUBLIC")
parser.add_argument("-a", "--algorithm", action="store", required=False,
                    metavar="LB_ALGORITHM", type=str,
                    help="Load balancing algoritm (defaults to RANDOM)",
                          choices=alg_list, default="RANDOM")
parser.add_argument("-p", "--service-port", action="store", required=False,
                    metavar="LB_PORT", type=int,
                    help="Service port - HTTP (defaults to 80)",
                    default=80)

# Parse arguments (validate user input)
args = parser.parse_args()

print ("Cloud Server build request initiated\n"
       "TIP: You may wish to check available options by issuing the -h flag")
       
# Locate the image to build from.
# Debian 6 images appear to lead to quickest build time completions (for now)
image = [i for i in cs.images.list() if preferred_image in i.name][0]

# Grab the flavor ID from the RAM amount selected by the user.
# The server create request requires the ID rather than RAM amount.
flavor = [f for f in cs.flavors.list() if args.size == f.ram][0]

# Print the image ID and name selected, as well as server count
print "-- Image details --\n\tID: %s\n\tName: %s" % (image.id, image.name)
print ("-- Server build details --\n\tSize: %d MB\n\tNode count: %d"
       % (args.size, args.count))

# Server list definition to be used in tracking build status/comletion
ids = []

# LB ID definition for later reference
lb_id = None

# Iterate through the server count specified, sending the build request
# for each one in turn (concurrent builds)
print "Building servers..."
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
first_node = True
while ids:
    # Track the element position for easier/efficient removal
    pos = 0
    for id in ids:
        # Get the server details for the ID in question
        server = cs.servers.get(id)
        # Should it meet the necessary criteria, provide extended info
        # and remove from the list
        if server.status in ["ACTIVE", "ERROR", "UNKNOWN"]:
            print ("\n-- Server details --\n\tName: %s\n\tStatus: %s"
                   % (server.name, server.status))
            if server.status in ["ACTIVE"]:
                print ("\tServer networks:\n\t\tPublic #1: %s\n\t\tPublic "
                      "#2: %s\n\t\tPrivate: %s"
                      % (server.networks["public"][0],
                      server.networks["public"][1],
                      server.networks["private"][0]))
                # Determine if this is the first build completed, and if so,
                # create the LB (requires at least one node in order to build)
                if first_node:
                    node = clb.Node(address=server.networks["private"][0],
                                    port=args.service_port,
                                    condition="ENABLED")
                    vip = clb.VirtualIP(type=args.lb_vip_type)
                    lb = clb.create(args.lb_name, port=args.service_port,
                         protocol="HTTP", nodes=[node], virtual_ips=[vip],
                         algorithm=args.algorithm)
                    lb_id = lb.id
                    first_node = False
                else:
                    # We need to ensure that the LB is not updating at the
                    # moment - avoid a status conflict if more than one
                    # node is ready to be added at any given time
                    lb = clb.get(lb_id)
                    while lb.status not in ["ACTIVE"]:
                        sleep(5)
                        lb = clb.get(lb_id)
                    
                    # Add the newly created node
                    node = clb.Node(address=server.networks["private"][0],
                                    port=args.service_port,
                                    condition="ENABLED")
                    lb.add_nodes(node)                  
            else:
                errors = True
                print "WARNING: Something went wrong with the build request"
                print "Please review the server state"
            del ids[pos]
        pos += 1
    # Reasonable wait period between server/node build status checks
    sleep(10)
    # Generate some output to assure the user/client things are moving
    sys.stdout.write(".")
    sys.stdout.flush()

# All done, print the LB details and exit message
print ("\n-- LB details --\n\tName: %s\n\tIP address: %s"
       % (lb.name, lb.virtual_ips[0].address))
exit_msg = "Build requests completed"
if errors:
    print "%s - with errors (see above for details)" % (exit_msg)
else:
    print "%s" % (exit_msg)
