import copy
import json
import os
import socket
import subprocess
from time import sleep

import docker
import yaml
from flask_api import exceptions

from utils.host_info import HostInfo


class BasicConnector(object):

    def __init__(self, model=None, path=".", frequency=4000, cpu_oversubscription=0, ram_oversubscription=0):
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

    def generate_files(self):
        pass

    def get_nodes(self):
        pass

    def get_network(self):
        pass

    def scale(self, service, instances):
        pass

    def get_all_instances(self):
        pass

    def count_services(self, service_name=None):
        pass

    def count_networks(self):
        pass

    def create_network(self, network):
        pass

    def deploy(self):
        pass

    def inject_labels(self, labels={}, **kwargs):
        pass

    def down(self, timeout=60):
        pass

    @classmethod
    def return_deployment(cls):
        pass

    @classmethod
    def event_attr_to_information(cls, event):
        pass

    @classmethod
    def instance_name(cls, alias: str) -> str:
        pass

    def get_running_container_processing(self, service):
        """ Find the number of the running containers for a service

        :param service: The name of the service
        :return: Return the number if the service exists otherwise None
        """
        pass


class CommonDockerSuperclass(BasicConnector):

    @classmethod
    def check_status(cls, *_args, **_kwargs):
        CurrentClass = cls

        def decorator(func):
            def wrapper(*args, **kwargs):
                options = ['available', 'running']
                if not len(_args) > 0:
                    raise exceptions.APIException('You have to select at least one option:' + str(options))
                option = str(_args[0])
                if option not in options:
                    raise exceptions.APIException('You have to select an option from:' + str(options))
                if option == 'available':
                    if int(CurrentClass.count_services(status=None)) < 1:
                        return func(*args, **kwargs)
                    raise exceptions.APIException('The system has a deployed instance.')
                if option == 'running':
                    if int(CurrentClass.count_services(status=None)) > 0:
                        return func(*args, **kwargs)
                    raise exceptions.APIException('The system is available.')

            return wrapper

        return decorator

    def generate_files(self):
        """
        This function returns the proper docker-swarm file
        :return:  The generated object as Json and store it as yaml file
        """

        res = {'version': '3.7'}

        res['networks'] = {i.name: {'external': True} for i in self.model.networks}
        res['services'] = {}

        for blueprint in self.model.topology:  # add networks to services
            if blueprint.service not in self.model.services:
                raise Exception("Model error: There is no service with name %s" % blueprint.service)
            service = copy.deepcopy(self.model.services[blueprint.service])
            if 'networks' not in service:
                service['networks'] = {}
            else:
                service['networks'] = {i: {} for i in service['networks']}
            for network in blueprint.networks:
                if type(network) == str:
                    res['networks'][network] = {'external': True}
                    service['networks'][network] = {}
                elif type(network) == dict and 'name' in network:
                    res['networks'][network['name']] = {'external': True}
                    service['networks'][network['name']] = {}
            temp_node = self.model.node_object(blueprint.node)
            service['deploy'] = self.node_representation(temp_node)
            service['deploy']['replicas'] = blueprint.replicas
            res['services'][blueprint.service_name] = service
        yaml.dump(res, open(self.path + "fogified-swarm.yaml", 'w'), default_flow_style=False)
        return res

    def node_capabilities(self, node):
        metric = str(node.capabilities['memory'])[-1]
        if metric not in ["G", "M"]: raise Exception("Model does not provide other metrics than G or M")
        memory = str(node.capabilities['memory'])[:-1] if metric == "G" else str(node.capabilities['memory'])[
                                                                             :-1] / 1024
        memory = float(memory)
        lower_memory_bound = memory - memory * self.ram_oversubscription / 100
        cpu = node.capabilities['processor']['cores'] * node.capabilities['processor']['clock_speed'] / self.frequency
        lower_cpu_bound = cpu - cpu * self.cpu_oversubscription / 100
        return {
            'upper_cpu_bound': cpu,
            'lower_cpu_bound': lower_cpu_bound,
            'upper_memory_bound': memory,
            'lower_memory_bound': lower_memory_bound
        }

    def node_representation(self, node):
        """ Generate the Node template of docker-compose spec

        :param node: The specific node as described in Docker-swarm
        :return: The resource's template for docker-compose
        """
        real_specs = list({"node.labels." + i for i in node.node_specifications})
        res = {"placement": {"constraints": real_specs if len(real_specs) > 0 else []}}

        #  If node is a real device return "as-is"
        if "node.labels.main_cluster_node!=True" in real_specs: return res
        if "node.labels.main_cluster_node==False" in real_specs: return res

        #  Otherwise compute the constraints
        res["placement"]["constraints"].append("node.labels.main_cluster_node==True")
        caps = self.node_capabilities(node)
        res['resources'] = {
            'limits': {
                'cpus': "{0:.1f}".format(caps['upper_cpu_bound']),
                'memory': str(caps['upper_memory_bound']) + "G"
            },
            'reservations': {
                'cpus': "{0:.1f}".format(caps['lower_cpu_bound']),
                'memory': str(caps['lower_memory_bound']) + "G"
            }
        }
        return res

    def count_networks(self):
        """
        Counts the networks that are created
        :return: The number of created networks
        """
        return subprocess.getoutput('docker network ls | grep fogify | wc -l')


