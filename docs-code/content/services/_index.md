+++
title = "Services"
description = ""
weight = 3
+++

{{< lead >}}
Services are self-contained binaries, made up of libraries, tools, and dependencies for the codebase.
The services should be described with exactly the same way as docker-compose specification. 
{{< /lead >}}

## Preliminaries

Docker provides a standardized way for building, sharing and executing containerized applications. 
Specifically, `dockerfiles` are files that include all details for building docker `Images`. 
`Images` package all the service's code, dependencies, artifacts, etc. 
The system stores `images` on local or remote repositories. 
The most well-known publicly available repository is docker-hub.
`Docker containers` are the running instances of the images and, consequently, 
the execution environment of Fog Node emulated instances.
### Dockerfiles

As we explained before, Docker builds images automatically by scanning the instructions from a Dockerfile. 
A Dockerfile is a file that includes all instructions that the user calls in order to assemble a docker image.
To build a new docker image, users run the build command that executes the instructions, creates and stores the new image. 
A simple example of a dockerfile is the following:

{{<code lang="Docker">}}
FROM ubuntu:18.04
COPY . /app
RUN make /app
CMD python /app/app.py
{{</code>}}

For more example and a detail documentation, we suggest the dockerfile's [official documentation](https://docs.docker.com/engine/reference/builder/).

### Images


The simplest way to create an image is to build a dockerfile. 
The `docker build` command creates a Docker image from a Dockerfile.
We can use the `-t` flag in order to specify a tag for the created image. 
Usually, this tag is the name of the image along with its version. 
For instance the following command creates an image with the `simple-app:0.1` tag, 
which illustrates that the image contains the version `0.1` of the `simple-app` service.

{{<code lang="Docker">}}
docker build -t simple-app:0.1 . 
{{</code>}}

One can search the available images on the local host by running the `docker image ls` command. 

{{<code lang="Docker">}}
docker image ls
{{</code>}}

For more example and a detail documentation, we suggest to check the available commands like `image pull`, `image rm`, 
etc, on [docker command documentation](https://docs.docker.com/engine/reference/commandline/docker/) 
while dedicated pages exist for
the docker image's [docker image](https://docs.docker.com/engine/reference/commandline/images/) 
and [docker build](https://docs.docker.com/engine/reference/commandline/build/) documentations.

{{< panel style="info">}} 
Similarly to Docker Swarm, in a Fogify deployment, the images should be either 
registered on every single node of the Fogify's Cluster or should be uploaded on a publicly available repository.
 {{< /panel >}}


### Containers

When a user "runs" an image, a running instance of that image is created, namely a docker container.
The `docker run` command execute a docker image and creates a docker `container`.
For instance the following command creates a docker container from the `simple-app:0.1` image.

{{<code lang="Docker">}}
docker run simple-app:0.1 
{{</code>}}

Similarly with the other concepts of docker, there are many parameters and commands that a user can use. 
Again, a more detailed view of docker container's commands is provided on the docker's command line [official documentation](https://docs.docker.com/engine/reference/commandline/docker/)

## Docker-compose files

`Docker-compose` is a toolkit for determining and executing multi-container applications. 
A YAML file defines and configures the application's services. 
Docker-compose helps users to create, start, and stop all services.
The docker-compose specification configures many concepts that an application needs, such as environmental parameters, 
dependencies between the services, resources from local host, exported container's ports, and many more. 
An overview of the docker-compose can be found on the [official page](https://docs.docker.com/compose/). 
To illustrate the functionalities of docker-compose, followingly, we present an example of a typical docker-compose file
 (`docker-compose.yaml`) that describes an `Apache Storm` cluster: 

{{< code lang="yaml" >}}
services:  # The list of the available services
  zookeeper:  # The service name that we use as service identifier
    image: zookeeper  # The image of the service
    restart: always
  nimbus:  
    image: storm:2.1.0 
    command: storm nimbus
    depends_on:  
      - zookeeper  # This determines that the service nimbus will wait until the zookeeper starts
    restart: always
    ports: # On this port the service receives external requests (host-port:container-port)
      - 6627:6627 
    volumes: # We can pass specific files into the service file system (host-path:container-path)
       - /home/TestTopology.jar:/example/TestTopology.jar  
  ui:
    image: storm:2.1.0
    command: storm ui
    depends_on:
      - nimbus
      - zookeeper
    restart: always
    ports:
      - 8080:8080
  supervisor:
    image: storm:2.1.0
    command: storm supervisor
    depends_on:
      - nimbus
      - zookeeper
    restart: always
{{</code>}}


