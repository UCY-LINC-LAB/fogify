from abc import ABC, abstractmethod

from FogifyModel.base import Node


class BasicConnector(ABC):

    @abstractmethod
    def generate_files(self):
        """
        This function returns the proper docker-swarm file
        :return:  The generated object as Json and store it as yaml file
        """
        pass

    @abstractmethod
    def get_nodes(self):
        """Returns the physical nodes of the cluster
        :return: A dictionary of <Node-id: Node-ip>
        """
        pass

    @abstractmethod
    def scale(self, service, instances):
        """ Executes a scaling action for specific instance's number
        :param service: The service that the system will scale
        :param instances: The number of Instances
        :return: Returns the result of the command execution
        """
        pass

    @abstractmethod
    def get_all_instances(self):
        """
        Generates all instances of all services and in which node they run
        :return: a dictionary that has as keys the nodes and as values a set of running containers on each node
        """
        pass

    @abstractmethod
    def count_services(self, service_name=None):
        """
        Counts the services that are running
        :param service_name: The name of the service, if it does not exists, function returns all services
        :return: The number of running services
        """
        pass

    @abstractmethod
    def count_networks(self):
        """
        Counts the networks that are created
        :return: The number of created networks
        """
        pass

    @abstractmethod
    def create_network(self, network):
        """Creates the overlay networks
        :param network: a network object contains network `name` and optional parameters of `subnet` and `gateway` of the network
        """
        pass

    @abstractmethod
    def deploy(self, timeout):
        """Deploy the emulated infrastructure
        :param timeout: The maximum number of seconds that the system waits until set the deployment as faulty
        """
        pass

    @abstractmethod
    def inject_labels(self, labels={}, **kwargs):
        """
        if there is a multi-host orchestrator, this method injects the placement labels
        :param labels:
        :param kwargs:
        :return:
        """
        pass

    @abstractmethod
    def down(self, timeout=60):
        """Undeploys a running infrastructure

        :param timeout: The duration that the system will wait until it raises exception
        """
        pass

    @classmethod
    @abstractmethod
    def return_deployment(cls):
        pass

    @classmethod
    @abstractmethod
    def event_attr_to_information(cls, event):
        pass

    @classmethod
    @abstractmethod
    def instance_name(cls, alias: str) -> str:
        pass

    @abstractmethod
    def get_running_container_processing(self, service):
        """ Find the number of the running containers for a service

        :param service: The name of the service
        :return: Return the number if the service exists otherwise None
        """
        pass

    @classmethod
    @abstractmethod
    def check_status(cls, *_args, **_kwargs):
        """
        A decorator that evaluates if there is a running Fogify topology
        """
        pass

    @abstractmethod
    def node_representation(self, node: Node):
        """ Generate the Node template of docker-compose spec

        :param node: The specific node as described in Docker-swarm
        :return: The resource's template for docker-compose
        """
        pass

    @abstractmethod
    def get_ips_for_service(self, service):
        """
        Returns all ips from all containers of a service
        :param service:
        :return:
        """
        pass

    def get_local_containers_infos(self):
        raise NotImplementedError

    @staticmethod
    def get_service_from_name(name):
        raise NotImplementedError

    @staticmethod
    def get_service_from_name(name):
        """
        Returns the service object based on the service name
        :param name: The name of the service
        :return: The service object
        """
        raise NotImplementedError

    @staticmethod
    def get_node_from_ip(ip_address):
        """
        Returns the node object based on the IP address
        :param ip_address: The IP address of the node
        :return: The node object
        """
        raise NotImplementedError
