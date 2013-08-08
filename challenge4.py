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
    Challenge 4
    -- Write a script that uses Cloud DNS to create a new A record when
       passed a FQDN and IP address as arguments.
    """
    # Parse script parameters
    parser = argparse.ArgumentParser(description=("Create an A record using "
                                                  "FQDN and IP address "
                                                   "parameters"))
    parser.add_argument("-f", "--fqdn", action="store",
                        required=True, type=str, metavar="FQDN",
                        help="Fully qualified domain name for A record")
    parser.add_argument("-i", "--ip", action="store",
                        required=True, type=str, metavar="IP_ADDRESS",
                        help="IP address to which A record will resolve to")
    parser.add_argument("-r", "--region", action="store", required=False,
                            metavar="REGION", type=str,
                            help=("Region where container should be created "
                                  "(defaults to 'ORD'"),
                                  choices=["ORD", "DFW", "LON"],
                                  default="ORD")
    parser.add_argument("-t", "--ttl", action="store",
                        required=False, type=int, metavar="TTL_VALUE",
                        help=("TTL for the new record (default %ds)"
                             % (DEFAULT_TTL)), default=DEFAULT_TTL)

    # Parse arguments (validate user input)
    args = parser.parse_args()

    # Determine if IP address provided is formatted correctly
    if not is_valid_ipv4(args.ip):
        print ("ERROR: IP address provided is incorrectly formated, please "
               "check and try again")
        exit(1)

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
        exit(2)
    # All is apparently well, define the zone/domain using the FQDN string
    else:
        zone_name = '.'.join(segments[-(len(segments)-1):])
    
    # If TTL has been provided, confirm that it is valid
    if args.ttl:
        ttl = is_int(args.ttl, DEFAULT_TTL)
        if not ttl:
            print ("ERROR: TTL must be an integer greater or equal to %d"
                   % (DEFAULT_TTL))
            exit(3)
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
        exit(4)
    except e.FileNotFound:
        print "ERROR: Credentials file '%s' not found" % (creds_file)
        exit(5)

    # Use a shorter Cloud DNS class reference string
    # This simplifies invocation later on (less typing)
    dns = pyrax.cloud_dns

    # Grab zone list
    domains = zone_list(dns)

    # No zones found, inform that one needs to be created and exit
    if len(domains) == 0:
        print "ERROR: You have no domains/zones at this time"
        print "Please create one first then try again"
        exit(6)

    # Attempt to locate the zone extracted from FQDN string
    try:
        zone = [i for i in domains if zone_name in i.name][0]
    except:
        print "ERROR: Zone '%s' not found" % (zone_name)
        print "Please check/create and try again"
        exit(7)

    # Attempt to add the new A record
    a_rec = {"type": "A",
            "name": args.fqdn,
            "data": args.ip,
            "ttl": ttl}

    try:
        rec = zone.add_record(a_rec)
        print "Successfully added"
        print ("-- Record details\n\tName: %s\n\tType: %s\n\tIP address: "
               "%s\n\tTTL: %s") % (rec[0].name, rec[0].type, rec[0].data,
               rec[0].ttl)
    except e.DomainRecordAdditionFailed as err:
        print "ERROR: Record addition request failed:", err


if __name__ == '__main__':
    main()
