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
CONFIGFILE = "~/.rackspace_cloud_credentials"

def main():
    """
    Challenge 1
     -- Write a script that builds three 512 MB Cloud Servers following a
        similar naming convention. (ie., web1, web2, web3) and returns the
        IP and login credentials for each server.
    """
    # Variable to determine if build errors were encountered
    ERRORS = False

    # Compile a list of available RAM sizes for use in argument parsing
    # later on. The choices permitted will be made up of this list.
    #    NOTE: Should revisit to make more dynamic for if and when
    #          the list is updated
    flavor_list = [512, 1024, 2048, 4096, 8192, 15360, 30720]
    
    # Define the script parameters (all are optional for the time being)
    parser = argparse.ArgumentParser(description=("Cloud Server provisioning "
                                                  "application"))
    parser.add_argument("-p", "--prefix", action="store", required=False,
                        metavar="SERVER_NAME_PREFIX", type=str,
                        help=("Server name prefix (defaults to 'server' e.g. "
                              "server1, server2, ...)"), default="server")
    parser.add_argument("-r", "--region", action="store", required=False,
                        metavar="REGION", type=str,
                        help=("Region where servers should be built (defaults"
                              " to 'ORD'"), choices=["ORD", "DFW", "LON"],
                              default="ORD")
    parser.add_argument("-i", "--image", action="store", required=False,
                        metavar="SERVER_IMAGE", type=str,
                        help=("Image ID to be used in server build (defaults"
                              " to '8ae428cd-0490-4f3a-818f-28213a7286b0' - "
                              "Debian Squeeze"),
                              default="8ae428cd-0490-4f3a-818f-28213a7286b0")
    parser.add_argument("-s", "--size", action="store", required=False,
                        metavar="SERVER_RAM_SIZE", type=int,
                        help=("Server RAM size in megabytes (defaults to "
                              "'512')"), choices=flavor_list, default=512)
    parser.add_argument("-c", "--count", action="store", required=False,
                        metavar="SERVER_COUNT", type=int,
                        help="Number of servers to build (defaults to 3)",
                        choices=range(1,11), default=3)

    # Parse arguments (validate user input)
    args = parser.parse_args()

    # Define the authentication credentials file location and request that
    # pyrax makes use of it. If not found, let the client/user know about it.

    # Use a credential file in the following format:
    # [rackspace_cloud]
    # username = myusername
    # api_key = 01234567890abcdef
    # region = LON

    try:
        creds_file = os.path.expanduser(CONFIGFILE)
        pyrax.set_credential_file(creds_file, args.region)
    except e.AuthenticationFailed:
        print ("ERROR: Authentication failed. Please check and confirm "
               "that the API username, key, and region are in place "
               "and correct.")
        exit(1)
    except e.FileNotFound:
        print "ERROR: Credentials file '%s' not found" % (creds_file)
        exit(2)

    # Use a shorter Cloud Servers class reference string
    # This simplifies invocation later on (less typing)
    cs = pyrax.cloudservers

    # Locate the image to build from (confirm it exists)
    try:
        image = [i for i in cs.images.list() if args.image in i.id][0]
    except:
        print ("ERROR: Image ID provided was not found. Please check "
               "and try again")
        exit(3)

    # Grab the flavor ID from the RAM amount selected by the user.
    # The server create request requires the ID rather than RAM amount.
    flavor = [f for f in cs.flavors.list() if args.size == f.ram][0]

    print ("Cloud Server build request initiated\n"
           "TIP: You may wish to check available options by issuing "
           "the -h/--help flag\n")

    # Print the image ID and name selected, as well as server count
    print "-- Image details\n\tID: %s\n\tName: %s" % (image.id, image.name)
    print ("\n-- Server build details\n\tSize: %d MB\n\tCount: %d"
           % (args.size, args.count))

    # Server list definition to be used in tracking build status/comletion
    servers = []

    # Iterate through the server count specified, sending the build request
    # for each one in turn (concurrent builds)
    count = 1
    while count <= args.count:
        # Issue the server creation request
        srv = cs.servers.create(args.prefix + str(count),
                                   image.id, flavor.id)
        # Add server ID from the create request to the tracking list
        servers.append(srv)
        count += 1

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
                print ("\n-- Server details:\n\tName: %s\n\tStatus: %s"
                       "\n\tAdmin password: %s"
                      % (server.name, server.status, server.adminPass))
                print ("\tNetworks:\n\t\tPublic #1: %s\n\t\t"
                       "Public #2: %s\n\t\tPrivate: %s"
                       % (server.networks["public"][0],
                          server.networks["public"][1],
                          server.networks["private"][0]))
                if server.status not in ["ACTIVE"]:
                    ERRORS = True
                    print "WARN: Something went wrong with the build request"
                del servers[count]
            count += 1
        # Reasonable wait period between checks
        sleep(15)

    # All done
    exit_msg = "\nBuild requests completed"
    if ERRORS:
        print "%s - with errors (see above for details)" % (exit_msg)
    else:
        print "%s" % (exit_msg)


if __name__ == '__main__':
    main()