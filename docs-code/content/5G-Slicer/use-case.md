+++
title = "Use-case"
description = ""
weight = 4
+++

5G-Slicer gives the opportunity for users to implement their scenarios via the `Template` class (`from usecases.template import Template`).
Specifically, users need to implement `generate_experiment` function and to utilize the 


{{<code lang="python">}}
from usecases.dublin_buses_experiment import BusExperiment
from SlicerSDK import SlicerSDK
file_path = "<docker-compose.yaml path>"
fogify_controller_url = "http://controller:5000"
slicerSDK = SlicerSDK(fogify_controller_url, file_path)
experiment = BusExperiment(slicerSDK, 
                bounding_box = (  # geographic bounding box of the experiment
                (53.33912464060235, -6.286239624023438), 
                (53.35833815100412, -6.226158142089845)),
                num_of_RUs = 1,  # number of radio units
                num_of_edge = 1,  # number of edge servers
                num_of_clouds = 1,  # number of cloud servers
                num_of_buses = 1,  # number of IoTs (buses)
                time_to_run = 60,  # minimum time of a bus-trace for the bounding box
                traces_filename = 'usecases/data/all.csv',  # file of the traces
                bus_stops_filename = 'usecases/data/stops.csv',  # file of the bus stops
                edge_service = 'edge_service',  # name of the edge service of the docker-compose file
                edge_device = 'edge_device',  # name of the edge device (described in fogify model) of the docker-compose file
                bus_service = 'bus_service',  # name of the IoT workload service of the docker-compose file
                bus_device = 'bus_device', # name of the IoT device (described in fogify model) of the docker-compose file
                cloud_service = 'cloud_service',  # name of the cloud service of the docker-compose file
                cloud_device = 'cloud_machine',  # name of the cloud service device (described in fogify model) of the docker-compose file
                slice_name = 'dublin_network', # name of the network that will be created
                max_num_of_trace_steps = 60, # maximum number of changes(locations) that a trace can have
                min_num_of_trace_steps = 0, # minimum number of changes(locations) that a trace can have
                bus_ids = [],  # specific bus-ids (traces) for the emulation, if it is empty, system takes `num_of_buses` randomly
                ru_overlap: str = "random"  # selects specific RUs based on their radius overlapping (`random`, `min_density`, `max_density`, `kmeans`)
           )
slicerSDK = experiment.generate_experiment()  # builds the experiment based on user's preferences 
slicerSDK.deploy()  # deploy the infrastructure

slicerSDK.scenario_execution('mobility_scenario')  # executes the mobility scenario of the selected buses

{{</code>}}






