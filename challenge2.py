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
import novaclient.exceptions
from math import ceil
from time import sleep

import pyrax
from pyrax import exceptions as e

# Set progress toolbar width (used with image and server creation progress)
TOOLBAR_WIDTH = 50

# Location of pyrax configuration file
CONFIG_FILE = "~/.rackspace_cloud_credentials"

# Identity type to be used (RAX)
IDENTITY_TYPE = "rackspace"

def main():
    """
    Challenge 2
    -- Write a script that clones a server (takes an image and deploys the
       image as a new server)
    """

    p = argparse.ArgumentParser(description=("Cloud Server cloning "
                                                  "application"))
    p.add_argument("source", action="store", metavar="[server ID]", type=str,
                   help=("ID of server to be cloned"))
    p.add_argument("-n", "--name", action="store", required=False,
                   metavar="[clone name]", type=str,
                   help=("Name of cloned server (default appends "
                         "'-copy' to original server name"))
    p.add_argument("-r", "--region", action="store", required=False,
                   metavar="[region]", type=str,
                   help=("Region where servers should be built (defaults"
                         " to 'ORD'"),
                   choices=["ORD", "DFW", "LON", "IAD", "HKG", "SYD"],
                   default="ORD")

    # Parse arguments (validate user input)
    args = p.parse_args()
    
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
        sys.exit(1)
    except e.FileNotFound:
        print "ERROR: Credentials file '%s' not found" % (creds_file)
        sys.exit(2)

    # Use a shorter Cloud Servers class reference string
    # This simplifies invocation later on (less typing)
    cs = pyrax.cloudservers

    # Attempt to locate the server using the ID provided
    try:
        source = cs.servers.get(args.source)
    except:
        print ("ERROR: Could not find server with ID '%s'\nPlease check "
               "and try again" % (args.server))
        sys.exit(3)    

    # Set the clone name if provided, or append default string to source name
    dest_name = args.name if args.name else source.name + "-copy"
    
    # Attempt to kick off the image build, freak out if it's already in
    # progress
    try:
        img_id = cs.servers.create_image(source.id, dest_name)
        print "Server image creation in progress..."
    except novaclient.exceptions.ClientException as err:
        print "ERROR: Image creation request failed\n%s" % (err)
        sys.exit(4)

    img = cs.images.get(img_id)

    # Show image creation progressing while the status is 'SAVING'
    while img.status in ["SAVING"]:
        sys.stdout.write(".")
        sys.stdout.flush()
        sleep(30)
        img = cs.images.get(img_id)
    print

    # Something is not right with the image creation, bail out gracefully
    if img.status not in ["ACTIVE"]:
        print ("ERROR: Something went wrong during the image creation"
               "Status: %s\n\n"% (img.status))
        sys.exit(5)
    else:
        print "Image creation complete.  Building server..."

    # All is well with the new image, create a new server using it
    # as a template
    srv = cs.servers.create(dest_name, img.id, source.flavor["id"])

    while srv.status in ["BUILD"]:
        sys.stdout.write(".")
        sys.stdout.flush()
        sleep(15)
        srv.get()  # Update server details
    print

    # Server build has issues, show the status
    if srv.status not in ["ACTIVE"]:
        print ("Something went wrong during the server creation\nPlease "
               "review the output below:\n\nID: %s\nName: %s\nStatus: %s\n\n"
               % (srv.id, srv.name, srv.status))
        sys.exit(6)
    # All is well
    else:
        print ("Cloning completed successfully\nServer details:\n\tName: %s"
               "\n\tAdmin password: %s\n\tNetworks:\n\t\tPublic #1: %s\n\t\t"
                       "Public #2: %s\n\t\tPrivate: %s"
                       % (srv.name, srv.adminPass, srv.networks["public"][0],
                          srv.networks["public"][1],
                          srv.networks["private"][0]))
                          
    # Remove the clone image and we're done
    try:
        cs.images.delete(img_id)
    except:
        print ("WARNING: Clone image delete request failed\n"
               "Please review and delete manually")


if __name__ == '__main__':
    main()
