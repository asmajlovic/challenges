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
RAM_LIST = [ 512, 1024, 2048, 4096, 8192, 16384 ]


def main():
    """
    Challenge 5
    -- Write a script that creates a Cloud Database instance. This instance
       should contain at least one database, and the database should have at
       least one user that can connect to it.
    """
    # Parse script parameters
    parser = argparse.ArgumentParser(description=("Create an Cloud DB "
                                                  "instance along with a DB "
                                                   "and management user"))
    parser.add_argument("-i", "--instance", action="store",
                        required=True, type=str, metavar="INSTANCE_NAME",
                        help="Preferred Cloud DB instance name")
    parser.add_argument("-m", "--ram", action="store", required=False,
                        type=int, metavar="RAM_SIZE",
                        help="Preferred RAM size of instance (default 512MB)",
                        choices=RAM_LIST, default=512)
    parser.add_argument("-v", "--volume", action="store", required=False,
                        type=int, metavar="DB_VOLUME_SIZE",
                        help=("Preferred DB volume size in GB (default "
                              "1 GB)"), default=1)
    parser.add_argument("-d", "--db", action="store",
                        required=False, type=str, metavar="DB_NAME",
                        help="Preferred DB name (default 'mydb'",
                        default="mydb")
    parser.add_argument("-u", "--username", action="store", required=False,
                        type=str, metavar="DB_USER",
                        help=("Preferred DB management user (default "
                              "'dbuser'"), default="dbuser")
    parser.add_argument("-p", "--password", action="store", required=False,
                        type=str, metavar="DB_PASS",
                        help=("Preferred DB user password (default random "
                              "string"), default=(pyrax.utils.random_name(
                                         length=10, ascii_only=True)))
    parser.add_argument("-r", "--region", action="store", required=False,
                            metavar="REGION", type=str,
                            help=("Region where container should be created "
                                  "(defaults to 'ORD'"),
                                  choices=["ORD", "DFW", "LON"],
                                  default="ORD")

    # Parse arguments (validate user input)
    args = parser.parse_args()

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
    flavor = [i for i in cdb.list_flavors() if args.ram == i.ram][0]

    # Attempt to create the instance
    print "Creating instance '%s'" % (args.instance)
    instance = cdb.create(args.instance, flavor=flavor, volume=args.volume)

    # Keep checking status until it's something other than 'BUILD'
    while instance.status in ["BUILD"]:
        # Push something to the screen to assure us things are moving along
        sys.stdout.write(".")
        sys.stdout.flush()
        # Reasonable wait time between status checks
        sleep(15)
        instance.get()
    print

    # Inform the client/user of the outcome
    if instance.status not in ["ACTIVE"]:
        print ("Something went wrong with the instance build\nStatus: %s"
               % instance.status)
        sys.exit(4)
    else:
        print "Instance creation complete"

    # Add the new DB to the instance
    instance.create_database(args.db)

    # Same for the user
    instance.create_user(args.username, args.password,
                                database_names=args.db)

    # We're done
    print ("-- Details:\n\tDB Host: %s\n\tDB Name: %s\n\tDB User: %s\n\t"
           "DB Password: %s" % (instance.hostname, args.db, args.username,
            args.password))


if __name__ == '__main__':
    main()