class DockerComposeConnector(CommonDockerSuperclass):

    @classmethod
    def count_services(cls, service_name: str = None, status: str = "Running") -> int:
        """
        Counts the services that are running
        :param service_name: The name of the service, if it does not exists, function returns all services
        :return: The number of running services
        """
        com = "docker ps --format '{{.Names}}' | grep fogify_"
        if service_name: com += ' | grep fogify_' + str(service_name)
        res = subprocess.getoutput(com + ' | wc -l')

        if len(res) > 0 and res.split(" ")[-1].isnumeric():
            return int(res.split(" ")[-1])
        return 0

    def deploy(self, timeout=60):
        """Deploy the emulated infrastructure
        :param timeout: The maximum number of seconds that the system waits until set the deployment as faulty
        """
        count = self.model.service_count()
        subprocess.check_output(
            ['docker-compose', '-f', self.path + self.file, '-p', 'fogify', '--compatibility', 'up', '-d'])

        if count is None: return

        finished = False
        for i in range(int(timeout / 5)):
            sleep(5)
            if self.count_services() == count:
                finished = True
                break
        if not finished:
            raise Exception("The process does not finish")

    def scale(self, service, instances):
        """ Executes a scaling action for specific instance's number

        :param service: The service that the system will scale
        :param instances: The number of Instances
        :return: Returns the result of the command execution
        """
        return subprocess.getoutput(
            'docker-compose -f ' + self.path + self.file + ' -p fogify --compatibility up --scale ' + service + "=" + str(
                instances) + " -d"
        )

    def get_all_instances(self):
        """
        Generates all instances of all services and in which node they run
        :return: a dictionary that has as keys the nodes and as values a set of running containers on each node
        """
        try:
            rows = subprocess.getoutput("""docker ps --format '{{.Names}}'""").split("\n")
            node_name = os.environ['MANAGER_NAME'] if 'MANAGER_NAME' in os.environ else 'localhost'
            fin_res = {node_name: []}
            for name in rows:
                if name.startswith("fogify_"):
                    fin_res[node_name].append(name)
            return fin_res
        except Exception:
            return {}

    def down(self, timeout=60):
        """Undeploys a running infrastructure

        :param timeout: The duration that the system will wait until it raises exception
        """
        try:
            subprocess.check_output(
                ['docker-compose',  '-f', self.path + self.file, '-p', 'fogify', 'down', '--remove-orphans']
            )
        except Exception as e:
            print(e)
        # check the services
        finished = False
        for i in range(int(timeout / 5)):
            sleep(5)
            if self.count_services() == 0:
                finished = True
                break
        if not finished:
            raise Exception("The deployment is not down")

        # check the networks
        # finished = False
        # for i in range(int(timeout / 5)):
        #     sleep(5)
        #     if self.count_networks().endswith('0'):
        #         finished = True
        #         break
        # if not finished:
        #     raise Exception("The networks are not down")

    def get_nodes(self):
        """Returns the physical nodes of the cluster

        :return: A dictionary of <Node-id: Node-ip>
        """
        name = os.environ['MANAGER_NAME'] if 'MANAGER_NAME' in os.environ else 'localhost'
        return {name: socket.gethostbyname(name)}

    def create_network(self, network):
        """Creates the overlay networks
        :param network: a network object contains network `name` and optional parameters of `subnet` and `gateway` of the network
        """
        com = ['docker', 'network', 'create', '-d', 'bridge', '--attachable', network['name']]
        subprocess.check_output(com)

    @classmethod
    def return_deployment(cls):
        client = docker.from_env()
        containers = client.containers.list()
        res = {}
        for container in containers:
            if container.name.startswith('fogify_'):
                service = container.attrs['Config']['Labels']["com.docker.compose.service"]
                if service not in res: res[service] = []
                res[service].append(container.name)
        return res

    @classmethod
    def event_attr_to_information(cls, event):

        attrs = event['Actor']['Attributes']
        service_name = None
        container_id = None
        container_name = None

        if 'com.docker.compose.project' in attrs and attrs['com.docker.compose.project'] == 'fogify':
            client = docker.from_env()
            container_id = event['id']
            service_name = attrs['com.docker.compose.service']
            container = client.containers.get(container_id)
            container_name = container.attrs['Name'].replace("/", "")
            client.close()
        return dict(
            service_name=service_name,
            container_id=container_id,
            container_name=container_name
        )

    @classmethod
    def instance_name(cls, alias: str) -> str:
        if alias.startswith("fogify_"):
            return alias[len("fogify_"):]
        else:
            return alias

    def get_running_container_processing(self, service):
        """ Find the number of the running containers for a service

        :param service: The name of the service
        :return: Return the number if the service exists otherwise None
        """
        try:
            return int(subprocess.getoutput("""docker inspect """ +
                                            "fogify_%s" % service + """ --format '{{.HostConfig.NanoCPUs}}'""")) / 1000000000
        except Exception as ex:
            print(ex)
            return None


