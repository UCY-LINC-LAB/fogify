import copy
import os
import subprocess
import threading
import time
from collections import deque
from utils import docker_manager
import docker
import requests
import yaml
from connectors import get_connector_class
from utils.docker_manager import ContainerNetworkNamespace

from utils.sniffer import Sniffer, SniffingStorage

ConnectorClass = get_connector_class()


def generate_network_distribution(path, name="experimental"):
    subprocess.check_output(['/bin/sh', '-c', "cat %s | grep icmp_seq | cut -d'=' -f4 | cut -d' ' -f1 >  %s" % (
        os.path.join(path, "rttdata.txt"), os.path.join(path, "rttdata2.txt"))])
    subprocess.check_output(['/bin/sh', '-c',
                             os.path.dirname(os.path.abspath(__file__)) + "/network_scripts/maketable %s > %s" % (
                                 os.path.join(path, "rttdata2.txt"), os.path.join(path, name + ".dist"))])
    return subprocess.check_output(['/bin/sh', '-c', os.path.dirname(
        os.path.abspath(__file__)) + "/network_scripts/stats %s" % os.path.join(path, "rttdata2.txt")]).decode("utf-8")


def inject_network_distribution(trace_file):
    return subprocess.check_output(['/bin/sh', '-c', "cp %s /usr/lib/tc" % trace_file])


def apply_network_rule(container, network, in_rule, out_rule, ifb_interface, create="TRUE", _ips={}):
    adapter = None
    count = 0
    while (adapter is None and count < 3):
        adapter = docker_manager.get_containers_adapter_for_network(container, network)
        time.sleep(1)
        count += 1
    if not adapter:
        return
    ifb_interface = ifb_interface + adapter[-1]
    subprocess.run(
        [os.path.dirname(os.path.abspath(__file__)) + '/apply_rule.sh', adapter, in_rule, out_rule, ifb_interface,
         str(create).lower()]
    )

    commands = " "
    counter = 12
    for ip in _ips:
        ips = ip.split("|")
        commands += 'tc class add dev %s parent 1:1 classid 1:%s htb rate 10000mbit' % (
            'ifb' + ifb_interface, str(counter)) + " \n"
        commands += 'tc qdisc add dev %s parent 1:%s handle %s: netem %s ' % (
            'ifb' + ifb_interface, str(counter), str(counter), _ips[ip]) + " \n"

        for ip in ips:
            commands += "tc filter add dev %s protocol ip prio 1 u32 match ip src %s flowid 1:%s " % (
                'ifb' + ifb_interface, ip, str(counter)) + " \n"
        counter += 1
    process = subprocess.Popen('/bin/bash', stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    out, err = process.communicate(commands.encode())


def read_network_rules(path):
    f = open(os.path.join(path, "network.yaml"), "r")
    infra = yaml.load(f, Loader=yaml.UnsafeLoader)
    return infra



def ips_to_rule(service_name, network, network_rules):
    f_name = service_name.replace("fogify_", "")
    res = {}
    if 'links' in network_rules[network] and f_name in network_rules[network]['links']:
        for i in network_rules[network]['links'][f_name]:
            network_ips = {}
            while network not in network_ips:
                network_ips = docker_manager.get_ips_for_service(i)

            res["|".join(network_ips[network])] = network_rules[network]['links'][service_name.replace("fogify_", "")][
                i]
    return res


class NetworkController(object):

    def submition(self, path):
        if 'SNIFFING_ENABLED' in os.environ and os.environ['SNIFFING_ENABLED'].lower() == 'true':
            buffer = deque()
            periodicity = int(os.environ['SNIFFING_PERIODICITY']) if 'SNIFFING_PERIODICITY' in os.environ and \
                                                                     os.environ[
                                                                         'SNIFFING_PERIODICITY'].isnumeric() else None
            storage = SniffingStorage(buffer, periodicity)
            t2 = threading.Thread(target=storage.store_data)
            t2.start()

        client = docker.from_env()
        for event in client.events(decode=True):

            try:
                if getattr(event, 'status', None) == 'start' and \
                        getattr(event, 'Type', None) == 'container':
                    properties = ConnectorClass.event_attr_to_information(event)
                    infra = read_network_rules(path)
                    if properties['service_name'] and properties['container_id'] and properties['container_name']:
                        def apply_net_qos(service_name, container_id, container_name, infra):
                            network_rules = infra[service_name.replace("fogify_", "")]
                            with ContainerNetworkNamespace(container_id):
                                for network in network_rules:
                                    apply_network_rule(container_name,
                                                       network,
                                                       network_rules[network]['downlink'],
                                                       network_rules[network]['uplink'],
                                                       container_id[:10],
                                                       create="TRUE",
                                                       _ips=ips_to_rule(
                                                           service_name, network, network_rules
                                                       ))

                            # update containers for new links
                            update_for_services_needed = set()
                            net_rules = infra[service_name.replace("fogify_", "")]
                            f_name = service_name.replace("fogify_", "")
                            for net in net_rules:
                                for i in net_rules[net]['links']:
                                    for j in net_rules[net]['links'][i]:
                                        if j == f_name:
                                            update_for_services_needed.add(i)
                            str_set = "|".join(update_for_services_needed)
                            action_url = 'http://%s:5000/control/%s/' % (
                                os.environ['CONTROLLER_IP'] if 'CONTROLLER_IP' in os.environ else '0.0.0.0', str_set)
                            requests.post(action_url, headers={'Content-Type': "application/json"})

                        threading.Thread(
                            target=apply_net_qos, args=(
                                properties['service_name'],
                                properties['container_id'],
                                properties['container_name'],
                                copy.deepcopy(infra)
                            )).start()

                        # update network rules to controller
                        def network_sniffing(event):
                            properties = ConnectorClass.event_attr_to_information(event)
                            with ContainerNetworkNamespace(properties['container_id']):
                                sniffer = Sniffer(buffer, properties['container_name'])
                                sniffer.sniff()

                        if 'SNIFFING_ENABLED' in os.environ and os.environ['SNIFFING_ENABLED'].lower() == 'true':
                            threading.Thread(target=network_sniffing, args=(event)).start()
            except Exception as ex:
                print(ex)
                continue
