import copy
import json
import logging
import os
import subprocess
import time

import docker
import iptc
import yaml
from iptc import IPTCError

from connectors import BasicConnector
from utils import Cache
from utils.docker_manager import ContainerNetworkNamespace, \
    get_ip_from_network_object, get_container_ip_property
from utils.inter_communication import Communicator
from utils.sniffer import SnifferHandler
from utils.units import RateUnit

SH = "/bin/sh"


class NetworkController:
    """
    This class applies the network QoS to the container's
    interfaces and starts the sniffer (if sniffer is enabled)
    Specifically, a subprocess observes the docker socket
    and if a new fogify container starts,
    the processes of this class ensure that both network
    QoS will be applied and the packet monitoring.
    """
    __cached_rules = None

    def __init__(self, connector: BasicConnector, sniffer: SnifferHandler = SnifferHandler()):
        self.connector = connector
        self.sniffer = sniffer

    def save_network_rules(self, data):
        """
        This function is responsible to save the network rules to a specific path.
        Since the network rules can be either
        a file(from deploy API) or a dictionary(from action API),
        the method performs a different process based on data type
        :param data: Network Rules in a dictionary form or in a file object
        :return: None
        """
        path = self.connector.path
        file_name = "network.yaml"
        if not os.path.exists(path): os.mkdir(path)
        print(data)
        if type(data) == dict:
            yaml.dump(data, open(os.path.join(path, file_name), 'w'), default_flow_style=False)
            return
        data.save(os.path.join(path, file_name))
        self.__class__.__cached_rules = None

    def apply_net_qos(self, service_name: str, container_id: str, network_rules: dict, inform_controller=True):
        clear_name = service_name.replace("fogify_", "")
        network_rules = network_rules[clear_name]
        self.execute_network_commands(clear_name, container_id, network_rules)
        if inform_controller:
            self.communicate_with_controller(network_rules)

    def execute_network_commands(self, service_name: str, container_id: str, network_rules: dict):
        with ContainerNetworkNamespace(container_id):
            for network, rules in network_rules.items():
                eth, ifb = NetworkController.get_adapters(container_id, network)  # TODO FIX PERFORMANCE
                # apply general network QoS
                downlink_rules, uplink_rules = rules['downlink'].replace("  ", " "), rules['uplink'].replace("  ", " ")
                NetworkController.apply_general_network_rules(eth, ifb, uplink_rules, downlink_rules)
                # apply link QoS between the containers
                ips_to_rules = self.ips_to_link_rules(service_name, network, rules)  # TODO FIX PERFORMANCE

                commands = self.get_link_commands(eth, 'ifb' + ifb, ips_to_rules)

                subprocess.Popen(SH, stdin=subprocess.PIPE).communicate(commands.encode())
                is_packet_monitoring_enabled = str(rules.get('packet_level_monitoring', 'false')).lower() == 'true'

                self.apply_firewall_rules(eth, network, rules.get('firewall_rules'))

                print("rules", rules)
                print("packet_monitoring", is_packet_monitoring_enabled)
                if is_packet_monitoring_enabled:
                    self.sniffer.start_thread_for_sniffing(container_id, service_name, eth, network)

    def apply_firewall_rules(self, interface, network, rules=[]):
        try:
            chain = iptc.Chain(iptc.Table(iptc.Table.FILTER), "INPUT")
            chain.delete()
        except IPTCError: pass
        pos = 0
        chain = iptc.Chain(iptc.Table(iptc.Table.FILTER), "INPUT")
        for rule in rules:
            iptc_rule = self.__generate_iptc_rule(interface, network, rule)
            chain.insert_rule(iptc_rule, pos)
            pos += 1

    def __generate_iptc_rule(self, interface, network, rule):
        iptc_rule = iptc.Rule()
        iptc_rule.in_interface = interface
        protocol = rule.get('protocol')
        dport = rule.get('to_port')
        sport = rule.get('from_port')
        from_ = rule.get('from')
        to_ = rule.get('to')
        type_ = rule.get('type')
        if protocol: iptc_rule.protocol = protocol
        if dport: iptc_rule.dport = dport
        if sport: iptc_rule.sport = sport
        if from_:
            to_node_ips = self.get_ips_for_service(from_)
            if network in to_node_ips:
                iptc_rule.src = ",".join(to_node_ips.get(network))
        if to_:
            to_node_ips = self.get_ips_for_service(to_)
            if network in to_node_ips:
                iptc_rule.dst = ",".join(to_node_ips.get(network))
        iptc_rule.target = iptc.Target(iptc_rule, getattr(iptc.Policy, type_.upper()) if type_ else iptc.Policy.ACCEPT)
        return iptc_rule

    @staticmethod
    def get_containers_adapter_for_network(container_id, network):
        try:
            networks = json.loads(
                subprocess.getoutput("docker inspect --format='{{json .NetworkSettings.Networks}}' %s" % container_id))
            ip = None
            if network in networks:
                ip = get_ip_from_network_object(networks[network])

            eth = get_container_ip_property(ip)
            return eth.split(" ")[-1] if eth else None
        except Exception:
            logging.error("The system does not return the adapter of the container/network pair (%s,%s)." % (
            container_id, network), exc_info=True)

    @staticmethod
    @Cache.memoize
    def get_adapters(container_id, network):
        """
        This method return the container's adapter for a specific network
        along with the identifier of the Fogify's egress virtual adapter.
        :param network: Network name
        :param container_id: Container's id
        :return: "adapter" the adapter of the container, "ifb_interface" the egress identifier
        """

        shorten_container_id = container_id[:10]
        adapter = None
        count = 0
        while (adapter is None and count < 3):
            adapter = NetworkController.get_containers_adapter_for_network(container_id, network)
            time.sleep(1)
            count += 1
        if not adapter: return None, None
        ifb_interface = shorten_container_id + adapter[-1]
        return adapter, ifb_interface

    def communicate_with_controller(self, network_rules):
        """
        This method notifies the controller about the
        updates that will be needed due to a new container
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

    def get_link_commands(self, interface, ifb_interface, ips_to_rule):
        """
        Performs network QoS links to the specific instances
        :param interface: ingress (initial) interface of the container
        :param ifb_interface: egress virtual interface
        :param ips_to_rule: specific rules for this interface
        :return: None
        """
        commands = " "
        for ip, rule in ips_to_rule.items():
            commands += self.generate_string_link_rule(ifb_interface, ip, rule["downlink"], "downlink")
            commands += self.generate_string_link_rule(interface, ip, rule["uplink"], "uplink")
        return commands

    @classmethod
    def generate_string_link_rule(cls, eth, ip, rule, _type):
        _type = 1 if _type == "downlink" else 2  # we change the id of the rule based on direction
        rule_id = cls.rule_id_from_ip(ip)
        rate, rule = cls.get_rate(rule)
        res = 'tc class add dev %s parent %s: classid %s:%s htb rate %s' % (eth, _type, _type, rule_id, rate) + " \n"
        res += 'tc qdisc add dev %s parent %s:%s handle %s: netem %s ' % (eth, _type, rule_id, rule_id, rule) + " \n"
        if _type == 2:  # Downlink
            res += "tc filter add dev %s parent %s: protocol ip prio 1 u32 match ip dst %s match ip src 0.0.0.0/0 flowid %s:%s " % (
            eth, _type, ip, _type, rule_id) + " \n"
        if _type == 1:  # uplink
            res += "tc filter add dev %s parent %s: protocol ip prio 1 u32 match ip src %s match ip dst 0.0.0.0/0 flowid %s:%s " % (
            eth, _type, ip, _type, rule_id) + " \n"
        return res

    @classmethod
    def rule_id_from_ip(cls, ip):
        rule_id = ip.split(".")[-1]
        rule_id = int(rule_id) + 11
        return rule_id

    def ips_to_link_rules(self, service_name, network, rules):
        from_service = service_name.replace("fogify_", "")
        res = {}
        rules_for_network = rules
        if not 'links' in rules_for_network: return {}

        for link in rules_for_network['links']:
            if link['from_node'] != from_service: continue
            if not 'to_node' in link: continue
            to_node_ips = self.get_ips_for_service(link['to_node'])
            if network not in to_node_ips: continue
            for ip in to_node_ips[network]:
                res[ip] = link['command']
        return res

    def get_ips_for_service(self, service):
        key = "get_ips_for_service:%s" % service
        res = Cache.get(key)
        if res: return res
        res = self.connector.get_ips_for_service(service)
        Cache.put(key, res)
        return res

    @staticmethod
    def check_starting_condition(event):
        """
        Evaluates if the event docker socket is a starting container event
        :param event: The docker socket event
        :return: True or False based on the rule
        """
        started = event.get('status') == 'start'
        is_container = event.get('Type') == 'container'
        emulation_is_running = os.getenv('EMULATION_IS_RUNNING') == 'TRUE'
        return started and is_container and emulation_is_running

    def start_thread_for_qos(self, service_name, container_id, network_rules, inform_controller=True, **kwargs):
        """
        This function starts a new thread in order to apply the network QoS on a specific emulated instance
        """
        self.apply_net_qos(service_name, container_id, network_rules, inform_controller)

    def listen(self):
        """
        The long-running method for observing the events of docker socket
        and applying both network QoS and sniffer on new created containers.
        :return: None
        """
        connector = self.connector

        self.sniffer.start_thread_for_sniffing_storage()

        client = docker.from_env()
        for event in client.events(decode=True):
            try:
                if not self.check_starting_condition(event):
                    continue
                info = connector.event_attr_to_information(event)
                network_rules = self.read_network_rules
                self.apply_network_qos_for_event(info, network_rules)

            except Exception:
                logging.error("An error occurred in container listener.", exc_info=True)
                continue

    def apply_network_qos_for_event(self, info, network_rules, inform_controller=True):
        if info['service_name'] and info['container_id'] and info['container_name']:
            self.start_thread_for_qos(**info, network_rules=network_rules, inform_controller=inform_controller)

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
        subprocess.check_output(
            [SH, '-c', "cat %s | grep icmp_seq | cut -d'=' -f4 | cut -d' ' -f1 >  %s" % (init_path, fin_path)])
        subprocess.check_output(
            [SH, '-c', "%s/network_scripts/maketable %s > %s" % (current_path, fin_path, dist_path)])
        res = subprocess.check_output([SH, '-c', "%s/network_scripts/stats %s" % (current_path, fin_path)]).decode(
            "utf-8")
        return res

    @classmethod
    def inject_network_distribution(cls, trace_file):
        """
        Saves the distribution to the right folder of the tc tool
        """
        return subprocess.check_output([SH, '-c', "cp %s /usr/lib/tc" % trace_file])

    @property
    def read_network_rules(self):
        """
        Reads the network rules file and returns a dictionary with the rules
        """
        if self.__class__.__cached_rules: return copy.deepcopy(self.__class__.__cached_rules)
        f = open(os.path.join(self.connector.path, "network.yaml"), "r")
        infra = yaml.load(f, Loader=yaml.UnsafeLoader)
        f.close()
        self.__class__.__cached_rules = infra
        return infra

    @classmethod
    def apply_general_network_rules(cls, adapter, ifb_interface, in_rule, out_rule):
        """
        Executes the 'apply_rule.sh' script in order to inject the right network characteristics to the specific
        emulated nodes.
        :param adapter: The specific adapter of a network
        :param ifb_interface: The id of the virtual adapter that the system will create
        :param in_rule: The ingress NetEm rule
        :param out_rule: The egress NetEm rule
        """
        rate_in, in_rule = cls.get_rate(in_rule)
        rate_out, out_rule = cls.get_rate(out_rule)

        subprocess.run(
            [os.path.dirname(os.path.abspath(__file__)) + '/apply_rule.sh', adapter, in_rule, out_rule, ifb_interface,
             rate_in, rate_out]# , stdout=open(os.devnull, 'wb'), stderr=open(os.devnull, 'wb')
            )

    @staticmethod
    def get_rate(in_rule):
        rule_in_values = in_rule.split(" ")
        rate_in = "10000000.0Kbit"
        for i in range(len(rule_in_values)):
            if rule_in_values[i] == 'rate':
                try:
                    rate_in = rule_in_values[i + 1]
                except Exception:
                    pass
        rate_in_lower = rate_in.lower()
        value = 0.0
        for unit in RateUnit.get_values():
            if rate_in_lower.endswith(unit):
                value = rate_in_lower.replace(unit, "")
                try:
                    value = float(value)
                except ValueError:
                    value = 0.0
        in_rule = in_rule.replace('rate ' + rate_in, "")
        if value == 0.0:
            return "1bps", in_rule
        return rate_in, in_rule

    def remove_cached_ips(self):
        Cache.clean_up()