class SwarmConnector(CommonDockerSuperclass):
    """
    The swarm implementation of Basic Connector of Fogify
    """

    def scale(self, service, instances):
        """ Executes a scaling action for specific instance's number

        :param service: The service that the system will scale
        :param instances: The number of Instances
        :return: Returns the result of the command execution
        """
        client = docker.from_env()
        for instance_service in client.services.list():
            if instance_service.name.startswith("fogify_") and str(instance_service.name).find(service) > -1:
                return instance_service.scale(instances)

    def get_running_container_processing(self, service):
        """ Find the number of the running containers for a service

        :param service: The name of the service
        :return: Return the number if the service exists otherwise None
        """
        try:
            print(service)
            return int(subprocess.getoutput("""docker service inspect """ +
                                            "fogify_%s" % service
                                            + """ --format '{{.Spec.TaskTemplate.Resources.Limits.NanoCPUs}}'""")) \
                   / 1000000000
        except Exception as ex:
            print(ex)
            return None

    def get_all_instances(self):
        """
        Generates all instances of all services and in which node they run
        :return: a dictionary that has as keys the nodes and as values a set of running containers on each node
        """
        try:
            res = [json.loads(s) for s in subprocess.getoutput(
                """docker stack ps -f "desired-state=running" --format '{ "{{.Name}}": "{{.Node}}" }' fogify""").split(
                "\n")]
            fin_res = {}
            for pair in res:
                for name in pair:
                    if pair[name] not in fin_res: fin_res[pair[name]] = []
                    fin_res[pair[name]].append(name)
            return fin_res
        except Exception:
            return {}

    @classmethod
    def count_services(cls, service_name: str = None, status: str = "Running"):
        """
        Counts the services that are running
        :param service_name: The name of the service, if it does not exists, function returns all services
        :return: The number of running services
        """
        com = 'docker stack ps fogify'
        if status: com += ' | grep ' + status
        if service_name: com += ' | grep ' + service_name
        res = subprocess.getoutput(com + ' | wc -l')
        if len(res) > 0 and res.split(" ")[-1].isnumeric():
            return int(res.split(" ")[-1])
        return 0

    def down(self, timeout=60):
        """Undeploys a running infrastructure

        :param timeout: The duration that the system will wait until it raises exception
        """
        try:
            subprocess.check_output(['docker', 'stack', 'rm', 'fogify'])
        except Exception as e:
            print(e)
        # check the services
        finished = False
        for i in range(int(timeout / 5)):
            sleep(5)
            if self.count_services() == 0:
                finished = True
                break

        if not finished: raise Exception("The deployment is not down")

        # check the networks
        finished = False
        for i in range(int(timeout / 5)):
            sleep(5)
            if self.count_networks().endswith('0'):
                finished = True
                break
        if not finished: raise Exception("The networks are not down")

    def get_nodes(self):
        """Returns the physical nodes of the cluster

        :return: A dictionary of <Node-id: Node-ip>
        """
        res = subprocess.check_output(
            [os.path.dirname(os.path.abspath(__file__)) + '/nodes.sh'], shell=True
        )
        res = res.decode('utf8').strip().split("\n")
        return {keyval[0]: socket.gethostbyname(keyval[1]) for keyval in [line.split(" - ") for line in res]}

    def deploy(self, timeout=60):
        """Deploy the emulated infrastructure
        :param timeout: The maximum number of seconds that the system waits until set the deployment as faulty
        """
        count = self.model.service_count()
        subprocess.check_output(
            ['docker', 'stack', 'deploy', '--prune', '--compose-file', self.path + self.file, 'fogify']
        )
        if count is None: return

        finished = False
        for i in range(int(timeout / 5)):
            sleep(5)
            cur_count = self.count_services()
            if str(cur_count) == str(count):
                finished = True
                break
        if not finished:
            raise Exception("The process does not finish")

    def inject_labels(self, labels={}, **kwargs):
        client = docker.from_env()
        for node in client.nodes.list():
            if node.attrs['Status']['Addr'] == kwargs['HOST_IP']:
                break
        labels.update(HostInfo.get_all_properties())
        labels['cpu_architecture'] = node.attrs["Description"]["Platform"]["Architecture"]
        labels['os'] = node.attrs["Description"]["Platform"]["OS"]

        if int(1000 * float(labels["cpu_hz_advertised_friendly"].split(" ")[0])) == self.frequency \
                and 'main_cluster_node' not in labels:
            labels['main_cluster_node'] = 'True'
        else:
            labels['main_cluster_node'] = 'False'

        node_spec = {'availability': node.attrs["Spec"]["Availability"],
                     'role': 'manager',
                     'Labels': labels
                     }

        node.update(node_spec)

    def get_manager_info(self):
        import docker
        client = docker.from_env()
        return client.swarm.attrs['JoinTokens']['Manager']

    def create_network(self, network):
        """Creates the overlay networks
        :param network: a network object contains network `name` and optional parameters of `subnet` and `gateway` of the network
        """
        subprocess.check_output(['docker', 'network', 'create', '-d', 'overlay', '--attachable', network['name']])

    @classmethod
    def return_deployment(cls):
        client = docker.from_env()
        services = client.services.list()
        res = {}
        for service in services:
            if service.name.startswith('fogify'):
                try:
                    res[service.name] = service.tasks()
                except Exception:
                    res[service.name] = []
        return res

    @classmethod
    def event_attr_to_information(cls, event) -> dict:
        attrs = event['Actor']['Attributes']
        service_name = None
        container_id = None
        container_name = None
        if 'com.docker.stack.namespace' in attrs and attrs['com.docker.stack.namespace'] == 'fogify':
            service_name = attrs['com.docker.swarm.service.name']
            container_id = event['id']
            container_name = attrs['com.docker.swarm.task.name']
        return dict(
            service_name=service_name,
            container_id=container_id,
            container_name=container_name
        )

    @classmethod
    def instance_name(cls, alias: str) -> str:
        if alias.startswith("fogify_"): alias = alias[len("fogify_"):]
        if alias.count(".") == 2: alias = alias[:alias.rfind(".")]
        return alias
