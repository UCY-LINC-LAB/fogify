+++
title = "Installation"
description = ""
weight = 2
+++


## Installation Modes

Fogify can be installed either directly on cluster nodes, aka as a [bare-metal installation]({{< relref path="./bare-metal.md" >}}), 
or the user can utilize a containerized version of the system written in [docker-compose file]({{< relref path="./as-a-service.md" >}}).
However, for both modes, the **all** cluster nodes should have installed the Requirement Software Components, 
namely, the docker Swarm orchestrator and a network Linux kernel package (iproute).

## Requirement Software Components

### Orchestrator (Swarm Installation)
According to the Orchestration, Fogify needs a pre-installed Docker Swarm Orchestrator. 
With the following command, the user can easily install a Docker Swarm Manager (master Node). 

{{< code lang="bash" >}}
docker swarm init
{{< /code >}}

The latter command will generate a result similar to: 
```
Swarm initialized: current node (dxn1zf6l61qsb1josjja83ngz) is now a manager.

To add a worker to this swarm, run the following command:

    docker swarm join \
    --token SWMTKN-1-49nj1cmql0jkz5s954yi3oex3nedyz0fb0xx14ie39trti4wxv-8vxv8rssmk743ojnwacrr2e7c \
    192.168.99.100:2377

To add a manager to this swarm, run 'docker swarm join-token manager' and follow the instructions.
```



At this time, the Docker Swarm cluster consists of one node which is Manager and Worker. 
If a user needs to add more nodes, he/she can run the following command on each extra node.

{{< code lang="bash" >}}

$ docker swarm join \
    --token SWMTKN-1-49nj1cmql0jkz5s954yi3oex3nedyz0fb0xx14ie39trti4wxv-8vxv8rssmk743ojnwacrr2e7c \
    192.168.99.100:2377
    
{{< /code >}}

### Kernel Network Plugin

Fogify executes some low-level commands in order to apply specific characteristics to the network. 
For this reason, on each cluster node, we should install the traffic control tool (tc-tool). 
On Debian-based destributions, tc-tool comes bundled with iproute, so in order to isntall it you have to run:

{{< code lang="bash" >}}
apt-get install iproute
{{< /code >}}

## Required Parameters

The parameters of the `Fogify` should pass through host's environmental parameter. Specifically, the parameters are the following:

* `MANAGER_NAME`: the relative name of the swarm master node
* `MANAGER_IP`: the manager's IP 
* `HOST_IP`: the machine's IP
* `CPU_OVERPROVISIONING_PERCENTAGE`: a CPU overprovisioning percentage, the default is `0`
* `RAM_OVERPROVISIONING_PERCENTAGE`: a CPU overprovisioning percentage, the default is `0`
* `CPU_FREQ`: The CPU frequency of the host machine

{{< panel style="info">}} 
A user selects a percentage of CPU or RAM overprovisioning, and Fogify will generate two limits: 
an upper limit and a lower limit for each emulated device. 
For instance, a 20% overprovissioning configuration demands the emulated nodes to occupy the 20% less than 
the maximum processing power that the user selected. However, when any node requires extra power, the system will provide it, 
if there are available resources. Generally, the system will 
provide overprovisioning as a share competing portion of `CPU` or `RAM`. 
{{< /panel >}}

{{< panel style="info">}} 
Running `Fogify` through `docker-compose.yaml` the latter parameters may be declared in `.env` file or via command line parameters of `docker-compose up` command.
 {{< /panel >}}