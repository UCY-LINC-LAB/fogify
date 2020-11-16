import copy
import json
import os
import socket
import subprocess
from time import sleep
from flask_api import exceptions
import yaml

from utils.host_info import HostInfo


class BasicConnector(object):

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

    def inject_labels(self, labels={}):
        pass

    def initialize(self, **kwargs):
        pass



class SwarmConnector(BasicConnector):
    """
    The swarm implementation of Basic Connector of Fogify
    """

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

    @classmethod
    def check_status(cls, *_args, **_kwargs):
        def decorator(func):
            def wrapper(*args, **kwargs):
                options = ['available', 'running']
                if not len(_args) > 0:
                    raise exceptions.APIException('You have to select at least one option:'+str(options))
                option = str(_args[0])
                if option not in options:
                    raise exceptions.APIException('You have to select an option from:' + str(options))
                if option == 'available':
                    if int(str(SwarmConnector.count_services(status=None))[-1]) < 1:
                        return func(*args, **kwargs)
                    else:
                        raise exceptions.APIException('The system has a deployed instance.')
                if option == 'running':
                    if int(SwarmConnector.count_services(status=None)) > 0:
                        return func(*args, **kwargs)
                    else:
                        raise exceptions.APIException('The system is available.')
            return wrapper
        return decorator

    def generate_files(self):
        """
        This function returns the proper docker-swarm file
        :return:  The generated object as Json and store it as yaml file
        """

        res = { 'version' : '3.7' }

        # generate networks
        res['networks']={
            i.name: {
                'external': True
            } for i in self.model.networks}

        res['services']={}
        deployment = self.model.topology

        for topology in deployment:
            if topology.service not in self.model.services:
                raise Exception("Model error: There is no service with name %s"%topology.service)
            service = copy.deepcopy(self.model.services[topology.service])
            if 'networks' not in service:
                service['networks']={}
            else:
                service['networks'] = {i:{} for i in service['networks']}
            for network in topology.networks:
                if type(network) == str:
                    res['networks'][network]={
                        'external': True
                    }
                    service['networks'][network] = {}
                    # service['networks']+=[network]
                else:
                    if 'name' in network:
                        res['networks'][network['name']] = {
                            'external': True
                        }
                        if 'ip' in network:
                            network['IP'] = network['ip']
                        if 'IP' in network:
                            service['networks'][network['name']] = {'ipv4_address': network['IP']}
                            # obj = {network['name']:{'ipv4_address': network['IP']}}
                        else:
                            service['networks'][network['name']] = {}
                        # service['networks'] += [obj]
            temp_node=self.model.node_object(topology.node)
            service['deploy']= self.node_representation(temp_node)
            service['deploy']['replicas']=topology.replicas
            res['services'][topology.service_name]=service
        yaml.dump(res, open(self.path + "fogified-swarm.yaml", 'w'), default_flow_style=False)
        return res


    def node_representation(self, node):
        """ Generate the Node template of docker-compose spec

        :param node: The specific node as described in Docker-swarm
        :return: The resource's template for docker-compose
        """
        real_specs = list({"node.labels."+i for i in node.node_specifications})
        res = { "placement": {"constraints": []} }
        if len(real_specs) > 0:
            res = {
                "placement": {
                    "constraints": real_specs
                }
            }

        for i in real_specs:
            if i == "node.labels.main_cluster_node!=True" or i == "node.labels.main_cluster_node==False":
                print(i)
                return res
        res["placement"]["constraints"].append("node.labels.main_cluster_node==True")
        if str(node.capabilities['memory'])[-1]=="G":
            memory = float(str(node.capabilities['memory'])[:-1])
        elif str(node.capabilities['memory'])[-1]=="M":
            memory = float(str(node.capabilities['memory'])[:-1])/1024
        else:
            raise Exception("Model does not provide other metrics than G or M")
        lower_memory_bound = memory-memory*self.ram_oversubscription/100
        cpu = node.capabilities['processor']['cores']*node.capabilities['processor']['clock_speed']/self.frequency
        lower_cpu_bound = cpu - cpu*self.cpu_oversubscription/100
        res['resources'] = {
                    'limits':{
                        'cpus': "{0:.1f}".format(cpu),
                        'memory': str(memory)+"G"
                    },
                    'reservations':{
                        'cpus': "{0:.1f}".format(lower_cpu_bound),
                        'memory': str(lower_memory_bound)+"G"
                    }
                }
        return res

    def scale(self, service, instances):
        """ Executes a scaling action for specific instance's number

        :param service: The service that the system will scale
        :param instances: The number of Instances
        :return: Returns the result of the command execution
        """
        return subprocess.getoutput(
            'docker service scale fogify_'+service+"="+str(instances)
        )

    def get_running_container_processing(self, service):
        """ Find the number of the running containers for a service

        :param service: The name of the service
        :return: Return the number if the service exists otherwise None
        """
        try:
            return int(subprocess.getoutput("""docker service inspect """+
                     "fogify_"+service+""" --format '{{.Spec.TaskTemplate.Resources.Limits.NanoCPUs}}'"""))/1000000000
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
            for i in res:
                for j in i:
                    if i[j] not in fin_res:
                        fin_res[i[j]]=[]
                    fin_res[i[j]].append(j)
            return fin_res
        except Exception:
            return {}

    @classmethod
    def count_services(cls, service_name=None, status="Running"):
        """
        Counts the services that are running
        :param service_name: The name of the service, if it does not exists, function returns all services
        :return: The number of running services
        """
        try:
            com = 'docker stack ps fogify'
            if status:
                com += ' | grep '+status
            if service_name:
                com += 'grep fogify_' + str(service_name)
            res = subprocess.getoutput(com+' | wc -l')
            try:
                return int(res.split(" ")[-1])
            except Exception:
                return 0
        except Exception as e:
            print(e)

    def count_networks(self):
        """Counts the networks that are created

        :return: The number of created networks
        """
        try:
            return subprocess.getoutput(
                'docker network ls | grep fogify | wc -l'
            )
        except Exception as e:
            print(e)

    def down(self, timeout=60):
        """Undeploys a running infrastructure

        :param timeout: The duration that the system will wait until it raises exception
        """
        try:
            subprocess.check_output(
                ['docker', 'stack', 'rm', 'fogify']
            )
        except Exception as e:
            print(e)
        # check the services
        finished = False
        for i in range(int(timeout/5)):
            sleep(5)
            if self.count_services() == 0:
                finished = True
                break
        if not finished:
            raise Exception("The deployment is not down")

        # check the networks
        finished = False
        for i in range(int(timeout/5)):
            sleep(5)
            if self.count_networks().endswith('0'):
                finished = True
                break
        if not finished:
            raise Exception("The networks are not down")

    def get_nodes(self):
        """Returns the physical nodes of the cluster

        :return: A dictionary of <Node-id: Node-ip>
        """
        res = subprocess.check_output(
            [os.path.dirname(os.path.abspath(__file__)) +'/nodes.sh'], shell=True
        )
        res = res.decode('utf8').strip().split("\n")
        return {keyval[0]: socket.gethostbyname(keyval[1]) for keyval in [line.split(" - ") for line in res]}

    def deploy(self,  timeout=60):
        """Deploy the emulated infrastructure
        :param timeout: The maximum number of seconds that the system waits until set the deployment as faulty
        """
        count = self.model.service_count()
        subprocess.check_output(
            ['docker', 'stack', 'deploy', '--prune', '--compose-file', self.path+self.file , 'fogify']
        )
        if count is None:
            return
        finished = False
        for i in range(int(timeout/5)):
            sleep(5)
            cur_count = self.count_services()
            if str(cur_count) == str(count):
                finished = True
                break
        if not finished:
            raise Exception("The process does not finish")

    def create_network(self, network):
        """Creates the overlay networks
        :param network: a network object contains network `name` and optional parameters of `subnet` and `gateway` of the network
        """
        com = ['docker', 'network', 'create', '-d', 'overlay', '--attachable', network['name']]
        if 'subnet' in network and 'gateway' in network:
            com.append('--subnet')
            com.append(network['subnet'])
            com.append('--gateway')
            com.append(network['gateway'])
        subprocess.check_output(com)

    def inject_labels(self, labels={}, **kwargs):
        import docker
        # name = socket.gethostname()
        client = docker.from_env()
        for node in client.nodes.list():
            if node.attrs['Status']['Addr'] == kwargs['HOST_IP']:
                break
        labels.update(HostInfo.get_all_properties())
        labels['cpu_architecture'] = node.attrs["Description"]["Platform"]["Architecture"]
        labels['os'] = node.attrs["Description"]["Platform"]["OS"]

        if int(1000*float(labels["cpu_hz_advertised_friendly"].split(" ")[0])) == self.frequency \
                and 'main_cluster_node' not in labels:
            labels['main_cluster_node'] = 'True'
        else:
            labels['main_cluster_node'] = 'False'

        node_spec = {'availability': node.attrs["Spec"]["Availability"],
                     # 'name': node.attrs["Spec"]['name'],
                     'role': 'manager',
                     'Labels': labels
                     }

        node.update(node_spec)


    def initialize(self, **kwargs):
        import docker
        client = docker.from_env()
        if kwargs['MANAGER_IP'] == kwargs['HOST_IP']:
            try:
                client.swarm.init(kwargs['advertise_addr'])
            except Exception as ex:
                pass
        else:
            client = docker.from_env()
            try:
                client.swarm.join(remote_addrs=[kwargs['MANAGER_IP']], join_token=kwargs['join_token'])
            except Exception as ex:
                client.swarm.leave(force=True)
                client.swarm.join(remote_addrs=[kwargs['MANAGER_IP']], join_token=kwargs['join_token'])

    def get_manager_info(self):
        import docker
        client = docker.from_env()
        return client.swarm.attrs['JoinTokens']['Manager']