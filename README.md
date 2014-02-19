challenges
==========

Rackspace API challenges

Challenge #1
------------
Write a script that builds three 512 MB Cloud Servers following a similar naming convention. (ie., web1, web2, web3) and returns the IP and login credentials for each server.

Challenge #2
------------
Write a script that clones a server (takes an image and deploys the image as a new server).

Challenge #3
------------
Write a script that accepts a directory as an argument as well as a container name. The script should upload the contents of the specified directory to the container (or create it if it doesn't exist). The script should handle errors appropriately (check for invalid paths, etc.)

Challenge #4
------------
Write a script that uses Cloud DNS to create a new A record when passed a FQDN and IP address as arguments.

Challenge #5
------------
Write a script that creates a Cloud Database instance. This instance should contain at least one database, and the database should have at least one user that can connect to it.

Challenge #6
------------
Write a script that creates a CDN enabled container in Cloud Files.

Challenge #7
------------
Write a script that will create 2 Cloud Servers and add them as nodes to a new Cloud Load Balancer.

Challenge #8
------------
Write a script that will create a static webpage served out of Cloud Files. The script must:

* Create a new container
* CDN enable the container
* Configure the container to serve an index page
* Create an index page object
* Upload the object to the container
* Create a CNAME record pointing to the CDN URL of the container

Challenge #9
------------
Write an application that when passed the arguments FQDN, image, and flavor it creates a server of the specified image and flavor with the same name as the FQDN, and creates a DNS entry for the FQDN pointing to the server's public IP address.

Challenge #10
-------------
Write an application that will:

* Create 2 servers, supplying a public SSH key to be located in /root/.ssh/authorized_keys
* Create a load balancer
* Add the 2 servers to the LB
* Set up a load balancer monitor and custom error page
* Create a DNS record based on a FQDN for the load balancer virtual IP
* Write the error page HTML source to an object in Cloud Files (creating a backup)