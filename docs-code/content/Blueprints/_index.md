+++
title = "Blueprints"
description = ""
weight = 6
+++

## Description

`Topology` element is a combination of a `node`, a `service`, attached `networks` and a replication factor (`replicas`). 
Finally, each node has a `label` which represents the name of the node at the deployed dockerized application. 
In the following example we have three `node-sm` nodes connected to the `internet` network (with specific connectivity characteristics) 
that will execute the `nimbus` and `supervisor` services respectively.

{{<code lang="yaml">}}
    topology:
        - node: node-sm  # Node template as described in Node profiles
          service: nimbus  # Service as described in docker-compose services
          label: nimbus  # label/identifier of the emulated fog node 
          replicas: 1  # replication factor of the node
          networks:  # a list of the networks that the node is connected to
            - internet
        - node: node-sm
          service: supervisor
          label: supervisor
          replicas: 2
          networks:
            - internet
{{</code >}}

## Parameters

### Label
`Label` is the identifier of the `blueprint`. 
Users can use the `label` to specify the instances for injecting `actions` and `scenarios`. 
Furthermore, users can include a number after the `label` to identify specific replica of the blueprint, e.g `supervisor.1`. 

### Service
`Service` is the executable that will run on the Fog node. 
The `service` is inherited from `services` section of the `docker-compose` specification.
For more details check out the following [link]().

### Node
Specifies on which emulated device the service will run on. The emulated node inherits the `capabilities` of `node profile`. 
For more details check out the following [link]().

### Replicas
`Replicas` identifies the number of instances that Fogify will create from the specific `blueprint`.
 All instances will have the same processing characteristics, execute the same service and are connected on the same networks.

### Networks

This section provides information about node networking. Specifically, users select in which `networks` the `blueprint` will be connected.
For instance, at the before-mentioned example, `supervisor` nodes will be connected to the `internet` network with default network connectivity QoS.
If there is a need for node-specific network QoS, user can override them. Following example illustrates how do users override the network QoS.

 {{<code lang="yaml">}}
....
        - node: node-sm
          service: supervisor
          label: supervisor
          replicas: 2
          networks:
            - name: internet
              uplink:
                bandwidth: 1Mbps
                latency:
                  delay: 200ms
                drop: 0.01%
              downlink:
                bandwidth: 1Mbps
                latency:
                  delay: 200ms
                drop: 0.01%
....
{{</code >}}

{{< panel style="info">}} 
Currently, user has to determine again all network properties again, even if the desired properties are the same with default.
{{< /panel >}}