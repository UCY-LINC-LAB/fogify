import logging
import os
import subprocess

from nsenter import Namespace


class ContainerNetworkNamespaceException(Exception): pass


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
        except Exception:
            logging.error("The system did not return the container's pid.", exc_info=True)

    @staticmethod
    def evaluate_pid(pid):
        if pid.startswith("State"): raise ContainerNetworkNamespaceException(
            "Failure due to the state of the container", pid)
        if not str(pid).isnumeric(): raise ContainerNetworkNamespaceException(
            "The container id is fault: %s" % str(pid))
        if not str(pid) != "0": raise ContainerNetworkNamespaceException("The container id is fault: %s" % str(pid))


def get_ip_from_network_object(network: dict):
    ip_address = network.get('IPAMConfig', {})
    ip = ip_address.get('IPv4Address') if ip_address is not None else None
    if ip_address is not None and ip is not None:
        return ip
    return network.get('IPAddress', {})

def get_container_ip_property(property):
    eth = subprocess.check_output(['/bin/sh', '-c', 'ip a | grep %s | tail -n 1' % property]).decode().replace("\n", "")
    return eth
