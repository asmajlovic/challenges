challenges
==========

Rackspace API challenges

Challenge #1
------------
Write a script that builds three 512 MB Cloud Servers following a similar naming convention. (ie., `web1`, `web2`, `web3`) and returns the IP and login credentials for each server.

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

* Create 2 servers, supplying a public SSH key to be located in `/root/.ssh/authorized_keys`
* Create a load balancer
* Add the 2 servers to the LB
* Set up a load balancer monitor and custom error page
* Create a DNS record based on a FQDN for the load balancer virtual IP
* Write the error page HTML source to an object in Cloud Files (creating a backup)

Challenge #11
-------------
Write an application that will:

* Create an SSL terminated load balancer (create and make use of a self-signed certificate)
* Create a DNS record that resolves to the load balancer virtual IP
* Create 3 servers and add them to the load balancer
* Each server should have a Cloud Block Storage volume attached to it (size and type are irrelevant)
* All 3 servers should be attached to the same isolated Cloud Network (e.g. `192.168.0.0/16`)
* Login information to all 3 servers should be returned in a readable format, including all connection information (IPs, admin password)

Challenge #12
-------------
Write an application that will create a [route](http://documentation.mailgun.com/user_manual.html#routes) in MailGun, so that when an e-mail is sent to challenge@[YOUR-REGISTERED-MAILGUN-DOMAIN] it calls your Challenge #1 script that builds 3 servers.

Assumptions: 

* Assume that Challenge #1 can be kicked off by accessing http://example.com/challenge1. Obviously this will not work, the idea is to ensure the message is getting posted to the URL in question
* __DO NOT PUT THE API KEY IN YOUR SCRIPT__, instead assume that the Mailgun API key is defined in `~/.mailgunapi`. Assume no formatting, the API key will be the only data in the mentioned file.

Challenge #13
-------------
Write an application that deletes everything in your cloud account (clean up after the previous 12 challenge tasks, if you will).  Unfortunately this is not straightforward to test on accounts being used for other purposes, so printing commands to be executed is acceptable.  The script should attempt to:

* Delete all Cloud Servers
* Delete all custom Cloud Server images
* Delete all Cloud Files containers and objects
* Delete all Cloud Database instances
* Delete all custom Cloud Networks
* Delete all Cloud Block Storage volumes

