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
from novaclient import exceptions as exc

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


def check_lb_status(obj):
    """
    Check LB status and freak out if not active
    """
    # We need to confirm that the LB is active before making any
    # additional changes, 10 second sleep is more than reasonable
    while obj.status not in ["ACTIVE", "ERROR"]:
        sleep(10)
        obj.get()
        
    if obj.status not in ["ACTIVE"]:
        print "ERROR: LB not in an active status"
        exit(14)
    
    return


def main():
    """
    Challenge 10:
    -- Write an application that will:
       -- Create 2 servers, supplying a ssh key to be installed at
          /root/.ssh/authorized_keys.
       -- Create a load balancer
       -- Add the 2 new servers to the LB
       -- Set up LB monitor and custom error page. 
       -- Create a DNS record based on a FQDN for the LB VIP. 
       -- Write the error page html to a file in Cloud Files for backup.
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
    
    # Compile a list of available LB algorithms (similar to above)
    ALGORITHM_LIST = [
                      "LEAST_CONNECTIONS",
                      "RANDOM",
                      "ROUND_ROBIN",
                      "WEIGHTED_LEAST_CONNECTIONS",
                      "WEIGHTED_ROUND_ROBIN"
                     ]

    # Define the script parameters (all are optional for the time being)
    p = argparse.ArgumentParser(description=(
        "Provisioning Cloud Servers behind HTTP LB with health checks and "
        "custom error page, as well as A record resolving to LB IP address"))
    p.add_argument("fqdn", action="store", type=str, metavar="[fqdn]",
                   help="Fully qualified domain name for A record")
    p.add_argument("ssh_key", type=str, metavar="[ssh public key]",
                   help=("SSH public key file to be placed in "
                         "/root/.ssh/authorized_keys"))
    p.add_argument("-x", "--prefix", action="store", required=False,
                   metavar="[server name prefix]", type=str,
                   help=("Server name prefix (defaults to 'server' e.g."
                         " server-1, server-2, ...)"), default="server-")
    p.add_argument("-f", "--flavour", action="store", required=False,
                   metavar="[server flavour]", type=str,
                   help=("Server flavor (RAM size in MB, defaults to "
                         "'1 GB Performance'"), choices=FLAVOUR_LIST,
                   default="1 GB Performance")
    p.add_argument("-i", "--image", action="store", required=False,
                   metavar="[server image]", type=str,
                   help=("Image name to be used in server build (defaults to "
                         " 'Debian 7')"), default="Debian 7 (Wheezy)")
    p.add_argument("-c", "--count", action="store", required=False,
                   metavar="[server count]", type=int,
                   help="Number of servers to build (defaults to 2)",
                   choices=xrange(1,11), default=2)
    p.add_argument("-n", "--lb-name", action="store", required=False,
                   metavar="[lb name]", type=str,
                   help=("Preferred LB name (defaults to server prefix"
                         " with 'lb' appended)"))
    p.add_argument("-v", "--lb-vip-type", action="store", required=False,
                   metavar="[vip type]", type=str,
                   help=("Virtual IP address type - PUBLIC or SERVICENET "
                         "(defaults to PUBLIC)"),
                   choices=["PUBLIC","SERVICENET"], default="PUBLIC")
    p.add_argument("-a", "--algorithm", action="store", required=False,
                   metavar="[lb algorithm]", type=str,
                   help="Load balancing algoritm (defaults to RANDOM)",
                   choices=ALGORITHM_LIST, default="RANDOM")
    p.add_argument("-p", "--service-port", action="store", required=False,
                   metavar="[lb port]", type=int,
                   help="LB HTTP service port (defaults to 80)", default=80)
    p.add_argument("-o", "--container", action="store", required=False,
                   metavar="[container name]", type=str,
                   help=("Container name where LB error page (error.html) "
                         "should be backed up (default 'lb-page-backup')"),
                   default="lb-page-backup")
    p.add_argument("-t", "--ttl", action="store", required=False,
                   metavar="[ttl value]", type=int,
                   help=("TTL for the DNS A record (default %d seconds)"
                            % (DEFAULT_TTL)),
                   default=DEFAULT_TTL)
    p.add_argument("-r", "--region", action="store", required=False,
                   metavar="[region]", type=str,
                   help=("Region where container should be created"
                         " (defaults to 'ORD'"),
                   choices=["ORD", "DFW", "LON", "IAD", "HKG", "SYD"],
                   default="ORD")

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
    
    # Confirm that the SSH public key file exists and looks correctly
    # formatted (presence of 'ssh-' somewhere in the file)
    #    NOTE: I suspect this string check can be handled better
    try:
        f = open(os.path.expanduser(args.ssh_key), "r")
        ssh_key = f.read()
        f.close()
        
        if "ssh-" not in ssh_key:
            print ("ERROR: SSH public key does not appear to be "
                   "correctly formatted.")
            exit(3)
        else:
            files = {"/root/.ssh/authorized_keys": ssh_key}
    except IOError:
        print ("ERROR: SSH public key file (%s) not found"
               % (args.ssh_key))
        exit(4)

    # Define the authentication credentials file location and request that pyrax
    # makes use of it. If not found, let the client/user know about it.

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
        exit(5)
    except e.FileNotFound:
        print "ERROR: Credentials file '%s' not found" % (creds_file)
        exit(6)

    # Use a shorter Cloud Servers and LB class reference strings
    # This simplifies invocation later on (less typing)
    cs = pyrax.cloudservers
    cf = pyrax.cloudfiles
    clb = pyrax.cloud_loadbalancers
    dns = pyrax.cloud_dns
    
    # Locate the image to build from (confirm it exists)
    try:
        image = [i for i in cs.images.list() if args.image in i.name][0]
    except:
        print ("ERROR: Image name provided was not found. Please check "
               "and try again")
        exit(7)

    # Grab the flavor ID from the RAM amount selected by the user.
    # The server create request requires the ID rather than RAM amount.
    try:
        flavour = [f for f in cs.flavors.list() if args.flavour in f.name][0]
    except:
        print ("ERROR: Flavor name provided has not matched any entries. "
               "Please check and try again.")
        exit(8)

    # Grab zone list
    domains = zone_list(dns)

    # No zones found, inform that one needs to be created and exit
    if len(domains) == 0:
        print "ERROR: You have no domains/zones at this time"
        print "Please create one first then try again"
        exit(9)

    # Attempt to locate the zone extracted from FQDN string
    try:
        zone = [i for i in domains if zone_name in i.name][0]
    except:
        print "ERROR: Zone '%s' not found" % (zone_name)
        print "Please check/create and try again"
        exit(10)
    
    # Determine the LB name from the args provided
    lbname = args.lb_name if args.lb_name else args.prefix + "lb"

    print ("\nINFO:Build requests initiated\n"
           "\tTIP: You may wish to check available options by issuing "
           "the -h flag")

    # Print the image ID and name selected, as well as server count
    print "\n-- Image details\n\tID: %s\n\tName: %s" % (image.id, image.name)
    print ("\n-- Server build details\n\tPrefix: %s\n\tFlavour: %s"
           "\n\tCount: %d" % (args.prefix, args.flavour, args.count))

    # Server list definition to be used in tracking build status/comletion
    servers = []

    # Iterate through the server count specified, sending the build request
    # for each one in turn (concurrent builds)
    for count in xrange(args.count):
        # Issue the server creation request with the SSH key included
        try:
            srv = cs.servers.create(args.prefix + str(count + 1),
                                    image.id, flavour.id, files=files)
        # SSH key too large, fail
        except exc.OverLimit:
            print "ERROR: SSH public key exceeds permitted size"
            exit(11)
        
        # Add server ID from the create request to the tracking list
        servers.append(srv)

    # Prepare a list for all active servers, since failed entries will
    # not be removed as we do not have health checks defined just yet
    srv = []

    # Check on the status of the server builds. Completed or error/unknown
    # states are removed from the list until nothing remains.
    while servers:
        # Track the element position for easier/efficient removal
        count = 0
        for server in servers:
            # Get the updated server details
            server.get()
            # Should it meet the necessary criteria, provide extended info
            # and remove from the list
            if server.status in ["ACTIVE", "ERROR", "UNKNOWN"]:
                print ("\n-- Server details\n\tName: %s\n\tStatus: %s"
                       "\n\tAdmin password: %s"
                      % (server.name, server.status, server.adminPass))
                print ("\tNetworks:\n\t\tPublic #1: %s\n\t\t"
                       "Public #2: %s\n\t\tPrivate: %s"
                       % (server.networks["public"][0],
                          server.networks["public"][1],
                          server.networks["private"][0]))
                # Failed build, state so to the client/user
                if server.status not in ["ACTIVE"]:
                    ERRORS = True
                    print "WARN: Build process for %s failed" % (server.name)
                # Otherwise append to the active list to be added to the LB
                else:
                    srv.append(server)
                del servers[count]
            count += 1
        # Reasonable wait period between checks
        sleep(15)

    # Check if we have active servers, no point in proceeding if there
    # are none since at least a single instance is required to create
    # an LB
    if len(srv) == 0:
        print "ERROR: No servers in an active state, cannot create LB"
        exit(12)
    else:
        # Otherwise, prepare and add all active nodes
        nodes = []
        for server in srv:
            nodes.append(clb.Node(address=server.networks["private"][0],
                                  port="80"))

        # Define the VIP type based on argument provided by client/user
        vip = clb.VirtualIP(type=args.lb_vip_type)
        
        # Create the LB
        print "INFO: Creating the load balancer"
        lb = clb.create(lbname, port=args.service_port, protocol="HTTP",
                        nodes=nodes, virtual_ips=[vip])
        
        # Wait for LB to settle down into active status
        check_lb_status(lb)
        
        # Add a CONNECT health monitor for the nodes
        lb.add_health_monitor(type="CONNECT", delay=10, timeout=5,
                              attemptsBeforeDeactivation=3)

        # Another check for status before we add the custom error page
        lb.get()
        check_lb_status(lb)
        
        # Add a custom LB error page
        html = ("<html><head><title>Application error</title></head><body>"
                "Something is not quite right here!</body></html>")
        
        lb.set_error_page(html)

        # Print LB details
        public_ips = [vip.address for vip in lb.virtual_ips]
        print ("\n-- LB details --\n\tName: %s\n\tPort: %s\n\t"
               "Algorithm type: %s\n\tNode count: %s"
                % (lb.name, lb.port, lb.algorithm, len(lb.nodes)))
        count = 1
        for ip in public_ips:
            print "\tIP address #%d: %s" % (count, ip)
            count += 1

        # Determine the LB IPv4 address to be used in the A record
        count = 0
        ip = public_ips[count]

        while not is_valid_ipv4(ip):
            count += 1
            ip = public_ips[count]
        
        # Attempt to add the new A record
        a_rec = {"type": "A",
                "name": args.fqdn,
                "data": ip,
                "ttl": ttl}

        try:
            rec = zone.add_record(a_rec)
            print ("\n-- Record details\n\tName: %s\n\tType: %s\n\tIP address: "
                   "%s\n\tTTL: %s") % (rec[0].name, rec[0].type, rec[0].data,
                   rec[0].ttl)
        except e.DomainRecordAdditionFailed as err:
            print "ERROR: Record addition request failed:", err
            exit(13)

        # Save the error page to a CF container (backup)
        try:
            print "\nINFO: Checking if backup container already exists..."
            cont = cf.get_container(args.container)
        except:
            cont = None

        # Container not found, create it and CDN enable
        if cont is None:
            try:
                print ("INFO: Container '%s' not found, creating..."
                       % (args.container))
                cont = cf.create_container(args.container)
            except:
                print "ERROR: Could not create CF container", args.container
                ERRORS = True
        else:
            print "INFO: Container found, back up in progress..."
                    
        # Write the error HTML to a temp file and upload to CF container
        # (should it have been created successfully of course)
        if cont:
            with pyrax.utils.SelfDeletingTempfile() as custom_error_file:
                with open(custom_error_file, "w") as tmp:
                    tmp.write(html)
                    filename = os.path.basename(custom_error_file)
                    cf.upload_file(cont, custom_error_file,
                                   content_type="text/html")
                
                    print ("INFO: Custom error page backed up to '%s'"
                            % (args.container + "/" + filename))
            
        # All done
        exit_msg = "\nINFO: Build requests completed"
        if ERRORS:
            print "%s - with errors (see above for details)" % (exit_msg)
        else:
            print "%s" % (exit_msg)


if __name__ == '__main__':
    main()
