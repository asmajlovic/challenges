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

# Location of pyrax configuration file
CONFIG_FILE = "~/.rackspace_cloud_credentials"

# Identity type to be used (RAX)
IDENTITY_TYPE = "rackspace"

# Max volume size (GB) definition
#   NOTE: Not a great way to define it but there seems to be no easy
#         way to determine the maximum volume size.  One approach is to
#         attempt to build an instance with a ridiculously high value and
#         parse the exception output/message for the current limit
MAX_VOL_SIZE = 150

# Available flavors
#   NOTE: Can be handled better if we can grab the flavor list before the
#         the arguments are parsed, this setting some choices dynamically.
#         Since region is part of the argument list, we get into a bit of
#         a pickle - region is an arg and needs to be parsed before we
#         can authenticate and grab the flavor list :-/
FLAVOUR_LIST = [512, 1024, 2048, 4096, 8192, 16384]


def main():
    """
    Challenge 5
    -- Write a script that creates a Cloud Database instance. This instance
       should contain at least one database, and the database should have at
       least one user that can connect to it.
    """
    # Parse script parameters
    p = argparse.ArgumentParser(description=("Create an Cloud DB instance "
                                             "along with a DB and management"
                                             " user"))
    p.add_argument("instance", action="store", type=str,
                   metavar="[instance name]",
                   help="Preferred Cloud DB instance name")
    p.add_argument("-m", "--memory", action="store", required=False,
                   type=int, metavar="[size]",
                   help="Preferred memory size of instance (default 512MB)",
                   choices=FLAVOUR_LIST, default=512)
    p.add_argument("-v", "--volume", action="store", required=False,
                   type=int, metavar="[volume size]",
                   help="Preferred DB volume size in GB (default 1GB)",
                   default=1)
    p.add_argument("-d", "--db", action="store", required=False, type=str,
                   metavar="[db name]",
                   help="Preferred DB name (default 'mydb')",
                   default="mydb")
    p.add_argument("-u", "--username", action="store", required=False,
                   type=str, metavar="[db user]",
                   help=("Preferred DB management user (default "
                         "'dbuser'"), default="dbuser")
    p.add_argument("-p", "--password", action="store", required=False,
                   type=str, metavar="[db password]",
                   help=("Preferred DB user password (default is a random "
                         "string"), default=(pyrax.utils.random_ascii(
                                                length=10)))
    p.add_argument("-o", "--host", action="store", required=False,
                   type=str, metavar="[host]",
                   help=("Host IP address/wildcard for user access (default "
                         "is '%')"),  default="%")
    p.add_argument("-r", "--region", action="store", required=False,
                   metavar="[region]", type=str,
                   help=("Region where container should be created "
                         "(defaults to 'ORD'"),
                   choices=["ORD", "DFW", "LON", "IAD", "HKG", "SYD"],
                   default="ORD")

    # Parse arguments (validate user input)
    args = p.parse_args()

    # Determine if volume size is in acceptable range
    if args.volume < 1 or args.volume > 150:
        print ("ERROR: Permitted volume size is between 1 and %d GB"
               % (MAX_VOL_SIZE))
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
               "that the API username, key, and region are in place and "
               "correct.")
        sys.exit(2)
    except e.FileNotFound:
        print "ERROR: Credentials file '%s' not found" % (creds_file)
        sys.exit(3)

    # Use a shorter Cloud Databases class reference string
    # This simplifies invocation later on (less typing)
    cdb = pyrax.cloud_databases

    # Determine which flavor was selected and grab the full details
    try:
        flavor = [i for i in cdb.list_flavors() if args.memory == i.ram][0]
    except:
        print ("ERROR: Flavor name provided has not matched any entries. "
               "Please check and try again.")
        sys.exit(4)

    # Attempt to create the instance
    try:
        print "INFO: Creating instance '%s'" % (args.instance)
        instance = cdb.create(args.instance, flavor=flavor,
                                volume=args.volume)
    except:
        print "ERROR: Instance creation failed"
        sys.exit(5)

    # Keep checking status until it's something other than 'BUILD'
    while instance.status in ["BUILD"]:
        # Push something to the screen to assure us things are moving along
        sys.stdout.write(".")
        sys.stdout.flush()
        # Reasonable wait time between status checks
        sleep(30)
        instance.get()
    print

    # Inform the client/user of the outcome
    if instance.status not in ["ACTIVE"]:
        print ("ERROR: Instance build failed\nStatus: %s"
               % instance.status)
        sys.exit(6)
    else:
        print "INFO: Instance successfully created"

    try:
        # Add the new DB to the instance
        instance.create_database(args.db)

        # Same for the user
        instance.create_user(args.username, args.password,
                                database_names=args.db, host=args.host)
    except e.BadRequest as err:
        print "ERROR: DB and user creation failed\nReason:", err
        sys.exit(7)

    # We're all done
    print ("-- Details:\n\tDB Host: %s\n\tDB Name: %s\n\tDB User: %s\n\t"
           "DB Password: %s" % (instance.hostname, args.db, args.username,
            args.password))


if __name__ == '__main__':
    main()
