# fogify
A Fog Computing Emulator Framework

Fogify is an emulation Framework easing the modeling, deployment and experimentation of fog testbeds. 
 Fogify provides a toolset to: model complex fog topologies comprised of heterogeneous resources, 
 network capabilities and QoS criteria; deploy the modelled configuration and services using popular 
 containerized infrastructure-as-code descriptions to a cloud or local environment; experiment, measure and evaluate the deployment by injecting faults and adapting the configuration at runtime to test different 
 "what-if" scenarios that reveal the limitations of a service before introduced to the public.

   ### Topology Editing
   A typical workflow starts with the user editing the docker-compose file of an IoT application, and extend it to encapsulate Fogify's model.
   The Fogify model is composed of: (i) <i>Fog Templates</i>, allowing the description of <i>Services</i>, <i>Nodes</i> and 
   <i>Networks</i>; and (ii) the <i>Fog Topology</i>, enabling users to specify <i>Blueprints</i>. 
   A Blueprint represents an emulated device and is a combination of a <i>Node</i>, <i>Service</i>, <i>Networks</i>, 
   <i>replicas</i> and a <i>label</i>. Services are inherited from docker-compose while the <i>x-fogify</i> 
   section provides all Fogify primitives. Thus, users still develop their application using familiar docker constructs 
   with the added functionality of Fogify not affecting portability. This means that a Fogify enhanced description will 
   run in any docker runtime environment without any alterations, however users will lose the functionality offered by Fogify. 

   ### Deployment
   When the description is ready, the user deploys the application using the FogifySDK through a Jupyter notebook, 
with the description received by the Fogify Controller.
If no error is detected by the Controller, it spawns the emulated devices and creates the overlay mesh networks between them, 
instantiates the services, and broadcasts (any) network constraints to Fogify Agents. 
Specifically, the Controller translates the model specification to underlying orchestration primitives and deploys them 
via the Cluster Orchestrator, ensuring the instantiation of the containerized services on the emulated environment. 
Located on every cluster node, Fogify Agents expose an API to accept requests from the Controller, apply network QoS primitives, and monitor the emulated devices.

### Testing
On a running emulated deployment, Fogify enables developers to apply <i>Actions</i> and "what-if" <i>Scenarios</i> 
(sequences of timestamped actions) on their IoT services, such as ad-hoc faults and topology changes. 
Actions and Scenarios are written by following the Fogify <i>Runtime Evaluation Model</i>. 
When an action or a scenario is submitted, the Fogify Controller coordinates its execution with the Cluster Orchestrator
 and the respective Fogify Agents. 
Furthermore, Fogify captures performance and app-level metrics via the Fogify Agent monitoring module.
All metrics are stored at the Agent's local storage and can be retrieved from the FogifySDK. 

### Analysis

To create an end-to-end interactive analytic tool for emulated deployments, we exploit the FogifySDK capabilities in Jupyter Notebook stack.
Specifically, we pre-installed the FogifySDK library on Jupyter thus the user can (un-) deploy a Fog Topology, apply ad-hoc changes and scenarios, 
and, especially, retrieve runtime performance metrics. For the latter, FogifySDK stores metrics to an in-memory data structure, namely panda's dataframe, 
providing exploratory analysis methods that produce plots and summary statistics. Except of out-of-the-box plots, provided by Pandas, 
we extended FogifySDK with tailored functions that provide a set of plots illustrating and explaining the effects of actions and scenarios in application performance. 
With the wide range of analytic methods provided by FogifySDK, users extract useful insights about QoS, cost, and predictive analytics. 
Finally, users may integrate other libraries, like scikit-learn, to endrose their analysis with ML and AI models. 


## Resources

### Documentation
You will find the full documentation of the Fogify at the [documentation page](https://ucy-linc-lab.github.io/fogify/).
At Fogify's documentation, we provide details about installation, modeling, experimentation, and, generally, a full get-started guide about the project. 

### The Team
The creators of the Fogify are members of the [Laboratory for Internet Computing (LInC), University of Cyprus](http://linc.ucy.ac.cy/).
You can find more information about our research activity visit our publications' [page](http://linc.ucy.ac.cy/index.php?id=12) and our [on-going projects](http://linc.ucy.ac.cy/index.php?id=13).


### Publications

For more details about Fogify and our scientific contributions, you can read the papers of [Fogify](http://linc.ucy.ac.cy/index.php?id=12) 
and a published [Demo](http://linc.ucy.ac.cy/index.php?id=12).
If you would like to use Fogify for your research, you should include at least on of the following BibTeX entries. 

Fogify's paper BibTeX citation:
```
@inproceedings{Symeonides2020,
author    = {Moysis, Symeonides and Zacharias, Georgiou and Demetris, Trihinas and George, Pallis and Marios D., Dikaiakos},
title     = {Fogify: A Fog Computing Emulation Framework},
year      = {2020},
publisher = {Association for Computing Machinery},
address   = {New York, NY, USA},
booktitle = {Proceedings of the 5th ACM/IEEE Symposium on Edge Computing},
location  = {San Jose, CA, USA},
series    = {SEC ’20}
}
```

Fogify's demo BibTeX citation:
```
@inproceedings{Symeonides2020,
author    = {Moysis, Symeonides and Zacharias, Georgiou and Demetris, Trihinas and George, Pallis and Marios D., Dikaiakos},
title     = {Demo: Emulating Geo-Distributed Fog Services},
year      = {2020},
publisher = {Association for Computing Machinery},
address   = {New York, NY, USA},
booktitle = {Proceedings of the 5th ACM/IEEE Symposium on Edge Computing},
location  = {San Jose, CA, USA},
series    = {SEC ’20}
} 
```


### Acknowledgements
This work is partially supported by the EU Commission through [RAINBOW](https://rainbow-h2020.eu/)  871403 (ICT-15-2019-2020) project 
and by the Cyprus Research and Innovation Foundation through COMPLEMENTARY/0916/0916/0171 project.

### License
The framework is open-sourced under the Apache 2.0 License base. The codebase of the framework is maintained by the authors for academic research and is therefore provided "as is".
