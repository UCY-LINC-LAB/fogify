+++
title = "Node Profiles"
description = ""
weight = 4
+++

## Description

The `Nodes` section is used to define Fog resources. 
A fog infrastructure is composed of machines with various resource capabilities from low processing power machines, 
like Raspberries, to public cloud VMs, like Amazon's EC2. 
To capture this heterogeneity `Nodes`
section allows users to describe the resource characteristics of a physical or 
virtual host, including properties for the `Processor`, `Memory`, and `Storage`.  
Users can determine multiple different Node profiles, 
which can be used in multiple Fog instances at the instantiation phase.

Following, we demonstrate how a raspberry pi 3b can be described:

{{< code lang="yaml" >}}
nodes:
- name: raspberry_pi_3_B
  capabilities:
    processor:
      cores: 4
      clock_speed: 1400
    memory: 1G
    disk: 
        type: SDcard
        size: 8G
        read: 95MB/s
        write: 90MB/s
{{</code>}}
## Parameters

### Name
`Name` is the identifier of the node profile. Users use `name` to specify which fog node has the specific node capabilities. 

### Capabilities
#### Processor
`Processor` characterizes the CPU capabilities of the current node profile. Specifically, users defines the `cores` 
that is the number of CPU's cores and the `clock_speed` that is the CPU frequency. 
By default, the units of `clock_speed` is the megahertz and the user should not define them.
After the deployment, Fogify translates the latter into the `cgroup` constraints, dedicated for each running container.
  
#### Memory
Similarly with processor tag, `memory` specifies the amount of RAM that a Fog node is equipped with. 
The available units of memory property is `G` for gigabyte and `M` for megabyte.

#### Disk
`Disk` defines the node's characteristics related to storage properties. 
With `disk` users can set the `type` of storage device (possible values are: `SDcard`, `SSD`, `HDD`), 
its `size` of storage in gigabyte (`G`) or megabyte (`M`), `read` and `write` speed in `MB/S`.

{{< panel style="info">}} 
In current version of Fogify, `disk` properties do not effect the deployment. 
We are working on that feature and we will provide it in near future.
 {{< /panel >}}