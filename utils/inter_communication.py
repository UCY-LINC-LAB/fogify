import logging
import os
import socket
import requests
from connectors.base import BasicConnector
from enum import Enum

class Communicator(object):
    """
    This class encapsulates all necessary API calls that are need to be performed between the Fogify Controller and
    the Fogify Agents.
    """

    class URLs(Enum):
        agent_action = 'http://%s:5500/actions/'
        agent_topology = 'http://%s:5500/topology/'
        controller_link_updates = 'http://%s:5000/control/%s/'
        agent_packet = 'http://%s:5500/packets/'
        agent_metrics = 'http://%s:5500/monitorings/'
        agent_distribution = 'http://%s:5500/generate-network-distribution/%s/'

    def __init__(self, connector: BasicConnector = None):
        self.connector = connector

    def __instance_ids(self, instance_id: str = None, instance_type: str = None):

        docker_instances = self.connector.get_all_instances()

        if instance_id in docker_instances:
            return {docker_instances[instance_id]: [instance_id]}

        if instance_type:
            instances = {}
            for node, docker_instances in docker_instances.items():
                for docker_instance in docker_instances:
                    if docker_instance.find(instance_type) < 0: continue
                    if node not in instances: instances[node] = []
                    instances[node] += [docker_instance]
            return instances
        return {}

    def agents__perform_action(self, commands: dict = {}, instance_id: str = None, instance_type: str = None, **kwargs):

        selected_instances = self.__instance_ids(instance_id, instance_type)
        res = {}
        for i in selected_instances:
            res.update(
                requests.post(

                    self.URLs.agent_action.value % socket.gethostbyname(i), json={
                        'instances': selected_instances[i],
                        'commands': commands
                    }, headers={'Content-Type': "application/json"}
                ).json()
            )
        return res

    def agents__forward_network_file(self, network_file):
        nodes = self.connector.get_nodes()
        res = {}
        for i in nodes:
            res.update({nodes[i]: requests.post(self.URLs.agent_topology.value % nodes[i],
                              files={'file': network_file}).json()})
        return res

    def agents__get_metrics(self, query: str = None)->list:
        return self.agents__get(self.URLs.agent_metrics, query)

    def agents__get_packets(self, query: str = None)->list:
        return self.agents__get(self.URLs.agent_packet.value, query)

    def agents__delete_metrics(self):
        return self.agents__delete(self.URLs.agent_metrics.value, "metrics")

    def agents__delete_packets(self):
        return self.agents__delete(self.URLs.agent_packet.value, "packets")

    def agents__delete(self, url: URLs, action_type: str):
        nodes = self.connector.get_nodes()
        res = {}
        for i in nodes:
            try:
                r = requests.delete(url % nodes[i]).json()
                res.update(r)
            except ConnectionError as e:
                logging.error( 'The agent of node %s is offline'%i, exc_info=True)
        return {"message": "The %s are empty now"%action_type}

    def agents__get(self, url: URLs, query: str):
        nodes = self.connector.get_nodes()
        res = {}
        str_url = url.value
        for i in nodes:
            try:
                str_url = str_url % nodes[i]
                str_url = str_url + "?" + query if query != "" else str_url
                r = requests.get(str_url).json()
                res.update(r)
            except ConnectionError as e:
                logging.error( 'The agent of node %s is offline'%i, exc_info=True)
        return res

    def agents__disseminate_net_distribution(self, name: str, file) -> dict:

        nodes = self.connector.get_nodes()
        res = {}
        for i in nodes:
            requests.post(self.URLs.agent_distribution.value % (nodes[i], name),
                              files={'file': file})

        return {"generated-distribution": res}

    def controller__link_updates(self, update_for_services_needed=None):
        if not update_for_services_needed: return
        str_set = "|".join(update_for_services_needed)
        action_url = self.URLs.controller_link_updates.value % (
            os.environ['CONTROLLER_IP'] if 'CONTROLLER_IP' in os.environ else '0.0.0.0', str_set)
        requests.post(action_url, headers={'Content-Type': "application/json"})

