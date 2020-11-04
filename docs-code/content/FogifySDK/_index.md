+++
title = "FogifySDK"
description = ""
weight = 9
+++

{{< lead >}}
Fogify provides a python SDK with programming primitives for interacting with the Fogify Controller. 
The FogifySDK provides the ability to submit IoT service descriptions adopting the Fogify model specification, 
manipulate service execution by applying actions and submitting "what-if" scenarios, extract real-time monitoring data 
and assess running deployments. 
Furthermore, the FogifySDK has a set of built-in analytics functions 
applicable on monitoring data, as well as, plotting functionality for easing metric examination.
{{< /lead >}}

## Instantiation

Users instantiate the `FogifySDK`, firstly, by importing the `FogifySDK` library and, secondly, by created a `FogifySDK` object.
The `FogifySDK` constructor requires the url of Fogify `Controller` and the "fogified" `docker-compose` file.

{{< code lang="python" >}}
from FogifySDK import FogifySDK
fogify = FogifySDK("http://controller:5000","docker-compose.yaml")
{{</code>}}

The `FogifySDK` object includes all required information for interconnection between the client and the `Fogify` framework.
`FogifySDK` covers all possible functionality that [Fogify API]() provides including control (`deploy`, `undeploy`), 
actions and scenario, and monitoring functions. The rest of page illustrates the latter functions and describes their documentation.

## Control Functions

Control functions are responsible for provision of a "fogified" topology. 
Specifically, there are two functions, namely:

* `deploy` function that provisions, bootstraps and deploys a "fogified" topology. 
The only parameter of `deploy` function is the `timeout`, 
which determines how many seconds a user will wait until consider that a deployment has an issue.

{{< code lang="python" >}}
fogify.deploy(timeout) #  The default value of timeout is 5 minutes
{{</code>}}

* `undeploy` function that destroys a topology and releases the occupied resources
{{< code lang="python" >}}
fogify.undeploy()
{{</code>}}


## Actions & Scenarios Functions
Fog deployments are usually neither statically provisioned nor stable. 
This instability highly impacts the execution of IoT services, especially in uncontrollable domains. 
As we described in previous sections of the documentation, Fogify addresses this challenge by providing runtime `Actions` and `Scenarios`. 
To provide a clear overview of actions and scenario functions, next we describe in details how a user can utilize `FogifySDK` to apply them on a running topology.

### Actions
An `Action` is a process that changes properties of a running Fog Topology.
Due to extensibility, we introduce a general `action` method in which users can utilize.
As we described earlier, the method needs the `action_type` parameter, which currently could be one of the following: 
`HORIZONTAL_SCALING`, `VERTICAL_SCALING`, `NETWORK`, `STRESS`, `COMMAND`, and the action's `parameters`. 
The `parameters` is a dictionary with all necessary variables of an action and the emulated instance `label` that the action will be apply to.

{{< code lang="python" >}}
fogify.action(action_type, **parameters)
{{</code>}}

Since the `action` method is too generic, `FogifySDK` includes a specific method 
for each action in order to ease their definitions and gives specific parameters for each.

#### Horizontal Scaling
A horizontal scaling action can either increase or decrease the instances of a service (Fog Node). Thus, FogifySDK introduces
two methods for that, namely:

