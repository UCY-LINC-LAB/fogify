+++
title = "Network Slice Modeling"
description = ""
weight = 2
+++

Users in 5G-Slicer are able to introduce network slices under the Fogify's `networks` primitive.
The model of network slices include the `name`, which is the identifier of the network slice, 
the `network_type` that is always should be `slice`, `midhaul_qos` that is the connectivity QoS among RUs and Edge nodes,
`backhaul_qos` that is the QoS connectivity between cloud-enabled core and edge, 
RU to UE connection type (`wireless_connection_type`) along with its `parameters`, and optional property `network_functions` of the network functions (or VNFs),
that includes the Fogify's [firewall rules](/fogify/network-qos.html#firewall-rules) (`firewall_rules`) and the [packet level monitoring](/fogify/network-qos.html#packet-level-monitoring) capability (`packet_level_monitoring`).

{{<code lang="yaml">}}
networks:
  - name: 'slice_name'
    network_type: slice
    midhaul_qos:
      ....
    backhaul_qos:
      ....
    wireless_connection_type: ....
    parameters:
      ....
    network_functions: # Optional
      ....
        
{{</code>}}

## Midhaul and Backhaul QoS

For the midhaul and backhaul qos, users can introduce network `latency`, including `delay` and its `deviation`, 
data rate (`bandwidth`) and the packets' error rate (`error_rate`).

{{<code lang="yaml">}}
  midhaul_qos:
      latency:
        delay: 30ms
        deviation: 1ms
      bandwidth: 100mbps
      error_rate: 1%
{{</code>}}

## 5G MIMO and SISO connectivity

For MIMO(mutli-input-multi-output) connections, users are able to select `MIMO` (or `SISO` for single-input-single-output) as `wireless_connection_type` and to introduce specific parameters, like 
`transmit_power`, which is the power in `dbm` of the transmitter, the currier frequency (`carrier_frequency`) in `gigahrz`,
 signal `bandwidth` in `megahrz`, user equipment noise figure (`UE_noise_figure`), RU and UE antenna gains (`RU_antennas_gain` & `UE_antennas_gain`),
 the expected (or measured) maximum and minimum bitrate (`maximum_bitrate` & `maximum_bitrate`), 
 the system's queuing delay (`queuing_delay`), and RU and UE antennas elements (`RU_antennas` & `UE_antennas`)


{{<code lang="yaml">}}
    networks:
      - name: dublin_network
        network_type: slice
        midhaul_qos: ...
        backhaul_qos: ...
        wireless_connection_type: MIMO
        parameters:
          transmit_power: 30  # dbm
          carrier_frequency: 28  # gigahrz
          bandwidth: 100  # megahrz
          UE_noise_figure: 7.8  # db
          RU_antennas_gain: 8 # db
          UE_antennas_gain: 3 # db
          maximum_bitrate: 538.71
          minmum_bitrate: 53.87
          queuing_delay: 2 # ms
          RU_antennas: 8
          UE_antennas: 4
        network_functions: ....
        
{{</code>}}


## Mathematical Models

Users are also able to select if the degradation of the signal follows a specific mathematical model. 
Specifically, we provide four different models, namely, `static`, `step_wise`, `linear` and `logarithmic` singal degradation.

### Static Signal Degradation
Static (or flat) degradation model applies the same QoS in a specific radius around the RUs.  
Users have to select `FlatWirelessNetwork` as the `wireless_connection_type`, the effective `radius` of the RUs, 
and the respective network's `QoS`. 

{{<code lang="yaml">}}
...
    wireless_connection_type: FlatWirelessNetwork
    parameters:
      radius: 8km
      qos:
        latency:
          delay: 5ms
          deviation: 1ms
        bandwidth: 10mbps
....
{{</code>}}

### Step-wise Signal Degradation

Step-wise (or multi-range network) connection has different QoS for different ranges from the RU. 
For instance, the following description indicates that the QoS from `0 to 0.4km` will be equals to `3ms` delay and `10mbps` data rate,
from `0.4km to 0.7km` will be `7ms` delay and data rate again `10mbps`, and, finally, from `0.7km`
 to the radius the delay and data rate will be `15ms` and `1mbps`, respectively.

{{<code lang="yaml">}}
...
    wireless_connection_type: MultiRangeNetwork
    parameters:
      radius: 1km
      bins:
          0km:
            latency:
              delay: 3ms
              deviation: 1ms
            bandwidth: 10mbps
          0.4km:
            latency:
              delay: 7ms
              deviation: 1ms
            bandwidth: 10mbps
          0.7km:
            latency:
              delay: 15ms
              deviation: 1ms
            bandwidth: 1mbps
....
{{</code>}}

### Linear and Logarithmic Signal Degradation

For linear and logarithmic degradation, users are able to select the best(`best_qos`) and worst(`worst_qos`) connection QoS 
and the `radius`. The system will degrade respectively the QoS based on the distance between RU-to-UE by following the respective function.

{{<code lang="yaml">}}
...
    wireless_connection_type: LinearDegradation|Log10Degradation
    parameters:
      radius: 0.8km
      best_qos:
        latency:
          delay: 5ms
          deviation: 1ms
        bandwidth: 10mbps
      worst_qos:
        latency:
          delay: 100ms
          deviation: 10ms
        bandwidth: 1mbps
...
{{</code>}}

