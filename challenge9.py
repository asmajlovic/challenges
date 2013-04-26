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
import socket
import sys
from time import sleep

import pyrax
from pyrax import exceptions as e

# Determine whether or not the IPv4 address provided is correctly structured
def is_valid_ipv4(address):
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

# Use a shorter Cloud Servers and DNS class reference strings
# This simplifies invocation later on (less typing)
cs = pyrax.cloudservers
dns = pyrax.cloud_dns

# Intro/description
print ("-- Server build from image and flavor - creating a FQDN DNS record "
       "in the process")

# Grab a list of available images and flavors
images = cs.list_images()
flavors = cs.list_flavors()

# Compile the list of images and flavors for simple selection
srv_img_dict = {}
srv_flav_dict = {}

# Ask the user to pick the image to use
for pos, img in enumerate(images):
    print "%2d) %s" % (pos, img.name)
    srv_img_dict[str(pos)] = img.id

img_sel = None
while img_sel not in srv_img_dict:
    if img_sel is not None:
        print "   -- Invalid choice"
    img_sel = raw_input("-- Select the image to use: ")

# Ask the user to pick the flavor to use
for pos, flav in enumerate(flavors):
    print "%2d) %s [%s GB disk]" % (pos, flav.name, flav.disk)
    srv_flav_dict[str(pos)] = flav.id

flav_sel = None
while flav_sel not in srv_flav_dict:
    if flav_sel is not None:
        print "   -- Invalid choice"
    flav_sel = raw_input("-- Select the flavor to use: ")

# Map to image and flavor IDs
img_id = srv_img_dict[img_sel]
flav_id = srv_flav_dict[flav_sel]

# Grab the server name
sname = raw_input("Please enter the FQDN for server name and DNS A record: ")

# Attempt to build the server and track progress
print "Building server..."
srv = cs.servers.create(sname, img_id, flav_id)

while srv.status in ["BUILD"]:
    sys.stdout.write(".")
    sys.stdout.flush()
    sleep(5)
    srv = cs.servers.get(srv.id)
print

# Server build has issues, show the status
if srv.status not in ["ACTIVE"]:
    print ("Something went wrong during the server creation\nPlease review the"
           "output below:\n\tID: %s\n\tName: %s\n\tStatus: %s\n" %
           (srv.id, srv.name, srv.status))
# All is well with the server build
else:
    print ("Server networks:\n\tPublic #1: %s\n\tPublic "
           "#2: %s\n\tPrivate: %s\n"
           % (srv.networks["public"][0],
              srv.networks["public"][1],
              srv.networks["private"][0]))

# Public IP address order is not standard, need to grab the IPv4 entry
#    NOTE: This can be approached better, will need to review later
count = 0
ip = srv.networks["public"][count]

while not is_valid_ipv4(ip):
    count += 1
    ip = srv.networks["public"][count]

# Attempt to create the zone from the FQDN provided
try:
    zone = dns.create(name=sname, emailAddress="pyrax@example.com",
            ttl=300, comment="Sample domain")
except e.DomainCreationFailed as err:
    print "Domain creation failed:", err

# Define and attempt to add the new A record
a_rec = {"type": "A",
        "name": sname,
        "data": ip,
        "ttl": 300}

# Attempt to add the A record and we're done
try:
    rec = zone.add_record(a_rec)
    print ("-- Record details\n\tName: %s\n\tType: %s\n\tIP address: %s\n\t"
           "TTL: %s") % (rec[0].name, rec[0].type, rec[0].data, rec[0].ttl)
    print "Process complete"
except e.DomainRecordAdditionFailed as err:
    print "Record creation failed:", err
