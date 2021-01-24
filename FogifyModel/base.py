import copy
from FogifyModel.actions import NetworkAction


class BaseModel(object):

    def __init__(self, data={}):
        self.__dict__ = data
        self.validate()

    def __repr__(self):
        return self.__str__()

    def validate(self):
        pass

class Node(BaseModel):
    name = ''
    capabilities = {}
    node_specifications = []

    def __str__(self):
        return "cpu: %s, memory: %s, node specifications: %s" % (
            self.capabilities['processor'], self.capabilities['memory'], self.node_specifications)

    def get_memory_unit(self) -> str:
        return self.get_memory()[-1]

    def get_memory(self) -> str:
        return self.capabilities['memory']

    def get_memory_value_in_gb(self) -> float:
        return float(self.get_memory()[:-1]) if self.get_memory_unit() == "G" else float(self.get_memory()[:-1]) / 1024
    
    def get_processor_cores(self):
        return int(self.capabilities['processor']['cores'])

    def get_processor_clock_speed(self):
        return int(self.capabilities['processor']['clock_speed'])

    def get_specifications(self) -> []:
        return self.node_specifications
    
    def validate(self):
        if self.get_memory_unit() not in ["G", "M"]: raise Exception("Model does not provide other metrics than G or M")

class Network(BaseModel):
    """ This class is the intermediate model of the network model"""
    capacity = None
    uplink = {}
    downlink = {}
    links = []

    @classmethod
    def get_bidirectional_links(cls, input):
        res = copy.deepcopy(input)
        if 'latency' in res:
            if 'delay' in res['latency']:
                latency = res['latency']['delay']
                latency = str(latency).strip()
                latency_metric = "ms"
                if latency.endswith('ms'):
                    latency = latency[:-2]
                if latency.endswith('s'):
                    latency = latency[:-1]
                    latency_metric = "s"
                res['latency']['delay'] = "%.2f" % (float(latency) / 2) + latency_metric
                if 'deviation' in res['latency']:
                    deviation = res['latency']['deviation']
                    deviation = deviation.strip()
                    deviation_metric = "ms"
                    if deviation.endswith('ms'):
                        deviation = deviation[:-2]
                    if deviation.endswith('s'):
                        deviation = deviation[:-1]
                        deviation_metric = "s"
                    res['latency']['deviation'] = "%.2f" % (float(deviation) / 2) + deviation_metric
        if 'drop' in res:
            drop = res['drop'].strip()
            drop = drop[:-1] if drop.endswith('%') else drop
            res['drop'] = "%.2f" % (float(drop) / 2) + '%'
        return NetworkAction(**res)

    def get_uplink(self):
        if self.uplink != {}:
            return NetworkAction(**self.uplink)
        elif hasattr(self, 'bidirectional'):
            return self.get_bidirectional_links(copy.deepcopy(self.bidirectional))
        else:
            raise Exception("You have to specify uplink or bidirectional characteristics (%s)" % self.__dict__)

    def get_downlink(self):
        if self.downlink != {}:
            return NetworkAction(**self.downlink)
        elif hasattr(self, 'bidirectional'):
            return self.get_bidirectional_links(copy.deepcopy(self.bidirectional))
        else:
            raise Exception("You have to specify uplink or bidirectional characteristics (%s)" % self.__dict__)

    def __str__(self):
        return "uplink: %s , downlink: %s " % (self.get_uplink(), self.get_uplink())

    @property
    def get_links(self):
        res = []
        for i in self.links:
            res.extend(self.get_link(i))
        return res

    @classmethod
    def get_link(cls, link):
        temp = []
        from_to, to_from = cls.get_link_rules(copy.deepcopy(link))
        if from_to:
            temp.append(dict(
                from_node=link['from_node'], to_node=link['to_node'], command=from_to))
        if to_from:
            temp.append(dict(
                from_node=link['to_node'], to_node=link['from_node'], command=to_from))
        return temp


    @classmethod
    def get_link_rules(cls, link):
        from_to, to_from = None, None
        if 'from_node' in link and 'to_node' in link:

            if 'properties' in link:
                from_to = {
                    'uplink': cls.get_bidirectional_links(link['properties']).get_command(),
                    'downlink': cls.get_bidirectional_links(link['properties']).get_command(),
                }

            elif 'uplink' in link and 'downlink' in link:
                from_to = {
                    'uplink': NetworkAction(**link['uplink']).get_command(),
                    'downlink': NetworkAction(**link['downlink']).get_command()}
            else:
                raise Exception("The link has not the proper structure", str(link))
            if 'bidirectional' in link and link['bidirectional']:
                to_from = {
                    'uplink': from_to['uplink'],
                    'downlink': from_to['downlink'],
                }
        return from_to, to_from


    @property
    def network_record(self):
        res = {}
        if self.capacity is not None: res['capacity'] = self.capacity
        res['uplink'] = self.get_uplink().get_command()
        res['downlink'] = self.get_downlink().get_command()
        # res['links'] = self.get_links()
        return res


