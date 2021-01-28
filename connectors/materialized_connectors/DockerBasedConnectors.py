import copy
import json
import logging
import os
import socket
import subprocess
from time import sleep
import docker
from flask_api import exceptions
from utils.host_info import HostInfo
from FogifyModel.base import Node, FogifyModel
from connectors.base import BasicConnector


class CommonDockerSuperclass(BasicConnector):

    def __init__(self,
                 model: FogifyModel = None,
                 path=os.getcwd() + os.environ['UPLOAD_FOLDER'] if 'UPLOAD_FOLDER' in os.environ else "",
                 frequency=float(os.environ['CPU_FREQ']) if 'CPU_FREQ' in os.environ else 2400.0,
                 cpu_oversubscription=
                 float(os.environ[
                         'CPU_OVERSUBSCRIPTION_PERCENTAGE']) if 'CPU_OVERSUBSCRIPTION_PERCENTAGE' in os.environ else 0.0,
                 ram_oversubscription=
                 float(os.environ[
                         'RAM_OVERSUBSCRIPTION_PERCENTAGE']) if 'RAM_OVERSUBSCRIPTION_PERCENTAGE' in os.environ else 0.0,
                 node_name=os.environ['MANAGER_NAME'] if 'MANAGER_NAME' in os.environ else 'localhost',
                 host_ip=os.environ['HOST_IP'] if 'HOST_IP' in os.environ else None
                 ):
        self.model = model
        self.frequency = frequency
        self.path = path
        self.file = "fogified-swarm.yaml"
        self.cpu_oversubscription = cpu_oversubscription
        self.ram_oversubscription = ram_oversubscription
        self.node_name = node_name
        self.host_ip = host_ip

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

        return res

    def node_representation(self, node: Node):
        real_specs = list({"node.labels." + i for i in node.get_specifications()})
        res = {"placement": {"constraints": real_specs if len(real_specs) > 0 else []}}

        #  If node is a real device return "as-is"
        if "node.labels.main_cluster_node!=True" in real_specs: return res
        if "node.labels.main_cluster_node==False" in real_specs: return res

        #  Otherwise compute the constraints
        res["placement"]["constraints"].append("node.labels.main_cluster_node==True")
        caps = self.__node_capabilities(node)
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
        count = subprocess.getoutput('docker network ls | grep fogify | wc -l')
        return int(count) if count.isnumeric() else -1

    def __node_capabilities(self, node: Node):
        memory = node.get_memory_value_in_gb()
        lower_memory_bound = memory - memory * self.ram_oversubscription / 100
        cpu = node.get_processor_cores() * node.get_processor_clock_speed() / self.frequency
        lower_cpu_bound = cpu - cpu * self.cpu_oversubscription / 100
        return {
            'upper_cpu_bound': cpu,
            'lower_cpu_bound': lower_cpu_bound,
            'upper_memory_bound': memory,
            'lower_memory_bound': lower_memory_bound
        }

    def inject_labels(self, labels={}, **kwargs):
        pass

    def get_container_ips(self, container_id):
        nets = json.loads(
            subprocess.getoutput("docker inspect --format '{{json .NetworkSettings.Networks}}' %s" % container_id))
        return {network: nets[network]['IPAddress'] for network in nets}

    def get_host_data_path(self, container_id):
        try:
            return subprocess.getoutput("docker inspect --format='{{.GraphDriver.Data.MergedDir}}' %s" % container_id)
        except Exception:
            logging.error("The system did not find the host's docker disk space (that is used for user-defined metrics).",
                          exc_info=True)
            return None


