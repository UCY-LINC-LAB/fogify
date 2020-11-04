+++
title = "Monitoring"
description = ""
weight = 8
+++

{{< lead >}}
Fogify provides a wide rage of monitoring metrics for each emulated instance and is able to extract user-defined metrics.{{< /lead >}}

## Default Metrics
Fogify captures performance metrics directly from the containerized process by inspecting the containers.
Pre-defined metrics available by Fogify include CPU time, memory usage, network traffic and many more. 
The following table depicts all available metrics provided by `Fogify`

{{< table style="table-striped" >}}
| metric        | description |
| ------------- |-------------|
| cpu      | The accumulative CPU time occupied by an emulated instance|
| cpu_util | The average utilization of CPU between two measurements|
| memory   | The occupied memory by an emulated instance |
| memory_util   | The utilization of the emulated instance's memory |
| network_rx_{network name}| The accumulative received bytes from a specific network|
| network_tx_{network name}| The accumulative transmitted bytes from a specific network|
{{< /table >}}


## User-defined Metrics

Users can expose application-level metrics for their IoT services. 
This is achieved by exposing metric updates, in JSON format, to a file (`fogify.metrics.json`) via the container root directory interface. 
Fogify will then retrieve them via a lightweight monitoring probe. 
When the agent retrieves the data, it stores them to the monitoring storage. 
Following, we offer an exemplary `fogify.metrics.json` file.

{{< code lang="json" >}}
{
  "response-time": 500,
  "requests": 6530,
  "log-in-requests": 100
}
{{</code>}}

In the previous json file there are three metrics exposed by the application, namely, the response time (`response-time`), 
requests count (`requests`) and login request count (`log-in-requests`).

{{< panel style="info">}} 
Currently, the metric's name should be string and its value should be numeric. 
{{< /panel >}}