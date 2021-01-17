import codecs
import logging
import os
import subprocess
import threading
import time
import docker
import yaml
from connectors import BasicConnector
from utils.docker_manager import ContainerNetworkNamespace, get_containers_adapter_for_network
from utils.inter_communication import Communicator
from utils.sniffer import SnifferHandler
import traceback

class NetworkController(object):
    """
    This class applies the network QoS to the container's interfaces and starts the sniffer (if sniffer is enabled)
    Specifically, a subprocess observes the docker socket and if a new fogify container starts,
    the processes of this class ensure that both network QoS will be applied and the packet monitoring.
    """

    def __init__(self,
                 connector: BasicConnector,
                 sniffer: SnifferHandler = SnifferHandler()):
        self.connector = connector
        self.sniffer = sniffer


    def save_network_rules(self, data):
        """
        This function is responsible to save the network rules to a specific path.
        Since the network rules can be either a file(from deploy API) or a dictionary(from action API),
        the method performs a different process based on data type
        :param data: Network Rules in a dictionary form or in a file object
        :param path: A standard path that the network rules will be saved
        :return: None
        """
        path = self.connector.path
        if not os.path.exists(path): os.mkdir(path)
        if type(data) == dict:
            yaml.dump(data, open(os.path.join(path, "network.yaml"), 'w') , default_flow_style=False)
            return
        data.save(os.path.join(path, "network.yaml"))

    def apply_net_qos(self, service_name: str, container_id :str, container_name: str, network_rules: dict):
        """
        The method retrieves the network rules for a specific service, applies them and,
        finally, if other instances will be effected (e.g. via network links) it notifies the controller about the changes
        :param service_name: The name of the service
        :param container_id: The container's id
        :param container_name: The container's name
        :param network_rules: A dictionary with the network rules
        :return: None
        """
        clear_name = service_name.replace("fogify_", "")
        network_rules = network_rules[clear_name]

        self.execute_network_commands(clear_name, container_id, container_name, network_rules)

        self.communicate_with_controller(network_rules)

    def execute_network_commands(self, service_name: str, container_id :str, container_name: str, network_rules: dict, create="TRUE"):
        for network in network_rules:
            with ContainerNetworkNamespace(container_id):

                eth, ifb = NetworkController.get_adapters(container_name, network, container_id)

                NetworkController.apply_network_rule(eth, ifb,
                                   network_rules[network]['downlink'].replace("  ", " "),
                                   network_rules[network]['uplink'].replace("  ", " "),
                                   create=create
                                   )

                ips_to_rule = self.ips_to_rule(service_name, network, network_rules)
                commands = self.get_link_rules(eth, 'ifb' + ifb, ips_to_rule)
                subprocess.Popen('/bin/bash', stdin=subprocess.PIPE, stdout=subprocess.PIPE).communicate(commands.encode())




    @classmethod
    def get_adapters(cls, container_name, network, container_id):
        """
        This method return the container's adapter for a specific network
        along with the identifier of the Fogify's egress virtual adapter.
        :param container_name: The container's name
        :param network: Network name
        :param container_id: Container's id
        :return: "adapter" that is the current adapter of the container, "ifb_interface" the egress identifier
        """

        container_id = container_id[:10]
        adapter = None
        count = 0
        while (adapter is None and count < 3):
            adapter = get_containers_adapter_for_network(container_name, network)
            time.sleep(1)
            count += 1
        if not adapter: return None, None
        ifb_interface = container_id + adapter[-1]
        return adapter, ifb_interface



    def communicate_with_controller(self, network_rules):
        """
        This method notifies the controller about the updates that will be needed due to a new container
        :param network_rules: network rule dict
        :return: None
        """

        services = set()  # services that will need update
        for network in network_rules:
            if 'links' not in network_rules[network]: continue
            for link in network_rules[network]['links']:
                if 'to_node' not in link: continue
                services.add(link['to_node'])

        Communicator(self.connector).controller__link_updates(services)


    def get_link_rules(self, interface, ifb_interface, ips_to_rule):
        """
        Performs network QoS links to the specific instances
        :param interface: ingress (initial) interface of the container
        :param ifb_interface: egress virtual interface
        :param ips_to_rule: specific rules for this interface
        :return: None
        """
        commands = " "
        for str_ips in ips_to_rule:
            ips = str_ips.split("|")
            for ip in ips:
                rule_id = ip.split(".")[-1]
                for i in ['downlink', 'uplink']:
                    eth = interface if i == 'downlink' else ifb_interface
                    _type = 2 if i == 'downlink' else 1
                    commands+=self.generate_string_link_rule(eth, rule_id, ip, ips_to_rule[str_ips][i], _type)
        return commands



    def generate_string_link_rule(self, eth, rule_id, ip, rule, _type):
        """
        Command link generator for link connections between emulated nodes
        :param eth: The network interface of the emulated node
        :param rule_id: An id of the specific rule. Specifically, last number of the network ip of the emulated node as rule id
        :param ip: The ip of the emulated node for the specific eth
        :param rule: The netem command
        :param _type: A number that specifies the rule type (1 for uplink, 2 for downlink)
        :return: The generated command lines
        """


        rule_id = int(rule_id) + 11 # due to the default rules that the system has already built (see file apply_rules.sh)
        res = 'tc class add dev %s parent %s: classid %s:%s htb rate 10000mbit' % (eth,_type, _type, rule_id) + " \n"

        res += 'tc qdisc add dev %s parent %s:%s handle %s: netem %s ' % (eth, _type, rule_id, rule_id, rule) + " \n"
        if _type == 2: # Downlink
            res += "tc filter add dev %s parent %s: protocol ip prio 1 u32 match ip dst %s match ip src 0.0.0.0/0 flowid %s:%s " % (eth , _type, ip, _type, rule_id) + " \n"
        if _type == 1: # uplink
            res += "tc filter add dev %s parent %s: protocol ip prio 1 u32 match ip src %s match ip dst 0.0.0.0/0 flowid %s:%s " % (eth , _type, ip, _type, rule_id) + " \n"
        return res


    def ips_to_rule(self, service_name, network, network_rules):
        """
        Returns a dictionary with a concatenated list of ips and the necessary commands.
        Since a service will have similar connectivity with all "to_node" services
        :param service_name: the service name
        :param network: the specific network name
        :param network_rules: the network rules
        :return: A dictionary with keys all ips separated with "|" and the NetEm command as value
        """
        f_name = service_name.replace("fogify_", "")
        res = {}
        if 'links' in network_rules[network]:
            for link in network_rules[network]['links']:
                if link['from_node'] == f_name and 'to_node' in link:

                    network_ips = self.connector.get_ips_for_service(link['to_node'])
                    if network not in network_ips: continue
                    res["|".join(network_ips[network])] = link['command']
        return res

    def check_starting_condition(self, event):
        """
        Evaluates if the event docker socket is a starting container event
        :param event: The docker socket event
        :return: True or False based on the rule
        """
        return 'status' in event and event['status'] == 'start' and 'Type' in event and event['Type']=='container'

    def start_thread_for_qos(self, service_name, container_id, container_name, network_rules):
        """
        This function starts a new thread in order to apply the network QoS on a specific emulated instance
        """
        threading.Thread(
            target=NetworkController.apply_net_qos, args=(
                self, service_name, container_id, container_name, network_rules
            )).start()

    def listen(self):
        """
        The long-running method for observing the events of docker socket
        and applying both network QoS and sniffer on new created containers.
        :return: None
        """
        connector = self.connector

        if self.sniffer.is_sniffer_enabled(): self.start_thread_for_sniffing_storage()

        client = docker.from_env()
        for event in client.events(decode=True):

            try:
                if not self.check_starting_condition(event): continue
                info = connector.event_attr_to_information(event)
                if not (info['service_name'] and info['container_id'] and info['container_name']): continue

                network_rules = self.read_network_rules()

                self.start_thread_for_qos(**info, network_rules=network_rules)
                if self.sniffer.is_sniffer_enabled(): self.sniffer.start_thread_for_sniffing(info)

            except Exception as ex:
                logging.error("An error occurred in container listener.",
                              exc_info=True)


                continue



    @classmethod
    def generate_network_distribution(cls, path, name="experimental"):
        """
        This function captures a distribution of network's ping trace and generates its distribution file.
        With that distribution file, tc tool can apply specific network distribution on delay function
        :param path: The path that the documents will be saved
        :param name: The name of the distribution
        :return: The distribution context of the ping trace file
        """
        init_path = os.path.join(path, "rttdata.txt")
        fin_path = os.path.join(path, "rttdata2.txt")
        current_path = os.path.dirname(os.path.abspath(__file__))
        dist_path = os.path.join(path, name + ".dist")
        subprocess.check_output(['/bin/sh', '-c', "cat %s | grep icmp_seq | cut -d'=' -f4 | cut -d' ' -f1 >  %s" % (init_path, fin_path) ])
        subprocess.check_output(['/bin/sh', '-c',"%s/network_scripts/maketable %s > %s" % ( current_path, fin_path,dist_path )])
        res = subprocess.check_output(['/bin/sh', '-c', "%s/network_scripts/stats %s" % (current_path, fin_path)]).decode("utf-8")
        return res

    @classmethod
    def inject_network_distribution(cls, trace_file):
        """
        Saves the distribution to the right folder of the tc tool
        """
        return subprocess.check_output(['/bin/sh', '-c', "cp %s /usr/lib/tc" % trace_file])

    def read_network_rules(self):
        """
        Reads the network rules file and returns a dictionary with the rules
        """
        f = open(os.path.join(self.connector.path, "network.yaml"), "r")
        infra = yaml.load(f, Loader=yaml.UnsafeLoader)
        f.close()
        return infra

    @classmethod
    def apply_network_rule(cls, adapter, ifb_interface , in_rule, out_rule, create="TRUE"):
        """
        Executes the 'apply_rule.sh' script in order to inject the right network characteristics to the specific
        emulated nodes.
        :param adapter: The specific adapter of a network
        :param ifb_interface: The id of the virtual adapter that the system will create
        :param in_rule: The ingress NetEm rule
        :param out_rule: The egress NetEm rule
        :param create: If true, it is the first time that the Fogify applies rules in this emulated node
        """
        subprocess.run(
            [os.path.dirname(os.path.abspath(__file__)) + '/apply_rule.sh', adapter, in_rule, out_rule, ifb_interface,
             str(create).lower()]
        )
