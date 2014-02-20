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
import socket
from sys import exit
from time import sleep

import pyrax
from pyrax import exceptions as e

# Location of pyrax configuration file
CONFIG_FILE = "~/.rackspace_cloud_credentials"

# Identity type to be used (RAX)
IDENTITY_TYPE = "rackspace"

# Default TTL value
DEFAULT_TTL = 300

def zone_list(obj):
    """
    Return all zones under an account
    """
    # Get and return the zone list
    doms = obj.list()
    return doms


def is_int(val, limit):
    """
    Determine if value provided is an integer greater than or equal to limit
    """
    try:
        val = int(val)
        if val < limit:
            val = None
    except ValueError:
        val = None
    return val


def is_valid_ipv4(address):
    """
    Determine whether or not the IPv4 address provided is correctly structured
    """
    try:
        addr = socket.inet_pton(socket.AF_INET, address)
    except AttributeError:
        try:
            addr = socket.inet_aton(address)
        except socket.error:
            return False
        return address.count('.') == 3
    except socket.error:
        return False
    return True


def main():
    """
    Challenge 9
    -- Write an application that when passed the arguments FQDN, image, and
       flavor it creates a server of the specified image and flavor with the
       same name as the FQDN, and creates a DNS entry for the FQDN pointing
       to the server's public IP.
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

    # Parse script parameters
    p = argparse.ArgumentParser(description=("Create a server using FQDN and "
                                             "IP address parameters"))
    p.add_argument("fqdn", action="store", type=str, metavar="[fqdn]",
                   help="Fully qualified domain name for A record")
    p.add_argument("-i", "--image", action="store", required=False,
                   metavar="[server image]", type=str,
                   help=("Image name to be used in server build "
                         "(defaults to 'Debian 7')"),
                   default="Debian 7 (Wheezy)")
    p.add_argument("-f", "--flavour", action="store", required=False,
                   metavar="[server flavour]", type=str,
                   help=("Server flavour name (defaults to "
                         "'1 GB Performance')"), choices=FLAVOUR_LIST,
                   default="1 GB Performance")
    p.add_argument("-r", "--region", action="store", required=False,
                   metavar="[region]", type=str,
                   help=("Region where container should be created "
                         "(defaults to 'ORD'"),
                   choices=["ORD", "DFW", "LON", "IAD", "HKG", "SYD"],
                   default="ORD")
    p.add_argument("-t", "--ttl", action="store", required=False,
                   type=int, metavar="[ttl value]",
                   help=("TTL for the new record (default %d seconds)"
                          % (DEFAULT_TTL)), default=DEFAULT_TTL)

    # Parse arguments (validate user input)
    args = p.parse_args()

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
        exit(1)
    # All is apparently well, define the zone/domain using the FQDN string
    else:
        zone_name = '.'.join(segments[-(len(segments)-1):])
    
    # If TTL has been provided, confirm that it is valid
    if args.ttl:
        ttl = is_int(args.ttl, DEFAULT_TTL)
        if not ttl:
            print ("ERROR: TTL must be an integer greater or equal to %d"
                   % (DEFAULT_TTL))
            exit(2)
    else:
        ttl = DEFAULT_TTL

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
               "that the API username, key, and region are in place and correct.")
        exit(3)
    except e.FileNotFound:
        print "ERROR: Credentials file '%s' not found" % (creds_file)
        exit(4)

    # Use a shorter Cloud Servers and DNS class reference strings
    # This simplifies invocation later on (less typing)
    cs = pyrax.cloudservers
    dns = pyrax.cloud_dns

    # Grab zone list
    domains = zone_list(dns)

    # No zones found, inform that one needs to be created and exit
    if len(domains) == 0:
        print "ERROR: You have no domains/zones at this time"
        print "Please create one first then try again"
        exit(5)

    # Attempt to locate the zone extracted from FQDN string
    try:
        zone = [d for d in domains if zone_name in d.name][0]
    except:
        print "ERROR: Zone '%s' not found" % (zone_name)
        print "Please check/create and try again"
        exit(6)

    # Locate the image to build from (confirm it exists)
    try:
        image = [i for i in cs.images.list() if args.image in i.name][0]
    except:
        print ("ERROR: Image name provided was not found. Please check "
               "and try again")
        exit(7)

    # Grab the flavor ID from the flavour name selected by the user.
    # The server create request requires the relevant ID.
    try:
        flavor = [f for f in cs.flavors.list() if args.flavour in f.name][0]
    except:
        print ("ERROR: Flavor name provided has not matched any entries. "
               "Please check and try again.")
        exit(8)

    # Print the image ID and name selected along with chosen RAM size
    print "-- Image details\n\tID: %s\n\tName: %s" % (image.id, image.name)
    print ("\n-- Server build details\n\tName: %s\n\tFlavour: %s"
           % (args.fqdn, args.flavour))

    # Attempt to build the server and track progress
    print "\nBuilding server..."
    srv = cs.servers.create(args.fqdn, image.id, flavor.id)

    while srv.status in ["BUILD"]:
        sleep(15)
        srv.get()

    # Server build has issues, show the status
    if srv.status not in ["ACTIVE"]:
        print ("WARN: Something went wrong during the server creation\n"
               "Please review the output below:\n\tID: %s\n\tName: %s\n\t"
               "Status: %s\n" % (srv.id, srv.name, srv.status))
    # All is well with the server build
    else:
        print ("\n-- Server details\n\tName: %s\n\tStatus: %s"
               "\n\tAdmin password: %s"
               % (srv.name, srv.status, srv.adminPass))
        print ("\tNetworks:\n\t\tPublic #1: %s\n\t\t"
               "Public #2: %s\n\t\tPrivate: %s"
               % (srv.networks["public"][0], srv.networks["public"][1],
                  srv.networks["private"][0]))

    # Public IP address order is not standard, need to grab the IPv4 entry
    #    NOTE: This can be approached better, will need to review later
    count = 0
    ip = srv.networks["public"][count]

    while not is_valid_ipv4(ip):
        count += 1
        ip = srv.networks["public"][count]

    # Define and attempt to add the new A record
    a_rec = {"type": "A",
            "name": args.fqdn,
            "data": ip,
            "ttl": ttl}

    # Attempt to add the A record and we're done
    try:
        rec = zone.add_record(a_rec)
        print ("\n-- Record details\n\tName: %s\n\tType: %s\n\tIP address: "
               "%s\n\tTTL: %s") % (rec[0].name, rec[0].type,
                                    rec[0].data, rec[0].ttl)
        print "INFO: All requests completed successfully"
    except e.DomainRecordAdditionFailed as err:
        print "ERROR: Record creation failed:", err
        exit(9)


if __name__ == '__main__':
    main()
