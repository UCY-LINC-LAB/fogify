+++
title = "5G-Slicer Extension"
description = ""
weight = 10
+++

<div class="row py-3">
    <div class="col-md-12" style="text-align: justify">
      <div class="container">
        <p class="lead">Experimentation with 
5G-enabled services over network slices is extremely challenging as it requires the 
deployment and coordination of numerous physical devices, including
edge and cloud resources.
To alleviate the difficulties in setting up real-world 5G testbeds, 
we introduce 5G-Slicer extension of the Fogify framework. 
5G-Slicer facilitates the definition of mobile network slices 
through modeling abstractions for radio units, mobile nodes, trajectories, etc., 
while also offering realistic network QoS by dynamically altering -at runtime- signal strength. 
Moreover, 5G-Slicer provides an already realized scenario for a city-scale deployment that 
smart-city researchers can simply configure through a "ready-to-use" template, 
leaving 5G-Slicer responsible for translating it into an emulated environment. </p>
      </div>
    </div>
</div>    

---

### Features

<div class="row py-3">
	<div class="col-md-6">
		<div class="card flex-row border-0">
			<div class="mt-3">
				<span class="fas fa-file fa-2x text-primary"></span>
			</div>
			<div class="card-body pl-2 " style="display: inline-block; text-align: justify">
				<h4 class="card-title">
					5G Slicing Modeling
				</h4>
				<p class="card-text text-muted">
					5G-Slicer offers high-level modeling abstractions for 5G radio units, backhaul & midhaul QoS, 
					user equipment, edge & cloud compute resources, VNFs, etc.
				</p>
			</div>
		</div>
	</div>
	<div class="col-md-6">
		<div class="card flex-row border-0">
			<div class="mt-3">
				<span class="fas fa-map-marked fa-2x text-primary"></span>
			</div>
			<div class="card-body pl-2" style="display: inline-block; text-align: justify">
				<h4 class="card-title">
					Positioning & Mobility
				</h4>
				<p class="card-text text-muted">
					Controlling the link quality,  such  as  network  latency,  bandwidth,  error  rate,  etc.,and  even  reproduce  real-world  node-to-node  and  node-to-network connection traces
				</p>
			</div>
		</div>
	</div>
	<div class="col-md-6">
		<div class="card flex-row border-0">
			<div class="mt-3">
				<span class="fas fa-bus fa-2x text-primary"></span>
			</div>
			<div class="card-body pl-2" style="display: inline-block; text-align: justify">
				<h4 class="card-title">
					ITS Use case template
				</h4>
				<p class="card-text text-muted">
                    5G-Slicer provides a "ready-to-use" template for a city-scale transportation sector that
                    users are able to introduce their services 
                 </p>
			</div>
		</div>
	</div>
	<div class="col-md-6">
		<div class="card flex-row border-0">
			<div class="mt-3">
				<span class="fas fa-search fa-2x text-primary"></span>
			</div>
			<div class="card-body pl-2" style="display: inline-block; text-align: justify">
				<h4 class="card-title">
					Monitoring Capabilities
				</h4>
				<p class="card-text text-muted">
		        Slicing plug-in introduced new monitoring capabilities for packet-level monitoring 
		        and analytics to the emulation suite
				</p>
			</div>
		</div>
	</div>
</div>






---

## Overview
<p></p>

<div class="container-md">
<div class="row justify-content-center">
   <div class="row">
   <div class="col-lg-6" style="text-align: justify">
   
A typical deployment starts by either describing the application services and network fabric via the 5G-Slicer model 
specification or by parameterizing a "ready-to-use" testbed template. 
The model specification can denote a wide range of network slice parameters, including the position of compute nodes and RUs, 
network links and their QoS, mobile node traces, communication protocols and VNFs applicable on nodes. 
On the contrary, parametrizable use-case templates automatically produce 5G deployments for IoT applications. 
The output of each template is a programming view equivalent to a validated deployment description. 
The topology and trajectories are propagated to the control layer.

Then, the system extracts from the description the network slice specification
and any signal degradation models defined during the modeling process. 
With these, it produces an in-memory Network Conceptual Graph (NCG), which contains the aforementioned information 
and will be used by the system for the runtime state propagation during the experimentation. 
The graph nodes represent network and compute devices annotated with information about their capabilities and 
deployed services, while edges denote the links between the nodes.
The weight of each edge is determined by network QoS, incl. data rate, network delay, packet and error rate. 
Then 5G-Slicer translates the NCG to an emulated environment by utilizing the Fogify Emulator Connector. 
</div>




   
   <div class="col-lg-6" style="text-align: justify">
   
   <p></p>
        <img class="img-fluid" src="slicer-overview.png" />
<p></p>


</div>
</div>
The connector is responsible for the emulation environment instantiation, and the deployment of the IoT application  through the FogifySDK. 
Furthermore, the Trajectory Manager parses the traces and applies the updates on the NCG, 
and, in turn propagates these to the running emulated environment.
One can view through an interactive map the traces of mobile nodes, 
their performance (i.e. cpu, energy), and the load imposed to MECs. 

</div>

</div>





   


<p/>



<div class="row  justify-content-center">
<div class="col-lg-12" style="text-align: justify">



</div>

</div>




---



## Publications

For more details about 5G-Slicer and our scientific contributions, you can read the papers of [5G-Slicer](http://linc.ucy.ac.cy/index.php?id=12) 
and a published [Demo](http://linc.ucy.ac.cy/index.php?id=12).
If you would like to use 5G-Slicer for your research, you should include at least on of the following BibTeX entries. 

5G-Slicer's paper BibTeX citation:
{{< code >}}
@INPROCEEDINGS{Symeonides2022,
author    = {Symeonides, Moysis and Trihinas, Demetris and Pallis, George and Dikaiakos, Marios D. and Psomas, Constantinos and Krikidis, Ioannis},
title     = {5G-Slicer: An emulator for mobile IoT applications deployed over 5G network slices}, 
booktitle = {Proceedings of the 7th ACM/IEEE Conference on Internet of Things Design and Implementation},
year      = {2022}
series    = {IoTDI ’22}
}
{{</code>}}

5G-Slicer's demo BibTeX citation:
{{< code >}}
@inproceedings{Symeonides2020,
author    = {Symeonides, Moysis and Trihinas, Demetris and Pallis, George and Dikaiakos, Marios D.},
title     = {Demo: Emulating 5G-Ready Mobile IoT Services},
booktitle = {Proceedings of the 7th ACM/IEEE Conference on Internet of Things Design and Implementation}, 
year      = {2022}
series    = {IoTDI ’22}
} 
{{</code>}}


## Acknowledgements
This work is partially supported by the EU Commission through [RAINBOW](https://rainbow-h2020.eu/)  871403 (ICT-15-2019-2020) project 
and by the Cyprus Research and Innovation Foundation through COMPLEMENTARY/0916/0916/0171 and INFRASTRUCTURES/1216/0017 (IRIDA) projects. 
The authors wish to thank Dr. Christos Tranoris and prof. Spyros Denazis of the U. of Patras for providing measurements from the "Patras 5G" testbed, 
which was supported by the 5GVINNI H2020 (EU grant agreement No. 815279)