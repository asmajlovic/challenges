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

# Determine whether or not the IPv4 address provided is correctly structured
def is_valid_ipv4(address):
    try:
        addr = socket.inet_pton(socket.AF_INET, address)
    except AttributeError:
        try:
            addr = socket.inet_aton(address)
        except socket.error:
            print "Invalid IP address specified, please try again"
            return False
        return address.count('.') == 3
    except socket.error:
        print "Invalid IP address specified, please try again"
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
    exit(1)
except e.FileNotFound:
    print "ERROR: Credentials file '%s' not found" % (creds_file)
    exit(1)

# Use a shorter Cloud DNS class reference string
# This simplifies invocation later on (less typing)
dns = pyrax.cloud_dns

# Intro and check for zones
print "-- Application to add an A record to Cloud DNS zone"
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
            val = int(raw_input("Select a zone to add A record to: "))
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
            print "Selection must be an integer listed above, please try again."

# We have determineded where the record needs to be added, request the
# subdomain from the user/client
print "Subdomain prefix required to complete the record creation"
print "\tIt will be added to the zone selected/created above"
prefix = raw_input("Please enter the prefix for the record (e.g. 'mail'\n"
                    "\tor nothing/<RETURN> if it is the base record): ")

# Determine if a prefix was provided and adjust accordingly
if prefix:
    subdomain = prefix + "." + zone.name
else:
    subdomain = zone.name

# Grab the IPv4 address and ttl for the new record
ip = raw_input("Please enter a valid IPv4 address to resolve to: ")
while not is_valid_ipv4(ip):
    ip = raw_input("Please enter a valid IPv4 address to resolve to: ")

ttl = get_ttl("A")

# Attempt to create the new A record
a_rec = {"type": "A",
        "name": subdomain,
        "data": ip,
        "ttl": ttl}

try:
    rec = zone.add_record(a_rec)
    print ("-- Record details\n\tName: %s\n\tType: %s\n\tIP address: %s\n\t"
           "TTL: %s") % (rec[0].name, rec[0].type, rec[0].data, rec[0].ttl)
    print "Complete"
except e.DomainRecordAdditionFailed as err:
    print "Record creation failed:", err