class DockerComposeConnector(CommonDockerSuperclass):

    @classmethod
    def count_services(cls, service_name: str = None, status: str = "Running") -> int:
        com = "docker ps --format '{{.Names}}' | grep fogify_"
        if service_name: com += ' | grep fogify_' + str(service_name)
        res = subprocess.getoutput(com + ' | wc -l')

        if len(res) > 0 and res.split(" ")[-1].isnumeric():
            return int(res.split(" ")[-1])
        return 0

    def deploy(self, timeout=60):
        count = self.model.service_count()
        subprocess.check_output(
            ['docker-compose', '-f', self.path + self.file, '-p', 'fogify', '--compatibility', 'up', '-d'])

        if count is None: return

        finished = False
        for i in range(int(timeout / 5)):
            sleep(5)
            finished = self.count_services() == count
            if finished: return
        if not finished:
            raise Exception("The process does not finish")

    def scale(self, service, instances):
        return subprocess.getoutput(
            'docker-compose -f ' + self.path + self.file + ' -p fogify --compatibility up --scale ' + service + "=" + str(
                instances) + " -d"
        )

    def get_all_instances(self):
        try:
            rows = subprocess.getoutput("""docker ps --format '{{.Names}}'""").split("\n")
            node_name = self.node_name
            fin_res = {node_name: []}
            for name in rows:
                if name.startswith("fogify_"):
                    fin_res[node_name].append(name)
            return fin_res
        except Exception:
            logging.error("The connector could not return the docker instances.",
                          exc_info=True)
            return {}

    def down(self, timeout=60):
        try:
            subprocess.check_output( ['docker-compose', '-f', self.path + self.file, '-p', 'fogify', 'down', '--remove-orphans'] )
        except Exception as e:
            logging.error("The undeploy failed. Please undeploy the stack manually (e.g. docker stop $(docker ps -q) )",
                          exc_info=True)
        # check the services
        finished = False
        for i in range(int(timeout / 5)):
            sleep(5)
            finished = self.count_services() == 0
            if finished: return

        if not finished:
            logging.error("The services did not removed yet. Please check the issue manually.",
                          exc_info=True)

    def get_nodes(self):
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
        service_name, container_id, container_name = None, None, None

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
        try:
            com = "docker inspect fogify_%s --format '{{.HostConfig.NanoCPUs}}'" % service
            return int(subprocess.getoutput(com)) / 1000000000
        except Exception as ex:
            print(ex)
            return None

    def get_container_ip_for_network(self, container_id, network):
        nets = self.get_container_ips(container_id)
        if network not in nets: return None
        return nets[network]

    def get_ips_for_service(self, service):

        res = {}
        if not service.startswith("fogify_"): service = "fogify_" + service
        com = """docker ps --format '{ "{{ .Names }}": "{{.ID}}" }' | grep %s""" % service
        name_id_pairs = subprocess.getoutput(com).split("\n")
        containers = []
        for name_id_pair in name_id_pairs:
            try:
                containers.append(json.loads(name_id_pair))
            except Exception as ex:
                logging.warning('The service %s returns invalid Container-ip %s' % (service, name_id_pair))

        for container in containers:
            for name in container:
                for net, ip in self.get_container_ips(container[name]).items():
                    if net not in res: res[net] = []
                    res[net].append(ip)
        return res


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
            is_fogifyed = instance_service.name.startswith("fogify_")
            contains_service_name = str(instance_service.name).find(service) > -1
            if is_fogifyed and contains_service_name:
                return instance_service.scale(instances)

    def get_running_container_processing(self, service):
        try:
            com = "docker service inspect fogify_%s  --format '{{.Spec.TaskTemplate.Resources.Limits.NanoCPUs}}'" % service
            return int(subprocess.getoutput(com))/1000000000
        except Exception as ex:
            print(ex)
            return None

    def get_all_instances(self):
        try:
            name_node_pairs = [json.loads(s) for s in subprocess.getoutput(
                """docker stack ps -f "desired-state=running" --format '{ "{{.Name}}": "{{.Node}}" }' fogify""").split(
                "\n")]
            res = {}
            for pair in name_node_pairs:
                for name, node in pair.items():
                    if node not in res: res[node] = []
                    res[node].append(name)
            return res
        except Exception:
            return {}

    @classmethod
    def count_services(cls, service_name: str = None, status: str = "Running"):
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

        if count is None: return

        subprocess.check_output(
            ['docker', 'stack', 'deploy', '--prune', '--compose-file', self.path + self.file, 'fogify']
        )

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
        node = self.__get_host_node()
        if not node: return
        labels = self.__transform_labels(labels, node)
        node_spec = {'availability': node.attrs["Spec"]["Availability"],
                     'role': 'manager',
                     'Labels': labels
                     }
        node.update(node_spec)

    def __transform_labels(self, labels, node):
        labels['cpu_architecture'] = node.attrs["Description"]["Platform"]["Architecture"]
        labels['os'] = node.attrs["Description"]["Platform"]["OS"]
        hosts_cpu_freq = int(1000 * float(labels["cpu_hz_advertised_friendly"].split(" ")[0]))
        is_main_cluster_node = 'main_cluster_node' not in labels
        has_cluster_node_freq = hosts_cpu_freq == self.frequency
        if "cpu_hz_advertised_friendly" not in labels:
            labels['main_cluster_node'] = 'True'
        elif has_cluster_node_freq and is_main_cluster_node:
            labels['main_cluster_node'] = 'True'
        else:
            labels['main_cluster_node'] = 'False'
        return labels

    def __get_host_node(self):
        client = docker.from_env()
        for node in client.nodes.list():
            if node.attrs['Status']['Addr'] == self.host_ip:
                return node
        return None

    def get_manager_info(self):
        return docker.from_env().swarm.attrs['JoinTokens']['Manager']

    def create_network(self, network):
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
        service_name, container_id, container_name = None, None, None
        belongs_to_fogify_stack = 'com.docker.stack.namespace' in attrs and attrs['com.docker.stack.namespace'] == 'fogify'
        if belongs_to_fogify_stack:
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

    def get_ips_for_service(self, service):
        if not service.startswith("fogify_"): service = "fogify_" + service
        ids = self.__get_container_ids_from_service(service)
        return self.__get_ips_from_container_ids(ids)

    def __get_container_ids_from_service(self, service):
        list_of_container_pairs = [json.loads(s) for s in subprocess.getoutput(
            """docker stack ps -f "desired-state=running" --format '{ "{{.Name}}": "{{.ID}}" }' fogify""").split("\n")]
        ids = []
        for pair in list_of_container_pairs:
            for name, id in pair.items():
                if name.startswith(service): ids.append(id)
        return ids

    def __get_ips_from_container_ids(self, ids):
        res = {}
        for id in ids:
            networks = json.loads(
                subprocess.getoutput("""docker inspect --format='{{json .NetworksAttachments}}' %s""" % id))
            if not networks: continue
            for network in networks:
                net_name = network['Network']['Spec']['Name']
                addresses = network['Addresses']
                if net_name not in res: res[net_name] = []
                res[net_name] += [address.replace("/24", "") for address in addresses]
        return res
