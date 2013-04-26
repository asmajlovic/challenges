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
from math import ceil
from time import sleep

import pyrax
from pyrax import exceptions as e

# Set upload progress toolbar width
toolbar_width = 50

# Function to return current zones under the account in question
def zone_list(obj):
    # Use a paginated request format, in case there is a significant zone count
    page_size = 25
    count = 0

    # Determine if any zones actually exist under the account, if not, request
    # that one be created
    doms = obj.list(limit=page_size)
    count += len(doms)

    # Loop until all zones have been considered
    while True:
        try:
            doms = obj.list_next_page()
            count += len(doms)
        except e.NoMoreResults:
            break

    # Return the domains and count
    return (doms, count)

# We may be asking for a TTL a few times, here's the function to handle it
def get_ttl(rec_type):
    ttl = None
    
    while not ttl:
        try:
            ttl = int(raw_input("Please enter the %s record TTL (in seconds): "
                                 % (rec_type)))
            # User could potentially provide a negative integer, check to make
            # sure TTL is at least 300 seconds
            if ttl < 300:
                print "Invalid selection. TTL must be at least 300s (5 min)"
                ttl = None
        except ValueError:
            print "TTL must be a positive integer >300, please try again."
    return ttl

# Parse script parameters
parser = argparse.ArgumentParser(description=("Create a Cloud Files static "
                                              "web site from a local "
                                              "folder/directory"))
parser.add_argument("-d", "--directory", action="store",
                    required=True, type=str,
                    help="Local directory to upload content from")
parser.add_argument("-c", "--container", action="store",
                    required=True, type=str,
                    help="Container name where content should be uploaded")
parser.add_argument("-t", "--ttl", action="store", required=False, type=int,
                    help=("CDN TTL (in seconds) for the container "
                          "(default 900 seconds)"), default=900)
parser.add_argument("-i", "--index", action="store", required=False, type=str,
                    help="Static web index file (default 'index.html')",
                    default="index.html")

args = parser.parse_args()

# Determine if the upload directory exists
if not os.path.isdir(args.directory):
    print ("ERROR: Specified directory (%s) does not exist, please check "
           "the path and try again)" % (args.directory))
    sys.exit(1)

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

# Use a shorter Cloud Files and DNS class reference strings
# This simplifies invocation later on (less typing)
cf = pyrax.cloudfiles
dns = pyrax.cloud_dns

# Determine if container already exists, otherwise create it
try:
    print "Checking if container exists..."
    cont = cf.get_container(args.container)
except:
    cont = None

# Container not found, create it and CDN enable
if cont is None:
    try:
        print ("Container '%s' does not exist, creating"
               % (args.container))
        cont = cf.create_container(args.container)
        print "Setting CDN TTL to %s seconds" % (args.ttl)
        cont.make_public(ttl=args.ttl)
    except:
        print "ERROR: Could not create container", args.container
        sys.exit(1)
# Otherwise print the current CDN TTL associated with the existing container
else:
    print ("Container '%s' already exists - continuing with upload" %
           (cont.name))

# Set the static web index file (metadata/header)
print "Setting static web index file to", args.index
meta = {"X-Container-Meta-Web-Index": args.index}
cf.set_container_metadata(cont, meta)

# Check and confirm if the index file exists, otherwise create a placeholder
# and inform/warn the client of the action
index_file = args.directory + "/" + args.index
if not os.path.isfile(index_file):
    print "Index file '%s' not found, creating a placeholder" % (index_file)
    f = open(index_file,'w')
    f.write("Index page placeholder\n")
    f.close()

# Grab a list of domains/zones
(domains, count) = zone_list(dns)

# No zones found, request that one be created
if count == 0:
    print "You have no domains/zones at this time"
    zone_name = raw_input("Please enter a zone name to create: ")
    emailadd = raw_input("Please enter an e-mail contact for the zone: ")
    ttl = get_ttl("NS")
    # Try and create the new zone
    try:
        zone = dns.create(name=zone_name, emailAddress=emailadd,
                ttl=ttl, comment="Created through pyrax")
    except e.DomainCreationFailed as err:
        print "Zone creation failed:", err
    print "Zone created:", zone.name
# Zones found, enumerate and request client/user selects which one to use
else:
    print "Available zones/domains:"
    for pos, zn in enumerate(domains):
        print "%2d) %s" % (pos, zn.name)
    # Keep requesting until a valid selection is made
    zone = None
    while not zone:
        try:
            val = int(raw_input("Select a zone to add CNAME record to: "))
            # User could potentially provide a negative integer, which will
            # still be a valid index reference - including a crude catch here
            if val < 0:
                print "Invalid selection. Please try again."
                zone = None
            else:
                zone = domains[val]
        except IndexError:
            print "Invalid selection. Please try again."
        except ValueError:
            print "Selection must be an integer listed, please try again."

# We have determineded where the record needs to be added, request the
# CNAME and TTL from the user/client
prefix = None
while not prefix:
    prefix = raw_input("Please enter the prefix for the record (e.g. 'cdn'): ")

cname = prefix + "." + zone.name
ttl = get_ttl("CNAME")
dest = cont.cdn_uri.replace("http://", "")

# Attempt to create the new CNAME record
cname_rec = {"type": "CNAME",
        "name": cname,
        "data": dest,
        "ttl": ttl}

try:
    rec = zone.add_record(cname_rec)
    print ("-- Record details\n\tName: %s\n\tType: %s\n\tDestination: %s\n\t"
           "TTL: %s") % (rec[0].name, rec[0].type, rec[0].data, rec[0].ttl)
    print "Record added"
except e.DomainRecordAdditionFailed as err:
    print "Record creation failed:", err

# Start the upload
print "Beginning directory/folder upload"
(upload_key, total_bytes) = cf.upload_folder(args.directory, cont)

# Inform the user of the total upload size
print ("Total upload size: %d bytes (%.2f MB)"
       % (total_bytes, total_bytes / 1024.0 / 1024))

# Prepare progress toolbar
sys.stdout.write("[%s]" % (" " * toolbar_width))
sys.stdout.flush()
sys.stdout.write("\b" * (toolbar_width+1)) # return to start of line, after '['

# Print the upload progress (1 second interval)
uploaded = 0
while uploaded < total_bytes:
    uploaded = cf.get_uploaded(upload_key)
    progress = int(ceil((uploaded * 100.0) / total_bytes / 2))
    sys.stdout.write("%s" % ("=" * progress))
    sys.stdout.flush()
    sys.stdout.write("\b" * (progress)) # Reset progress bar
    sleep(1)
print

# Upload completed, confirm/print object count
nms = cf.get_container_object_names(cont)
print "Number of objects uploaded: %d" % (len(nms))
print "Upload complete"