class Topology(object):
    """ This class represents a topology object capable to be translated to the underlying container orchestrator"""

    def __init__(self, node, service, label, replicas=1, networks=[]):
        self.node = node
        self.service = service
        self.label = label
        self.replicas = replicas
        self.networks = networks

    def __str__(self):
        return "node: %s, service: %s, replicas: %s, networks: %s " % (self.node,
                                                                       self.service,
                                                                       self.replicas,
                                                                       self.networks)

    @property
    def service_name(self):
        return "%s" % (self.label)


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
        fogify = data["x-fogify"]
        self.services = data["services"] if "services" in data else []
        self.nodes = [Node(i) for i in fogify['nodes']] if 'nodes' in fogify else []
        self.networks = [Network(i) for i in fogify['networks']] if 'networks' in fogify else []
        self.deployment = Deployment({"topology": fogify['topology']}) if 'topology' in fogify else None


    @property
    def all_networks(self):
        res = [{'name': network.name} for network in self.networks]
        res = self.__get_networks_from_services(res)
        return res

    def __get_networks_from_services(self, res):
        for topology in self.topology:
            service = copy.deepcopy(self.services[topology.service])
            if 'networks' not in service: continue
            for network in service['networks']:
                if network not in [i['name'] for i in res]:
                    res.append({"name": network})
        return res

    @property
    def topology(self):
        return self.deployment.get_topologies()

    def __repr__(self):
        return "Nodes: %s , Networks: %s , Deployment: %s , Services: %s" % (
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

    def network_object(self, network_object):
        real_node = None
        extra_name = ""
        if type(network_object) == dict:
            up_down_links = 'uplink' not in network_object or 'downlink' not in network_object
            bidirectional = 'bidirectional' not in network_object
            if up_down_links and bidirectional:
                if 'name' in network_object:
                    extra_name = network_object['name']
        if type(network_object) == str:
            extra_name = network_object
        for node in self.networks:
            if node.name == extra_name:
                real_node = node
                break

        if real_node is None and type(network_object) != str: return Network(network_object)

        if real_node is None: raise Exception("Model Error: the network specs do not exist")

        return real_node

    def service_count(self): return sum([i.replicas for i in self.topology])

    @property
    def topology(self): return self.deployment.get_topologies()

    def generate_network_rules(self):
        res = {}
        mode_topology = self.topology
        for fognode in mode_topology:
            res[fognode.service_name] = {}
            for network_name in fognode.networks:
                network = self.network_object(network_name)

                if network is None: continue

                if fognode.service_name not in res:
                    res[fognode.service_name] = network.network_record

                res[fognode.service_name][network.name] = network.network_record
                res[fognode.service_name][network.name]['links'] = \
                    [i for i in network.get_links if i['from_node'] == fognode.service_name]

        return res



