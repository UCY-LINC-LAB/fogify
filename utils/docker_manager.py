import json
import os
import subprocess
from nsenter import Namespace
from connectors.DockerBasedConnectors import CommonDockerSuperclass

class ContainerNetworkNamespace(Namespace):

    def __init__(self, container_id):
        proc = os.environ["NAMESPACE_PATH"] if "NAMESPACE_PATH" in os.environ else "/proc/"
        pid_res = self.get_pid_from_container(container_id)
        pid = pid_res.split(" ")[-1]
        if str(pid).isnumeric() and str(pid) != "0":
            Namespace.__init__(self, proc + "/" + str(pid) + "/ns/net", 'net')
        else:
            raise Exception("The container id is fault: %s" % str(pid_res))

    def get_pid_from_container(self, container_id):
        try:
            res = subprocess.getoutput(
                "docker inspect %s --format '{{.State.Pid}}' " % container_id)

            if res.split(" ")[-1].startswith("State"): raise Exception("Failure due to the state of the container", res)
            return res
        except Exception as ex:
            print(ex)



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
        print("get_containers_adapter_for_network", ex)




