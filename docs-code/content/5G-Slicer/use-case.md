+++
title = "Dublin's Buses Use-case"
description = ""
weight = 4
+++

5G-Slicer gives the opportunity for users to implement their scenarios via the `Template` class (`from usecases.template import Template`).
Specifically, users need to implement `generate_experiment` function or to utilize the already created use-cases of the 5G-Slicer packet.
The 5G-Slicer has already implemented a city-scale usecase of dublin's buses datasets. 

Users need only to introduce their application and a basic 5G-Slicer model like the following:
{{<code lang="yaml">}}
services:
  cloud_service:
    image: bus-exp:0.0.1
  edge_service:
    image: bus-exp:0.0.1
  bus_service:
    image: bus-exp:0.0.1
    environment:
      - "NODE_TYPE=IOT_NODE"
    volumes:
      - "/home/ubuntu/data:/data"
version: '3.7'

x-fogify:
  networks:
  - network_type: slice
    midhaul_qos:
      latency:
        delay: 10ms
        deviation: 1ms
      bandwidth: 1000mbps
    backhaul_qos:
      latency:
        delay: 30ms
        deviation: 1ms
      bandwidth: 100mbps
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
    name: dublin_network
  nodes:
  - capabilities:
      memory: 2G
      processor:
        clock_speed: 2400
        cores: 4
    name: cloud_machine
  - capabilities:
      memory: 2G
      processor:
        clock_speed: 1400
        cores: 2
    name: edge_device
  - capabilities:
      memory: 0.25G
      processor:
        clock_speed: 500
        cores: 1
    name: bus_device
{{</code>}}

Then, they need to select specific parameters at the `BusExperiment` class implementation like: 
bounding box (`bounding_box`) in which the execution will take place, 
number of RUs, MECs, Cloud nodes, and buses (`num_of_RUs`, `num_of_edge`, `num_of_clouds`, `num_of_buses`) 
that the system randomly will extract from the dublin's buses dataset, place of the traces file and bus stop file, etc.
Then, the function `generate_experiment` will return a `SlicerSDK` object that already has the information about the deployment.

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






