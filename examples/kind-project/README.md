# This is an example of Kubernetes in Docker deployed on Fogify

In this example, we emulated on top **Fogify** a geo-distributed kubernetes (kind) cluster. 
The emulated cluster contains four types of nodes, namely: 
* a controller deployed on a `t3.medium` Amazon instance in `eu-west-1` 
* a worker deployed on a `t3.medium` Amazon instance in `eu-west-1` 
* a worker deployed on a `raspberry` placed in Nicosia
* a worker deployed on a `raspberry` placed in Vienna

The network latencies are computed with data of realtime rtt information (from both `https://wondernetwork.com/` and `https://www.cloudping.co/grid/latency/timeframe/1D` )
The `kind-docker-compose-10nodes.yaml` realizes a cluster with 10 Nodes, specifically, 1 controller, and 3 workers per region 
(3 deployed on `eu-west-1`, 3 raspberries placed on Nicosia, 3 raspberries placed on Vienna).

Due to the restricted capabilities of Docker swarm, users are able to execute the latter experiments only on docker-compose mode of Fogify.
Specifically, one should declare the `CONNECTOR` equals to `DockerComposeConnector` at `.env` file.
```shell script
MANAGER_NAME=...
MANAGER_IP=...
HOST_IP=...
CPU_OVERSUBSCRIPTION_PERCENTAGE=100
RAM_OVERSUBSCRIPTION_PERCENTAGE=100
CPU_FREQ=1900
NAMESPACE_PATH=/home/proc
CONNECTOR=DockerComposeConnector
```

**Note:** The image `rainbowh2020/k8s-test-cluster:latest` that is used in this experiment is an extension 
of official kind docker image. The extension is used for testing of Rainbow EU project and will be publicly available by 
the end of the project. However, you can change the image with the official kind image. 

## Resources
Rainbow project: https://rainbow-h2020.eu/
Kind (Kubernetes in Docker) project https://kind.sigs.k8s.io/
