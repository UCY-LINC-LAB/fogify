import copy
import os
import yaml

from models.actions import NetworkAction, NetworkLinkAction


class BaseModel(object):

    def __init__(self, data={}):
        self.__dict__ = data

    def __repr__(self):
        return self.__str__()


class Node(BaseModel):
    name = ''
    capabilities = {}
    node_specifications = []

    def __str__(self):
        return "cpu: %s, memory: %s, node specifications: %s" %(self.capabilities['processor'], self.capabilities['memory'], self.node_specifications)



class Network(BaseModel):
    """ This class is the intermediate model of the network model"""
    capacity=None
    uplink={}
    downlink={}
    links=[]

    def get_bidirectional_links(self, res):
        if 'latency' in res:
            if 'delay' in res['latency']:
                latency = res['latency']['delay']
                latency = latency.strip()
                latency_metric = "ms"
                if latency.endswith('ms'):
                    latency = latency[:-2]
                if latency.endswith('s'):
                    latency = latency[:-1]
                    latency_metric = "s"
                res['latency']['delay'] = "%.2f" %(float(latency)/2) + latency_metric
                if 'deviation' in res['latency']:
                    deviation = res['latency']['deviation']
                    deviation = deviation.strip()
                    deviation_metric = "ms"
                    if deviation.endswith('ms'):
                        deviation = deviation[:-2]
                    if deviation.endswith('s'):
                        deviation = deviation[:-1]
                        deviation_metric = "s"
                    res['latency']['deviation'] =  "%.2f" %(float(deviation)/2) + deviation_metric
        if 'drop' in res:
            drop = res['drop'].strip()
            drop = drop[:-1] if drop.endswith('%') else drop
            res['drop'] = "%.2f" %(float(drop)/2) + '%'
        return NetworkAction(**res)

    def get_uplink(self):
        if self.uplink != {}:
            return NetworkAction(**self.uplink)
        elif hasattr(self, 'bidirectional'):
            return self.get_bidirectional_links(copy.deepcopy(self.bidirectional))
        else:
            raise Exception("You have to specify uplink or bidirectional characteristics (%s)"%self.__dict__)

    def get_downlink(self):
        if self.downlink != {}:
            return NetworkAction(**self.downlink)
        elif hasattr(self, 'bidirectional'):
            return self.get_bidirectional_links(copy.deepcopy(self.bidirectional))
        else:
            raise Exception("You have to specify uplink or bidirectional characteristics (%s)"%self.__dict__)
    def __str__(self):
        return "uplink: %s , downlink: %s "%(self.get_uplink(),self.get_uplink())

    def get_links(self):
        temp = {}
        for i in self.links:

            if 'from_node' in i and 'to_node' in i and 'properties' in i:
                if 'bidirectional' in i and str(i['bidirectional']).lower() == 'true':
                    if i['from_node'] not in temp:
                        temp[i['from_node']] = {}
                    if i['to_node'] not in temp:
                        temp[i['to_node']] = {}
                    temp[i['from_node']][i['to_node']] = self.get_bidirectional_links(copy.deepcopy(i['properties'])).get_command()
                    temp[i['to_node']][i['from_node']] = self.get_bidirectional_links(copy.deepcopy(i['properties'])).get_command()
                else:
                    if i['from_node'] not in temp:
                        temp[i['from_node']] = {}
                    temp[i['from_node']][i['to_node']] = NetworkAction(**i['properties']).get_command()
        return temp

    @property
    def network_record(self):
        res={}
        if self.capacity is not None:
            res['capacity'] = self.capacity
        res['uplink'] = self.get_uplink().get_command()
        res['downlink'] = self.get_downlink().get_command()
        res['links'] = self.get_links()
        return res


class Topology(object):
    """ This class represents a topology object capable to be translated to the underlying container orchestrator"""
    def __init__(self, node, service, label, replicas=1, networks=[]):
        self.node=node
        self.service=service
        self.label=label
        self.replicas=replicas
        self.networks=networks
    def __str__(self):
        return "node: %s, service: %s, replicas: %s, networks: %s " %( self.node,
                    self.service,
                    self.replicas,
                    self.networks)

    @property
    def service_name(self):
        return "%s"%(self.label)

class Deployment(BaseModel):
    """
    This class represents a deployment of a topology. In the deployment, there are many topologies,
    however, in the first version of Fogify users can only deploy one topology.
    """

    topology = []


    def get_topologies(self):
        return [Topology(**i) for i in self.topology]

    def __str__(self):
        return str([str(i) for i in self.get_topologies()])


class FogifyModel(object):
    """
    This class is responsible for parsing and translating the Fogify's model to an abstract representation.
    """

    nodes = []
    networks = []
    deployments = []

    def __init__(self, data):
        fogify=data["x-fogify"]
        self.services = data["services"] if "services" in data else []
        self.nodes = [Node(i) for i in fogify['nodes']] if 'nodes' in fogify else []
        self.networks = [Network(i) for i in fogify['networks']] if 'networks' in fogify else []
        self.deployment = Deployment({"topology": fogify['topology']}) if 'topology' in fogify else None

            # [Deployment(i) for i in fogify['deployments']] if 'deployments' in fogify else []

    @property
    def all_networks(self):
        res = []
        for network in self.networks:
            cur = {'name': network.name}
            if hasattr( network, 'subnet') and hasattr(network,'gateway'):
                cur['subnet'] = network.subnet
                cur['gateway'] = network.gateway
            res.append(cur)

        for topology in self.topology:
            service = copy.deepcopy(self.services[topology.service])
            if 'networks' in service:
                for network in service['networks']:
                    if network not in [i['name'] for i in res]:
                        res.append(
                            {"name": network}
                        )
        return res

    @property
    def topology(self):
        return self.deployment.get_topologies()

    def __repr__(self):
        return "Nodes: %s , Networks: %s , Deployment: %s , Services: %s"%(
            self.nodes,
            self.networks,
            self.deployment,
            self.services)


    def node_object(self, node_name):
        real_node = None
        for node in self.nodes:
            if node.name == node_name:
                real_node = node
                break
        if real_node is None:
            raise Exception("Model Error: the node specs do not exist")
        return real_node

    def network_object(self, network_name):
        real_node = None
        extra_name = ""
        if type(network_name) == dict:
            if 'uplink' not in network_name or 'downlink' not in network_name:
                if 'name' in network_name:
                    extra_name = network_name['name']
        if type(network_name) == str:
            extra_name = network_name
        for node in self.networks:
            if node.name == extra_name:
                real_node = node
                break
        if real_node is None and type(network_name) != str:
            return Network(network_name)

        if real_node is None:
            raise Exception("Model Error: the network specs do not exist")
        return real_node

    def service_count(self):
        sum = 0
        for i in self.topology:
            sum+=i.replicas
        return sum

    @property
    def topology(self):
        return self.deployment.get_topologies()

class NetworkGenerator(object):
    """
    It generates the network rules that are recognizable from the Fogify Agents
    """

    def __init__(self, model):
        self.model = model

    def generate_network_rules(self):
        res = {}
        mode_topology = self.model.topology
        for fognode in mode_topology:
            res[fognode.service_name] = {}
            for network_name in fognode.networks:
                network = self.model.network_object(network_name)
                if network is not None:
                    if fognode.service_name not in res:
                        res[fognode.service_name] = network.network_record

                    res[fognode.service_name][network.name] = network.network_record
        return res