* `horizontal_scaling_up` which spans new instances of a specific `instance_type` (is the same as the model's `label`). The number of instances is determined by `num_of_instances` and by default is `1`.
{{< code lang="python" >}}
fogify.horizontal_scaling_up(instance_type, num_of_instances)
{{</code>}}

* `horizontal_scaling_down` that destroys instances of a specific `instance_type`. Similarly, the number of instances is determined by `num_of_instances` and by default is `1`.
{{< code lang="python" >}}
fogify.horizontal_scaling_down(instance_type, num_of_instances)
{{</code>}}

#### Vertical Scaling
A vertical scaling action can either increase or decrease the processing power of a service (Fog Node). 
Specifically, user can provide the following parameters:

* `instance_type` that could be either an instance `instance-id` or `label`
* `cpu`, which is a cpu percent of increase (`+<percent>`) or decrease (`-<percent>`), e.g. `+20` or `-20`
* `memory` defines the new memory limit
* `num_of_instances` determines how many instances will be effected. The default is `1`. If the `instance_type` is an 
`instance-id`, the number of instances will not effect the action at all.

{{< code lang="python" >}}
fogify.vertical_scaling( instance_type, cpu, memory, num_of_instances):
{{</code>}}

{{< panel style="info">}} 
 The method not allow definition of both cpu and memory vertical scaling at once.
 {{< /panel >}}

#### Network

Network alterations are crucial in testing of fog deployments, so, `FogifySDK` provides a wide range of possible parameters that can be changed.
At the description of [Network QoS]() documentation, we illustrated all possible parameters that one can use in `Fogify`. 
Similarly, the same parameters can be applied at the `update_network` method. Specifically, the method requires the following parameters:
* `instance_type` that could be either an instance `instance-id` or `label`
* `network`, which is the name of the network that will be updated
* `network_characteristics` are the network properties that will be updated from the action (same as `Network QoS` properties)
* `num_of_instances` determines how many instances will be effected. The default is `1`. If the `instance_type` is an 
`instance-id`, the number of instances will not effect the action at all.

{{< code lang="python" >}}
fogify.update_network(instance_type, network, network_characteristics, num_of_instances)
{{</code>}}

#### Stress 

A stress action provides the ability to simulate workload interference on a running Fog node. 
This is useful to evaluate the behaviour of a service during workload variation and/or interference from other services. 
The parameters of the function are the following:
* `instance_type` that could be either an instance `instance-id` or `label`
* `duration` specifies how many seconds the stress action will effect the node
* `num_of_instances` determines how many instances will be effected. The default is `1`. If the `instance_type` is an 
`instance-id`, the number of instances will not effect the action at all.
* `cpu` specifies how many cpu intensive workload threads will be spawed in the emulated Fog node
* `io` specifies how many io intensive workload threads will be spawed in the emulated Fog node
* `vm` specifies how many memory intensive workload threads will be spawed in the emulated Fog node and 
the `vm_bytes` determines the size of the memory that will be occupied and free in every cycle of the test
{{< code lang="python" >}}
fogify.stress(instance_type, duration, num_of_instances, cpu, io, vm, vm_bytes)
{{</code>}}
#### Commands
With the `command` method, users are able to execute arbitrary commands directly to the emulated fog nodes. 
The latter gives the opportunity to extend the functionality of Fogify without extending its code-base. 
The parameters of the `command` method are:
* `instance_type` that could be either an instance `instance-id` or `label`
* `command` which the Fogify will execute on the emulated fog node
* `num_of_instances` determines how many instances will be effected. The default is `1`. If the `instance_type` is an 
`instance-id`, the number of instances will not effect the action at all.

{{< code lang="python" >}}
fogify.command(instance_type, command, num_of_instances)
{{</code>}}

### Scenario Execution
As we described in [scenario section](), scenarios are a sequence of timestamped actions described in a yaml representation.
Users specify multiple scenarios on fogify model file (the extended docker-compose) with different names. In order to execute
a scenario through `FogifySDK`, you can simple run the `execute_scenario` method with the only required parameter to be the `scenario_name`.

{{< code lang="python" >}}
fogify.execute_scenario(scenario_name)
{{</code>}}

## Monitoring & Analysis Functions
Fogify stores the metrics from the running emulated nodes in a distributed manner, on each host node.
Users can then extract metrics to generate useful insights about QoS, cost, and predictive analytics. 
This is achieved through the `FogifySDK`, which retrieves local metrics to an in-memory data structure (`pandas` dataframe)
providing exploratory analysis methods that produce plots and summary statistics.
Next we have the basic methods that are implemented on FogifySDK to manipulate and user the stored monitoring data.

### Retrieve Monitoring Metrics
`FogifySDK` achieves the monitoring data retrieval by requesting them from the Fogify controller. 
When the data is retrieved, the `FogifySDK` creates a `pantas` dataframe from them. 
Specifically, the method `get_metrics_from` retrieves all monitored metrics from a running emulated instance. 
The only parameter that the method needs is the `instance_label`.

{{< code lang="python" >}}
fogify.get_metrics_from(instance_label)
{{</code>}}
### Clear Monitoring Storage
Since users would like to "start" different experiments without re-deploy the whole topology, 
`FogifySDK` offers a method to clear the stored data. The method is the `clean_metrics` and does not require any other parameter. 
{{< code lang="python" >}}
fogify.clean_metrics()
{{</code>}}

## Miscellaneous

### Deploy a Network Distribution

As we described in previous section, users are able to deploy custom network delay distributions.
Specifically, user captures a `ping` trace file and deployed to Fogify.
The `deploy_network_distribution` requires two parameters, namely, the `name` of the distribution and the `file` of the distribution.
When the file is deployed to the system, Fogify is able to utilize it on the network QoS properties.

{{< code lang="python" >}}
fogify.deploy_network_distribution(name, file)
{{</code>}}