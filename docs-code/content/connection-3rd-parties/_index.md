+++
title = "Connection with third parties and API"
description = ""
weight = 9
+++

## Fogify's Restfull API

The Fogify Controller exposes a REST API for interacting with the emulated testbed. 
Next we describe in details the available methods along with their parameters. 
Specifically, users can deploy and undeploy topologies, execute ad-hoc actions and retrieve monitored metrics. 

### Deploy Topology

The user deploys his/her topology with a `POST` api call to the `<manager>:5000/topology/` path. 

* **Parameters**: 
    * file: A yaml file that describes the application and the topology of the experiment

### Undeploy Topology

The user undeploys his/her topology with a `DELETE` api call to the `<manager>:5000/topology/` path. 

### Deploy Actions

The user can execute various actions at runtime that can alter the underlying infrastructure. 
To achieve that a user can execute `POST` call to `<manager>:5000/action/<action_type>`.
For `action_type`, we have various types, namely: `horizontal_scaling`, `vertical_scaling`, `network`, `command` and `stress`.
Users can determine either a `blueprint` `label` and the `number` of instances that the action would like to affect or 
the label along with the number of a specific node, e.g. `supervisor.5`.

We have already described the action's parameters in [`Actions & Scenarios`]({{< relref path="../actions-and-scenarios/_index.md" >}}).


### Get Monitoring Metrics

Returns the metrics in CSV format for all instances of the running application. The user should execute a `GET` api call 
to the `<manager>:5000/monitorings/` and the kresponse of the system will be in the following form:
{{< code lang="json" >}}
{
  "instance_id1": "CSV_file_for_instance_id1",
  "instance_id2": "CSV_file_for_instance_id2"
}
{{</code>}}

### Remove Monitoring Metrics
In order to "clean" the monitoring metrics for a new experiment, 
we can execute a `DELETE` api call to the `<manager>:5000/monitorings/` path. 

## Miscellaneous

### Deploy a Network Distribution
In order to deploy a custom delay distribution, one has to capture a `ping` trace file and deploy it to the system.
Specifically, there is the `/generate-network-distribution/<name>/` endpoint where users send the file through `POST` api call.
The property `name` specifies the name of the distribution on Fogify.
The generation of trace file requires the execution of the following command where `destination` can be either a `url` or an `IP` of the destination.
After that user should store the results of the latter command to a file. That is the file, which system requires in order to generate the distribution

{{< code lang="bash" >}}
ping <destination>
{{</code>}}

## Python SDK (FogifySDK)

If you are familiar with python programming language, we suggest to use [**FogifySDK**]({{< relref path="../FogifySDK/_index.md" >}})
since it has implemented all available Fogify methods.