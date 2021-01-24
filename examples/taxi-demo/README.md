# fogify-demo
Demo: Emulating Geo-Distributed Fog Services

This demo presents an end-to-end system that combines **Fogify**, our interactive fog emulator, with **Jupyter**, a web-based interactive tool for data analysis.
On the one hand, Fogify helps developers by enabling the deployment of emulated fog realms locally or on cloud infrastructure 
while easing the description of fog topologies by extending the Docker Compose to support the "fogified" model specification. 
With the "fogified" model, Fogify allocates resources as separated containerized processes, and establishes network connections between them. 
At running time, Fogify allows developers to inject ad-hoc faults, entity downtime, perform scaling actions, adjust the workload, network changes and restrict data movement.

## Requirements

Before starting, we have to install docker, docker-compose and docker swarm on the infrastructure. 
For more information, we suggest the official [documentation](https://docs.docker.com/).

Furthermore, the system executes some low-level commands in order to apply specific characteristics to the network. 
For this reason, on each cluster of the swarm cluster, we should install the traffic control tool (tc-tool). 
On Debian-based destributions, tc-tool comes bundled with iproute, so in order to isntall it you have to run:

```bash
apt-get install iproute
```

## Stack Instantiation
The Fogify and Jupyter stack is provided as dockerized services described via docker-compose file. 
So we should run the following command at the swarm master node. 

```bash
sudo docker-compose -p fogemulator up
```
In order to open the web interface of Jupyter, you have to find the output of the `ui` service 
where the system outputs the `url` and the `token` 

![Jupyter Notebook](./images/jupyter.png)

For instance, in previous output we can open the Jupyter interface with the following url:
```
http://127.0.0.1:8888/?token=1cd2e914cd03e76d551a666cb0a8dcdb6361bc29ddf54eed
```

If we have more nodes in the cluster, we have to execute the following command on every node.

```bash
sudo docker-compose -p fogemulator up agent cadvisor
```

For both modes, users should provide a set of parameters to compose file (written in .env file), specificaly:
```bash
MANAGER_NAME=.... #The name of the swarm master node
MANAGER_IP=192.168.1.1 #The IP of the swarm master node
HOST_IP=192.168.1.1 #The IP of the host
```

## Preparation of taxis use-case
As a simple testing app, we implemented a simple  IoT service that is driven by real-world data ([New York Taxi](https://on.nyc.gov/2OssELg)) to showcase a 
scenario of a taxi-cab company that collects and analyzes location-based data from its fleet.
The codebase of the application is under the `application` folder and 
can be easily build by running the following command:
```bash
./application/build-image.sh
```
When the containers are built,  user has to create a folder named `/home/ubuntu/data` and should place the `yellow_tripdata_2018-01.csv` of New York taxi trip [dataset](https://www1.nyc.gov/site/tlc/about/tlc-trip-record-data.page).
Finally, the user can utilize the `demo_files/docker-compose.yaml` file as input of the Fogify.
