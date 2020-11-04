+++
title = "Fogify in Docker-compose"
description = ""
weight = 1
+++

### Execution

To ease the installation of Fogify, we created a docker-compose file that contains a dockerized version of Fogify connected
with a Jupyter server, which is used as a web-based GUI.
Since, the Fogify and Jupyter stack is provided as dockerized services, 
we only need to run the following command at the swarm master node. 

{{< code lang="bash" >}}
sudo docker-compose -p fogemulator up
{{</ code >}}
In order to open the web interface of Jupyter, you have to find the output of the `ui` service 
where the system outputs the `url` and the `token` 

![Jupyter Notebook](/fogify/jupyter.png)

For instance, in previous output we can open the Jupyter interface with the following url:
{{< code lang="bash" >}}
http://127.0.0.1:8888/?token=1cd2e914cd03e76d551a666cb0a8dcdb6361bc29ddf54eed
{{</ code >}}

If we have more nodes in the cluster, we have to execute the following command on every node.

{{< code lang="bash" >}}
sudo docker-compose -p fogemulator up agent cadvisor
{{</ code >}}

For both modes, users should provide a set of parameters to compose file (written in .env file), specificaly:
{{< code lang="bash" >}}
MANAGER_NAME=.... #The name of the swarm master node
MANAGER_IP=192.168.1.1 #The IP of the swarm master node
HOST_IP=192.168.1.1 #The IP of the host
CPU_OVERPROVISIONING_PERCENTAGE=... # A percentage of cpu over provisioning 0-100
RAM_OVERPROVISIONING_PERCENTAGE=... # A percentage of memory over provisioning 0-100 
CPU_FREQ= ... # The frequency of the underlying CPU 
VERSION=.... #The version of Fogify
{{</ code >}}

### Docker-compose file
Next, we have the docker-compose file of Fogify system. The `fogify` and `fogify-jupyter` 
are images upload to docker-hub.  

{{< code lang="yaml" >}}
version: '3.7'

services:

  ui:
    image: fogemulator/fogify-jupyter:${VERSION}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /usr/bin/docker:/usr/bin/docker
    ports:
      - 8888:8888
    environment:
      - "JUPYTER_ENABLE_LAB=yes"
      - "GRANT_SUDO=yes"
    user: root
  controller:
    build: .
    image: fogemulator/fogify:${VERSION} 
    entrypoint: [ "python", "/code/fogify/main.py", "--controller"]
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /usr/bin/docker:/usr/bin/docker
    ports:
      - 5000:5000
    extra_hosts:
      - ${MANAGER_NAME}:${MANAGER_IP}
  agent:
    image: fogemulator/fogify:${VERSION}
    entrypoint: [ "python", "/code/fogify/main.py", "--agent", "--agent-ip", "${HOST_IP}"]
    extra_hosts:
      - ${MANAGER_NAME}:${MANAGER_IP}
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
      - /usr/bin/docker:/usr/bin/docker
      - /proc/:/proc/
      - /var/run/docker/:/var/run/docker/
      - /sys/class/net/:/sys/class/net/
      - /usr/bin/nsenter:/usr/bin/nsenter
      - /lib/modules:/lib/modules
      - /sbin/modprobe:/sbin/modprobe
    privileged: true
    cap_add:
      - ALL
    depends_on:
      - cadvisor
      - controller
    ports:
      - 5500:5500
    environment:
      CONTROLLER_IP: ${MANAGER_IP}

  cadvisor:
    image: gcr.io/google-containers/cadvisor:v0.35.0
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
      - /dev/disk/:/dev/disk:ro
    ports:
      - 9090:8080
    expose:
      - 8080
{{</ code >}}