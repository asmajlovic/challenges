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

import os
import sys
from math import ceil
from time import sleep

import pyrax
from pyrax import exceptions as e

# Set image progress toolbar width
toolbar_width = 50

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
    sys.exit(1)

# Use a shorter Cloud Servers class reference string
# This simplifies invocation later on (less typing)
cs = pyrax.cloudservers

# Check and confirm the account in question has servers at the moment,
# otherwise exit gracefully
servers = cs.servers.list()
if len(servers) == 0:
    print ("You do not appear to have any servers at the moment.\n"
           "Please create one manually then attempt to clone again.")
    sys.exit(2)

# List the servers currently under the account
#    NOTE: May need to review this approach given there may be a significant
#          number of servers under the account already
srv_id_dict = {}
srv_flavor_dict = {}
print "Select a server from which an image will be created:"
for pos, srv in enumerate(servers):
    print "%2d) %s [%s]" % (pos, srv.name, srv.accessIPv4)
    srv_id_dict[str(pos)] = srv.id
    srv_flavor_dict[str(pos)] = srv.flavor["id"]

# Ask the user to pick the server to clone
selection = None
while selection not in srv_id_dict:
    if selection is not None:
        print "   -- Invalid choice"
    selection = raw_input("Select a server to clone: ")

# We know the ID and flavour, now we need a name for the image
server_id = srv_id_dict[selection]
flavor_id = srv_flavor_dict[selection]
iname = raw_input("Enter a name for the image: ")
sname = raw_input("Enter a name for the new server to be created: ")

# Kick off the image build
img_id = cs.servers.create_image(server_id, iname)
print "Image '%s' with ID '%s' is being created." % (iname, img_id)

# Prepare progress toolbar
sys.stdout.write("[%s]" % (" " * toolbar_width))
sys.stdout.flush()
sys.stdout.write("\b" * (toolbar_width+1)) # return to start of line, after '['

# Grab the image details
img = cs.images.get(img_id)

# Show image creation progress while the status is 'SAVING'
while img.status in ["SAVING"]:
    progress = int(ceil(img.progress / 2))
    sys.stdout.write("%s" % ("=" * progress))
    sys.stdout.flush()
    sys.stdout.write("\b" * (progress)) # Reset progress bar
    sleep(5)
    img = cs.images.get(img_id)
print

# Something is not right with the image creation, bail out gracefully
if img.status not in ["ACTIVE"]:
    print ("Something went wrong during the image creation\nPlease review the"
           "output below:\n\nID: %s\nName: %s\nStatus: %s\n\n" %
           (img.id, img.name, img.status))
    sys.exit(3)
else:
    print "Image creation complete.  Building server..."

# All is well with the new image, create a new server using it as a template
srv = cs.servers.create(sname, img_id, flavor_id)

# Let's do the progress thing all over again, this time for the server build
sys.stdout.write("[%s]" % (" " * toolbar_width))
sys.stdout.flush()
sys.stdout.write("\b" * (toolbar_width+1)) # return to start of line, after '['

while srv.status in ["BUILD"]:
    progress = int(ceil(srv.progress / 2))
    sys.stdout.write("%s" % ("=" * progress))
    sys.stdout.flush()
    sys.stdout.write("\b" * (progress)) # Reset progress bar
    sleep(5)
    srv = cs.servers.get(srv.id)
print

# Server build has issues, show the status
if srv.status not in ["ACTIVE"]:
    print ("Something went wrong during the server creation\nPlease review the"
           "output below:\n\nID: %s\nName: %s\nStatus: %s\n\n" %
           (srv.id, srv.name, srv.status))
    sys.exit(4)
# All is well, and we're done
else:
    print ("Cloning completed successfully\nServer name: %s\nNetworks: %s" %
          (srv.name, srv.networks))
