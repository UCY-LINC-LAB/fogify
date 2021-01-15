import os

from FogifyModel.base import FogifyModel, Node

from abc import ABC, abstractmethod


class BasicConnector(ABC):

    def __init__(self,
                     model: FogifyModel=None,
                     path = os.getcwd() + os.environ['UPLOAD_FOLDER'] if 'UPLOAD_FOLDER' in os.environ else "",
                     frequency=int(os.environ['CPU_FREQ']) if 'CPU_FREQ' in os.environ else 2400,
                     cpu_oversubscription=
                        int(os.environ['CPU_OVERSUBSCRIPTION_PERCENTAGE']) if 'CPU_OVERSUBSCRIPTION_PERCENTAGE' in os.environ else 0,
                     ram_oversubscription=
                        int(os.environ['RAM_OVERSUBSCRIPTION_PERCENTAGE']) if 'RAM_OVERSUBSCRIPTION_PERCENTAGE' in os.environ else 0,
                     node_name=os.environ['MANAGER_NAME'] if 'MANAGER_NAME' in os.environ else 'localhost',
                     host_ip=os.environ['HOST_IP'] if 'HOST_IP' in os.environ else None
                 ):
        """Initialize a Swarm Connector.
            :param model (FogifyModel): The fogify model that will be traslated to the proper docker-compose file
            :param path (str): The path that the swarm file will be saved
            :param frequency(int): The frequency of the underlying infrastructure nodes
        """
        self.model = model
        self.frequency = frequency
        self.path = path
        self.file = "fogified-swarm.yaml"
        self.cpu_oversubscription = cpu_oversubscription
        self.ram_oversubscription = ram_oversubscription
        self.node_name = node_name
        self.host_ip = host_ip

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