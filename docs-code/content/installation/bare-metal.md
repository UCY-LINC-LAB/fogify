+++
title = "Bare-metal Installation"
description = ""
weight = 2
+++

### Dependencies
When we have installed the expected software components, now we have to install the main components of the Fogify System. 
Since Fogify is developed with python, firstly, we install the python libraries with the following command 
(on each Cluster Node): 
{{< code lang="bash" >}}
sudo pip3 install -r requirements.txt
{{< /code >}}

### Fogify Controller (Master)
The Fogify Controller should run on the Cluster's Manager Node. The Controller will receive any request 
and will communicate to the other nodes (Fogify Agents) in order to disseminate the appropriate commands. 

{{< code lang="bash" >}}
 python3  main.py --controller
{{< /code >}}

### Fogify Agent

#### Monitoring

For our initial version of Fogify, 
we utilize an external monitoring agent to endorse our monitoring metrics, namely the cAdvisor. 
Thus, when the Swarm Cluster is up and running, the user should deploy the cAdvisor on 
each Cluster's Node. 
The following command deploys a cAdvisor agent that exposes the monitoring metrics to the 9090 port.


{{< code lang="bash" >}}
#!/usr/bin/env bash
sudo docker run \
  --volume=/:/rootfs:ro \
  --volume=/var/run:/var/run:ro \
  --volume=/sys:/sys:ro \
  --volume=/var/lib/docker/:/var/lib/docker:ro \
  --volume=/dev/disk/:/dev/disk:ro \
  --publish=9090:8080 \
  --detach=true \
  --name=cadvisor \
  google/cadvisor:latest
{{< /code >}}



#### Agent's Installation

A Fogify Agent should run on each Swarm Node in order to apply the specific network characteristics, 
retrieve the monitoring data and employ the stress actions. 
The agent should run with "sudo" because the network actions need admins privileges.

{{< code lang="bash" >}}
sudo python3  main.py --agent
{{< /code >}}





