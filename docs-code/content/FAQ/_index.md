+++
title = "Frequently Asked Questions (FAQs)"
description = ""
weight = 11
+++

{{< lead >}}
This section demonstrate the most frequent questions along with their answers
{{< /lead >}}

### Does Fogify provide workload generators for IoT devices?
 
No, Fogify only offers emulation at the infrastructure layer. 
Users are responsible to provide workload generators as containerized services.

### How Fogify achieves the mobility of Fog Computing Deployments?

Currently, Fogify provides users the ability to define scenarios for time-scheduled network alterations, 
so user should provide the network changes that a Fog node will experience at the execution of the experiment.

### Where can I find examples of a Fogify deployment?

Currently, we provide an end-to-end example of Fogify usage at the demo repository (https://github.com/UCY-LINC-LAB/fogify-demo).
However, we will provide a wide range of applications described with Fogify in near future.

### Is the Fogify's emulation accurate and near to real-world deployments?

According to the emulation accuracy, we compare real deployments and emulated deployments for the same architectures.
 
Our experiments show the following results:

<div class="row">
    <p></p>
    <div class="col-lg-3 offset-1" style="margin-top: 40px">
        <img class="img-fluid" src="results/processing.png" />
         <p style="text-align: justify">
         The emulated computing resources has only a small performance degradation for workloads approaching 100% CPU usage
        </p>
    </div>
    <div class="col-lg-3 " style="margin-top: 40px">
        <img class="img-fluid" src="results/network.png" />
        <p style="text-align: justify">
        Fogify achieves near to real-world network link capabilities, with only outliers not captured and a slight overhead in low-latency connections
        </p>
    </div>
    <div class="col-lg-4 " style="margin-top: 40px">
        <img class="img-fluid" src="results/application.png" />
        <p style="text-align: justify">
        The emulation results closely follow the real measurements with a 5%-8% deviation of the overall experiment time.
        The picture illustrates a image recognition algorithm in two deployments. A Cloud-only deployment and an Edge-Cloud deployment.
        </p>
    </div>
</div>

You can find more information about our experiments in the [Fogify's paper](http://www.cs.ucy.ac.cy/mdd/docs/2020-SEC-Fogify.pdf)