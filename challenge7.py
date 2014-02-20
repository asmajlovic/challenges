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

# Location of pyrax configuration file
CONFIG_FILE = "~/.rackspace_cloud_credentials"

# Identity type to be used (RAX)
IDENTITY_TYPE = "rackspace"

def main():
    """
    Challenge 7
    -- Write a script that will create 2 Cloud Servers and add them as nodes
       to a new Cloud Load Balancer.
    """
    # Variable to determine if build errors were encountered
    ERRORS = False

    # Compile a list of available flavours for use in argument parsing
    # later on. The choices permitted will be made up of this list.
    #    NOTE: Should revisit to make more dynamic and account for any
    #          flavour updates
    FLAVOUR_LIST = [
                    "512MB Standard", 
                    "1GB Standard",
                    "2GB Standard",
                    "4GB Standard",
                    "8GB Standard",
                    "15GB Standard",
                    "30GB Standard",
                    "1 GB Performance",
                    "2 GB Performance",
                    "4 GB Performance",
                    "8 GB Performance",
                    "15 GB Performance",
                    "30 GB Performance",
                    "60 GB Performance",
                    "90 GB Performance",
                    "120 GB Performance"
                    ]
    
    # Compile a list of available LB algorithms (similar to above)
    ALGORITHM_LIST = [
                      "LEAST_CONNECTIONS",
                      "RANDOM",
                      "ROUND_ROBIN",
                      "WEIGHTED_LEAST_CONNECTIONS",
                      "WEIGHTED_ROUND_ROBIN"
                     ]

    # Define the script parameters (all are optional for the time being)
    p = argparse.ArgumentParser(description=("Provisioning Cloud Servers "
                                             "behind an HTTP load balancer"))
    p.add_argument("-x", "--prefix", action="store", required=False,
                   metavar="[server name prefix]", type=str,
                   help=("Server name prefix (defaults to 'server' e.g."
                         " server-1, server-2, ...)"), default="server-")
    p.add_argument("-f", "--flavour", action="store", required=False,
                   metavar="[server flavour]", type=str,
                   help=("Server flavor (RAM size in MB, defaults to "
                         "'1 GB Performance'"),
                   choices=FLAVOUR_LIST, default="1 GB Performance")
    p.add_argument("-i", "--image", action="store", required=False,
                   metavar="[server image]", type=str,
                   help=("Image name to be used in server build (defaults to "
                         " 'Debian 7'"),
                   default="Debian 7 (Wheezy")
    p.add_argument("-c", "--count", action="store", required=False,
                   metavar="[server count]", type=int,
                   help="Number of servers to build (defaults to 2)",
                   choices=xrange(1,11), default=2)
    p.add_argument("-n", "--lb-name", action="store", required=False,
                   metavar="[lb name]", type=str,
                   help=("Preferred LB name (defaults to server prefix with "
                         " '-lb' appended)"))
    p.add_argument("-t", "--lb-vip-type", action="store", required=False,
                   metavar="[vip type]", type=str,
                   help=("Virtual IP address type - PUBLIC or SNET "
                         "(defaults to PUBLIC)"),
                   choices=["PUBLIC","SNET"], default="PUBLIC")
    p.add_argument("-a", "--algorithm", action="store", required=False,
                   metavar="[lb algorithm]", type=str,
                   help="Load balancing algoritm (defaults to RANDOM)",
                   choices=ALGORITHM_LIST, default="RANDOM")
    p.add_argument("-p", "--service-port", action="store",
                   required=False, metavar="[lb port]", type=int,
                   help="LB HTTP service port (defaults to 80)", default=80)
    p.add_argument("-r", "--region", action="store", required=False,
                   metavar="[region]", type=str,
                   help=("Region where resources should be created"
                         " (defaults to 'ORD'"),
                   choices=["ORD", "DFW", "LON", "IAD", "HKG", "SYD"],
                   default="ORD")

    # Parse arguments (validate user input)
    args = p.parse_args()

    # Define the authentication credentials file location and request that pyrax
    # makes use of it. If not found, let the client/user know about it.

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
               "that the API username, key, and region are in place and "
               "correct.")
        exit(1)
    except e.FileNotFound:
        print "ERROR: Credentials file '%s' not found" % (creds_file)
        exit(2)

    # Use a shorter Cloud Servers and LB class reference strings
    # This simplifies invocation later on (less typing)
    cs = pyrax.cloudservers
    clb = pyrax.cloud_loadbalancers
       
    # Locate the image to build from (confirm it exists)
    try:
        image = [i for i in cs.images.list() if args.image in i.name][0]
    except:
        print ("ERROR: Image ID provided was not found. Please check "
               "and try again")
        exit(3)

    # Grab the flavor ID from the RAM amount selected by the user.
    # The server create request requires the ID rather than RAM amount.
    flavor = [f for f in cs.flavors.list() if args.flavour == f.name][0]
    
    # Set the LB name from the args provided
    lbname = args.lb_name if args.lb_name else args.prefix + "lb"

    print ("\nINFO: Cloud Server build request initiated\n"
           "\tTIP: You may wish to check available options by issuing "
           "the -h flag")

    # Print the image ID and name selected, as well as server count
    print "\n-- Image details\n\tID: %s\n\tName: %s" % (image.id, image.name)
    print ("\n-- Server build details\n\tFlavour: %s\n\tCount: %d"
           % (args.flavour, args.count))

    # Server list definition to be used in tracking build status/comletion
    servers = []

    # Iterate through the server count specified, sending the build request
    # for each one in turn (concurrent builds)
    for count in xrange(args.count):
        # Issue the server creation request
        srv = cs.servers.create(args.prefix + str(count + 1),
                                   image.id, flavor.id)
        # Add server ID from the create request to the tracking list
        servers.append(srv)

    # Prepare a list for all active servers, since failed entries will
    # not be removed as we do not have health checks defined just yet
    srv = []

    # Check on the status of the server builds. Completed or error/unknown
    # states are removed from the list until nothing remains.
    while servers:
        # Track the element position for easier/efficient removal
        count = 0
        for server in servers:
            # Get the updated server details
            server.get()
            # Should it meet the necessary criteria, provide extended info
            # and remove from the list
            if server.status in ["ACTIVE", "ERROR", "UNKNOWN"]:
                print ("\n-- Server details\n\tName: %s\n\tStatus: %s"
                       "\n\tAdmin password: %s"
                      % (server.name, server.status, server.adminPass))
                print ("\tNetworks:\n\t\tPublic #1: %s\n\t\t"
                       "Public #2: %s\n\t\tPrivate: %s"
                       % (server.networks["public"][0],
                          server.networks["public"][1],
                          server.networks["private"][0]))
                # Failed build, state so to the client/user
                if server.status not in ["ACTIVE"]:
                    ERRORS = True
                    print "WARN: Build process for %s failed" % (server.name)
                # Otherwise append to the active list to be added to the LB
                else:
                    srv.append(server)
                del servers[count]
            count += 1
        # Reasonable wait period between checks
        sleep(15)

    # Check if we have active servers, no point in proceeding if there
    # are none since at least a single instance is required to create
    # an LB
    if len(srv) == 0:
        print "ERROR: No servers in an active state, cannot create LB"
        exit(4)
    else:
        # Otherwise, prepare and add all active nodes
        nodes = []
        for server in srv:
            nodes.append(clb.Node(address=server.networks["private"][0],
                                  port="80"))

        # Define the VIP type based on argument provided by client/user
        vip = clb.VirtualIP(type=args.lb_vip_type)
        
        # Create the LB
        lb = clb.create(lbname, port=args.service_port, protocol="HTTP",
                        nodes=nodes, virtual_ips=[vip], algorithm=args.algorithm)

        # Print LB details
        public_ips = [vip.address for vip in lb.virtual_ips]
        print ("\n-- LB details --\n\tName: %s\n\tPort: %s\n\t"
               "Algorithm type: %s\n\tNode count: %s"
                % (lb.name, lb.port, lb.algorithm, len(lb.nodes)))
        count = 1
        for ip in public_ips:
            print "\tIP address #%d: %s" % (count, ip)
            count += 1
    
    # All done, complete with an overall status update
    exit_msg = "\nINFO: Build requests completed"
    if ERRORS:
        print "%s - with errors (see above for details)" % (exit_msg)
    else:
        print "%s" % (exit_msg)


if __name__ == '__main__':
    main()
