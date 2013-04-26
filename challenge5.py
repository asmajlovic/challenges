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

import getpass
import os
import sys
from time import sleep

import pyrax
from pyrax import exceptions as e

# Max volume size (GB) definition
#   NOTE: Not a great way to define it but there seems to be no straightforward
#         way to determine the maximum volume size.  One approach is to
#         attempt to build an instance with a ridiculously high value and
#         parse the exception output/message for the current limit
max_volume_size = 150

# Define the authentication credentials file location and request that pyrax
# makes use of it. If not found, let the client/user know about it.

# Use a credential file in the following format:
# [rackspace_cloud]
# username = myusername
# api_key = 01234567890abcdef
# region = ORD

try:
    creds_file = os.path.expanduser("~/.rackspace_cloud_credentials")
    pyrax.set_credential_file(creds_file, "ORD")
except e.AuthenticationFailed:
    print ("ERROR: Authentication failed. Please check and confirm "
           "that the API username, key, and region are in place and correct.")
    sys.exit(1)
except e.FileNotFound:
    print "ERROR: Credentials file '%s' not found" % (creds_file)
    sys.exit(2)

# Use a shorter Cloud Databases class reference string
# This simplifies invocation later on (less typing)
cdb = pyrax.cloud_databases

# Grab a list of all available flavours and enumerate, giving the selection
# prompt to the client/user
flavors = cdb.list_flavors()
name = raw_input("Please enter a name for your new Cloud Database instance: ")
print "Available flavors:"
for pos, flavor in enumerate(flavors):
    print "%2d) %s [%s RAM]" % (pos, flavor.name, flavor.ram)

# Keep requesting until a valid selection is made
selection = None
while not selection:
    try:
        val = int(raw_input("Select a flavor for your new instance: "))
        # User could potentially provide a negative integer, which will still
        # be a valid index reference - including a crude catch here
        if val < 0:
            print "Invalid selection. Please try again."
            selection = None
        else:
            selection = flavors[val]
    except IndexError:
        print "Invalid selection. Please try again."
    except ValueError:
        print "Selection must be an integer listed above, please try again."

# Repeat for the volume size
size = None
while not size:
    try:
        size = int(raw_input(("Please enter the volume size in GB (1-%d): ")
              % max_volume_size))
        if size < 1 or size > max_volume_size:
            print "Volume size must be a positive integer in the listed range"
            size = None
    except ValueError:
        print "Volume size must be a positive integer in the listed range"

# Grab DB name from user/client
dbname = raw_input("Please enter the DB name to be created on instance: ")

# Same again for the DB user
dbuser = raw_input("Please enter the username to manage the DB: ")

# We need a password as well (possibility of auto-generating as a feature)
dbpass = getpass.getpass("Please enter the preferred password for the user: ")

# Attempt to create the instance
print "Creating instance '%s'" % (name)
instance = cdb.create(name, flavor=selection, volume=size)
id = instance.id

# Keep checking status until it's something other than 'BUILD'
while instance.status in ["BUILD"]:
    sys.stdout.write(".")
    sys.stdout.flush()
    sleep(5)
    instance = cdb.get(id)
print

# Inform the client/user of the outcome
if instance.status not in ["ACTIVE"]:
    print "Something went wrong with the build\nStatus: %s" % instance.status
    sys.exit(3)
else:
    print "Instance creation complete"

# Add the new DB to the instance
db = instance.create_database(dbname)

# Same for the user
user = instance.create_user(dbuser, dbpass, database_names=db.name)

# We're done
print "Database created and user added. All done."
