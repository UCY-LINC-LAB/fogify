import json
import logging
import os
import subprocess
from nsenter import Namespace

class ContainerNetworkNamespace(Namespace):

    def __init__(self, container_id):
        proc = os.environ["NAMESPACE_PATH"] if "NAMESPACE_PATH" in os.environ else "/proc/"
        pid = self.get_pid_from_container(container_id)
        Namespace.__init__(self, proc + "/" + str(pid) + "/ns/net", 'net')

    def get_pid_from_container(self, container_id):
        try:
            res = subprocess.getoutput("docker inspect %s --format '{{.State.Pid}}' " % container_id)
            res = res.split(" ")[-1]
            ContainerNetworkNamespace.evaluate_pid(res)
            return res
        except Exception as ex:
            logging.error("The system did not return the container's pid.", exc_info=True)
    @staticmethod
    def evaluate_pid(pid):
        if pid.startswith("State"): raise Exception("Failure due to the state of the container", pid)
        if not str(pid).isnumeric(): raise Exception("The container id is fault: %s" % str(pid))
        if not str(pid) != "0": raise Exception("The container id is fault: %s" % str(pid))


def get_ip_from_network_object(network: dict):
    if 'IPAMConfig' in network \
            and network['IPAMConfig'] is not None \
            and 'IPv4Address' in network['IPAMConfig']:  # Overlay networks
        ip = network['IPAMConfig']['IPv4Address']
    else:
        ip = network['IPAddress']
    return ip

def get_container_ip_property(property):
    eth = subprocess.check_output( ['/bin/sh', '-c', 'ip a | grep %s | tail -n 1' % property]).decode().replace("\n", "")
    return eth

def get_containers_adapter_for_network(container_id, network):
    try:
        networks = json.loads(
            subprocess.getoutput("docker inspect --format='{{json .NetworkSettings.Networks}}' %s" % container_id))
        ip = None
        if network in networks:

            ip = get_ip_from_network_object(networks[network])

        eth = get_container_ip_property(ip)
        return eth.split(" ")[-1] if eth else None
    except Exception as ex:
        logging.error(
            "The system does not return the adapter of the container/network pair (%s,%s)."% (container_id, network),
                      exc_info=True)




