+++
title = "Actions & Scenarios"
description = ""
weight = 7
+++

The Fogify's model abstractions enable the rapid prototyping of emulated Fog deployments. 
However, Fog deployments are usually neither statically provisioned nor stable. 
This instability highly impacts the execution of IoT services, especially in uncontrollable domains.
Fogify addresses this challenge by providing runtime `Actions` & `Scenarios`. 
`Action` is a process that changes properties of a running Fog Topology while 
`Scenario` allows the repeatable execution of a series of `Actions` written in a yaml format.

## Actions

The user can execute various actions at runtime that can alter the underlying infrastructure. 
To achieve that a user can execute `POST` call to `<manager>:5000/action/<action_type>` or can utilize the [FogifySDK]().
For `action_type`, we have various types, namely: `horizontal_scaling`, `vertical_scaling`, `network`, `command` and `stress`.
Users can determine either a `blueprint` `label` and the `number` of instances that the action would like to affect or 
the label along with the number of a specific node, e.g. `supervisor.5`.


### Horizontal Scaling
For horizontal scaling actions, we have to select the instance type (`label`), 
the number of instances and the action that will be applied (`up` or `down`)
{{< code lang="json" >}}
{ 
  "params":{
    "instance_type" : "supervisor-1", 
    "instances": 2, 
    "type":"up"
    } 

}
{{</code>}}

{{< panel style="info">}} 
Currently, Fogify does not guarantee that the horizontal scaling action will be apply, user has to be sure about the extra resources.
{{< /panel >}}

### Vertical Scaling
For vertical scaling actions, we have to select the instance type (`label`), and the action that will be applied.
For `CPU` power, user can define a cpu percent of increase (`+<percent>`) or decrease (`-<percent>`). 
For `memory`, one defines the new memory limit. We can not define both cpu and memory vertical scaling at once.
{{< code lang="json" >}}
{ 
  "params":{
    "instance_type" : "supervisor-1.1", 
    "cpu":"+20",
    "memory": "3G"
    } 

}
{{</code>}}


{{< panel style="info">}} 
Currently, Fogify does not guarantee that the vertical scaling action will be apply, user has to be sure about the extra resources.
{{< /panel >}}
### Network
This action updates the network connectivity of a node. Again, the user selects the instance type (`label`)
and the action object that contains various network parameter like `delay`, `bandwidth`, `drop` etc. Furthermore, a user 
selects a specific network. At the following example, we apply our action to the `supervisor-1` to the  `internet` network connection.
{{< code lang="json" >}}
{ "params":{
	"instance_type" : "supervisor-1", 
	"instances": 1, 
	"action":{
		"uplink":{
			"latency":{"delay":"100ms"}, 
			"bandwidth": "100Mbps", 
			"drop": 0.0001},
		"downlink":{
			"latency":{"delay":"100ms"}, 
			"bandwidth": "100Mbps", 
			"drop": 0.0001}, 
	"network":"internet"}} 
	}
{{</code>}}



### Stress
Fogify can inject extra workload to specific node(s) in order to simulate the interferences of colocated service
on a node. For instance, with the following json object, Fogify will inject a 50% cpu-intensive workload for 300s to one instance
of the node `supervisor-1`. 

{{< code lang="json" >}}
    { 
    "params":{
        "instance_type" : "supervisor-1", 
        "instances": 1, 
        "action":{
            "cpu":50,
            "duration": "300s"
            }	
        } 
    }
{{</code>}}

### Command
Fogify can inject terminal command to specific node(s). The latter helps users to execute even user-defined actions on running fog nodes.
For instance, with the following json object, Fogify will inject a submission command on `nimbus` node. 

{{< code lang="json" >}}
    { 
    "params":{
        "instance_type" : "nimbus", 
        "instances": 1, 
        "action":{
            "command": "/bin/storm jar test.jar test-topology"
            }	
        } 
    }
{{</code>}}

## Scenarios

With the Scenarios, a user will be able to define predefined series of actions at specific time. 
For instance, at the `scenario_1` the first action will be executed at 5th minute from the started point of the experiment.

{{< code lang="yaml" >}}
scenarios:
- name: scenario_1
  actions: 
    - time: 30
      position: 0
      instance_type: supervisor-1
      instances: 1
      action:
        type: network
        parameters:
            network: edge-net-1
            bidirectional:
              bandwidth: 100Mbps
              drop: 0.1%
              latency:
                delay: 1000ms
    - time: ....
{{</code >}}

