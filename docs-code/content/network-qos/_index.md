+++
title = "Network QoS"
description = ""
weight = 5
+++

## Description
We consider that an application spans on different nodes and sites through one or more network connections. 
There could be significant heterogeneity in the upward and downward links due to widely different link capacities. 
In our model, one specifies multiple parameters for network connectivity like delay, packet loss rate, packet corruption, etc.
{{<code lang="yaml">}}
    networks:
    - name: internet
      uplink:
        bandwidth: 10Mbps
        latency:
          delay: 20ms
        drop: 0.01%
      downlink:
        bandwidth: 10Mbps
        latency:
          delay: 20ms
        drop: 0.01%
{{</code>}}
## Parameters

### Name
`Name` is the identifier of the network profile. Users use `name` to specify which fog node is connected to specific networks. 

### Uplink & Downlink

Fogify provides users the ability to define different `uplink` and `downlink` characteristics. 
Specifically, users can define network `latency`, `bandwidth` and `drop` packet rate. 
We should note here that if a user would like to determine a general characteristic between two nodes, 
user has to specify both `uplink` and `downlink`. For instance, if the network delay between two nodes, A and B, is `6ms` 
user should determine `3ms` uplink and `3ms` downlink in both nodes. 
The measurement unit of `bandwidth` is `Mbps` while the `drop` rate is determined by a percentage (e.g. `0.1%`). 
The next subsection illustrates the network `latency` definition since it can be much more complex than `bandwidth` or `drop` rate.
 
### Network Latency
`Latency` is composed of the average network `delay` and the optional properties of `deviation`, 
which is the deviation between the mean and the max/min values of the delay, and the `correlation`, which determines the
maximum percent of difference between previous delay value and the current one. 
Both `delay` and `deviation` are measured in `ms`.
Finally, users can determine the `distribution`
of the delay's values. The by-default available distributions are `uniform`, `gaussian`, `pareto` and `paretonormal`, however,
users can upload their own ping delay traces and the system generates any custom distribution [TODO add link]()

{{<code lang="yaml">}}
...
        latency:
          delay: 20ms
          deviation: 5ms
          correlation: 20%
          distribution: uniform
...
{{</code>}}

### Capacity
`Capacity` restricts the number of connected devices on a network. 

{{< panel style="info">}} 
In current version of Fogify, `Capacity` does not effect the deployment. 
We are working on that feature and we will provide it in near future.
 {{< /panel >}}

### Links
With `links` users are able to define specific characteristics on top of packets that transfer between pears of emulated nodes. 
The definition of a `link`, user should define the `from_node` property that determines the source of the packets,
`to_node` property that specifies the destination of the packets, and the `properties`, which are the similar as the network properties.
A boolean optional field, named `bidirectional`, determines if a similar rule will be applied to the `from_node` to `to_node` link.

{{<code lang="yaml">}}
...
    networks:
    - name: internet
      uplink:
        bandwidth: 10Mbps
        latency:
          delay: 20ms
        drop: 0.01%
      downlink:
        bandwidth: 10Mbps
        latency:
          delay: 20ms
        drop: 0.01%
      links:
        from_node: "cloud-server"
        to_node: "mec-svc-1"
        bidirectional: true
        properties:
            latency:
              delay: 200ms
...
{{</code>}}

The latter example illustrates a bidirectional link between `cloud-server` node and `mec-svc-1` node is `200ms`. 
