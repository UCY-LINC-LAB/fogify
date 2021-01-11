import datetime
import os
import sys
import time
from enum import Enum

import requests
import yaml

if sys.version_info[0] < 3:
    pass
else:
    pass

import pandas as pd


class ExceptionFogifySDK(Exception):
    pass


class FogifySDK(object):

    def __init__(self, url: str, docker_compose: str = None):
        self.url = url

        self.docker_compose = None
        self.nodes = []
        self.networks = []
        self.topology = []
        self.services = []
        self.docker_swarm_rep = None

        if docker_compose:
            try:
                file = open(docker_compose, "r")
                self.docker_compose = file.read()
                file.close()
                self.parse_docker_swarm()
            except FileNotFoundError:
                raise ExceptionFogifySDK("No such file or directory: " + docker_compose)

    class Action_type(Enum):
        HORIZONTAL_SCALING = 'HORIZONTAL_SCALING'
        VERTICAL_SCALING = 'VERTICAL_SCALING'
        NETWORK = 'NETWORK'
        STRESS = 'STRESS'
        COMMAND = "COMMAND"

    def get_url(self, path: str = ""):
        if not self.url.startswith("http://"):
            return "https://%s" % (self.url + path)
        return self.url + path

    def check_docker_swarm_existence(self):
        if self.docker_compose is None:
            raise ExceptionFogifySDK('You can not apply this functionality with fogify yaml')

    def parse_docker_swarm(self):
        self.check_docker_swarm_existence()
        self.docker_swarm_rep = yaml.safe_load(self.docker_compose)

        if 'services' not in self.docker_swarm_rep:
            raise ExceptionFogifySDK("The docker-compose should have at least services")

        if 'x-fogify' in self.docker_swarm_rep:
            if self.docker_swarm_rep['x-fogify']:
                self.networks = self.docker_swarm_rep['x-fogify']['networks'] if 'networks' in self.docker_swarm_rep[
                    'x-fogify'] else []
                self.nodes = self.docker_swarm_rep['x-fogify']['nodes'] if 'nodes' in self.docker_swarm_rep[
                    'x-fogify'] else []
                self.scenarios = self.docker_swarm_rep['x-fogify']['scenarios'] if 'scenarios' in self.docker_swarm_rep[
                    'x-fogify'] else []
                self.topology = self.docker_swarm_rep['x-fogify']['topology'] if 'topology' in self.docker_swarm_rep[
                    'x-fogify'] else []
        self.services = [i for i in self.docker_swarm_rep["services"]]

    def upload_file(self, remove_file: bool = True):
        if self.docker_compose:
            self.docker_swarm_rep["x-fogify"] = {
                "networks": self.networks if hasattr(self, 'networks') else [],
                "topology": self.topology if hasattr(self, 'topology') else [],
                "nodes": self.nodes if hasattr(self, 'nodes') else [],
                "scenarios": self.scenarios if hasattr(self, 'scenarios') else []
            }
            f = open("fogified-docker-compose.yaml", "w")
            f.write(yaml.dump(self.docker_swarm_rep))
            f.close()
            self.fogify_yaml = open("fogified-docker-compose.yaml", "rb")
            if remove_file:
                os.remove("fogified-docker-compose.yaml")
        return self.fogify_yaml

    def __del__(self):
        if hasattr(self, 'fogify_yaml') and self.fogify_yaml:
            self.fogify_yaml.close()
        del self

    def deploy(self, timeout: int = 120):
        url = self.get_url("/topology/")
        self.clean_metrics()
        self.clean_annotations()
        response = requests.post(url, files={"file": self.upload_file()}, headers={}).json()

        if not ('message' in response and response['message'].upper() == "OK"):
            raise ExceptionFogifySDK("The deployment is failed")

        service_count = {name: response['swarm']['services'][name]['deploy']['replicas'] for name in
                         response['swarm']['services']}

        from tqdm import tqdm
        total = sum([int(service_count[i]) for i in service_count])
        pbar = tqdm(total=total, desc="Deploy process")
        count = 0
        current_iteration = 0
        while (count < total and current_iteration < timeout):
            time.sleep(5)
            response = requests.get(url, headers={}).json()
            new_count = 0
            for i in response:
                new_count += len(response[i])
            dif = new_count - count
            pbar.update(dif)
            count = new_count
            current_iteration += 5

        pbar.close()
        if current_iteration > timeout:
            self.undeploy()
            raise ExceptionFogifySDK("The deployment is failed")

        return {
            "message": "The services are deployed ( %s )" % str(service_count)
        }

    def undeploy(self, timeout: int = 120):
        url = self.get_url("/topology/")
        print(url)
        response = requests.delete(url)
        if response.status_code != 200:
            raise ExceptionFogifySDK("Server error ( %s )" % str(response.json()))
        response = requests.get(url, headers={}).json()
        total = 0
        for i in response:
            total += len(response[i])

        from tqdm import tqdm
        pbar = tqdm(total=total, desc="Undeploy process")
        count = total
        current_iteration = 0
        while (count > 0 and current_iteration < timeout):
            time.sleep(5)
            response = requests.get(url, headers={}).json()
            new_count = 0
            for i in response:
                new_count += len(response[i])
            dif = count - new_count
            pbar.update(dif)
            count = new_count
            current_iteration += 5
        self.data = {}
        pbar.close()
        if current_iteration > timeout:
            raise ExceptionFogifySDK("The undeployment is failed")

        return {
            "message": "The %s services are undeployed" % str(total)
        }

    def get_metrics(self, service: str = None, from_timestamp: str = None, to_timestamp: str = None):
        query = ""
        query += "from_timestamp=" + str(
            int(datetime.datetime.timestamp(from_timestamp))) + "&" if from_timestamp else ""
        query += "to_timestamp=" + str(int(datetime.datetime.timestamp(to_timestamp))) + "&" if to_timestamp else ""
        query += "service=" + service if service else ""
        if hasattr(self, 'data') and service in self.data:
            resp = requests.get(self.get_url("/monitorings/") + "?" + query).json()

            if service in resp:
                resp[service].sort(key=lambda k: k['count'])
                intervals = [i['count'] for i in self.data[service]]
                for i in resp[service]:
                    if i['count'] not in intervals:
                        self.data[service].append(i)
        else:
            self.data = requests.get(self.get_url("/monitorings/") + "?" + query).json()
            for i in self.data:
                self.data[i].sort(key=lambda k: k['count'])
        return self

    def get_network_packets_from(self, service: str, from_timestamp: str = None, to_timestamp: str = None,
                                 packet_type: str = None):

        query = ""
        query += "from_timestamp=" + str(
            int(datetime.datetime.timestamp(from_timestamp))) + "&" if from_timestamp else ""
        query += "to_timestamp=" + str(int(datetime.datetime.timestamp(to_timestamp))) + "&" if to_timestamp else ""
        query += "packet_type=" + str(packet_type) + "&" if packet_type else ""
        query += "service=" + service
        data = requests.get(self.get_url("/packets/") + "?" + query).json()
        if "res" not in data:
            raise ExceptionFogifySDK("The API call for packets does not response readable object")
        res = pd.DataFrame.from_records(data["res"])

        return res

    def get_metrics_from(self, service: str):
        if hasattr(self, 'data') and service in self.data:
            self.get_metrics(service=service,
                             from_timestamp=datetime.datetime.strptime(self.data[service][-1]['timestamp'],
                                                                       "%a, %d %b %Y %H:%M:%S %Z") - datetime.timedelta(
                                 milliseconds=100))
        else:
            self.get_metrics()
        res = pd.DataFrame.from_records(self.data[service])
        res.timestamp = pd.to_datetime(res['timestamp']).dt.tz_localize(None)
        res.set_index('timestamp', inplace=True)
        return res

    def clean_metrics(self):
        if hasattr(self, 'data'):
            del self.data
        return requests.delete(self.get_url("/monitorings/")).json()

    def horizontal_scaling_up(self, instance_type: str, num_of_instances: int = 1):
        return self.action(
            FogifySDK.Action_type.HORIZONTAL_SCALING.value,
            instance_type=instance_type,
            instances=num_of_instances,
            type="up"
        )

    def horizontal_scaling_down(self, instance_type: str, num_of_instances: int = 1):
        return self.action(
            FogifySDK.Action_type.HORIZONTAL_SCALING.value,
            instance_type=instance_type,
            instances=num_of_instances,
            type="down"
        )

    def vertical_scaling(self, instance_type: str, num_of_instances: int = 1, cpu: str = None, memory: str = None):
        if cpu and memory:
            raise ExceptionFogifySDK("You can not scale-up both cpu and memory at once.")
        if cpu is None and memory is None:
            raise ExceptionFogifySDK("You did not select neither cpu nor memory for vertical scaling.")
        if cpu:
            if type(cpu) != str:
                raise ExceptionFogifySDK("cpu parameter should be string")
            if cpu[0] not in ['-', '+']:
                raise ExceptionFogifySDK("Select +/- to increase or decrease the cpu processing power")
            try:
                int(cpu[1:])
            except Exception:
                raise ExceptionFogifySDK("The percent should be numeric")
            params = {'action': 'cpu', 'value': cpu}
        if memory:
            params = {'action': 'memory', 'value': memory}
        return self.action(
            FogifySDK.Action_type.VERTICAL_SCALING.value,
            instance_type=instance_type,
            instances=num_of_instances,
            **params
        )

    def update_network(self, instance_type: str, network: str, network_characteristics: dict = {},
                       num_of_instances: int = 1):
        network_characteristics['network'] = network
        return self.action(
            FogifySDK.Action_type.NETWORK.value,
            instance_type=instance_type,
            instances=num_of_instances,
            action=network_characteristics
        )

    def stress(self, instance_type: str, duration: int = 60, num_of_instances: int = 1, cpu=None, io=None, vm=None,
               vm_bytes=None):
        if all(v is None for v in [cpu, io, vm, vm_bytes]):
            raise ExceptionFogifySDK("You can not set all stress parameters as None")
        res = {}
        if cpu:
            res['cpu'] = cpu
        if io:
            res['io'] = io
        if vm:
            res['vm'] = vm
        if vm_bytes:
            res['vm_bytes'] = vm_bytes
        return self.action(
            FogifySDK.Action_type.STRESS.value,
            instance_type=instance_type,
            instances=num_of_instances,
            action=dict(
                duration=duration,
                **res
            )
        )

    def command(self, instance_type: str, command: str, num_of_instances: int = 1):
        res = {}
        res['command'] = command
        return self.action(
            FogifySDK.Action_type.COMMAND.value,
            instance_type=instance_type,
            instances=num_of_instances,
            action=dict(
                **res
            )
        )

    def action(self, action_type: Action_type, **kwargs):
        headers = {'Content-Type': 'application/json; charset=utf-8'}
        action_type_to_url = {
            self.Action_type.HORIZONTAL_SCALING.value: "/actions/horizontal_scaling/",
            self.Action_type.VERTICAL_SCALING.value: "/actions/vertical_scaling/",
            self.Action_type.NETWORK.value: "/actions/network/",
            self.Action_type.STRESS.value: "/actions/stress/",
            self.Action_type.COMMAND.value: "/actions/command/"
        }
        if action_type not in [e.value for e in FogifySDK.Action_type]:
            raise ExceptionFogifySDK("The action type %s is not defined." % action_type)
        res = requests.request("POST",
                               self.get_url(action_type_to_url[action_type]),
                               json={"params": kwargs}, headers=headers
                               ).json()
        if "message" in res and res["message"].upper() == "OK":
            return res
        else:
            raise ExceptionFogifySDK("The API did not return proper response for that action (%S)" % str(res))

    def scenario_execution(self,
                           name: str = None,
                           remove_previous_metrics: bool = True):
        print("Scenario execution process: ")
        from tqdm import tqdm
        if remove_previous_metrics:
            self.clean_metrics()

        if len(self.scenarios) == 0:
            raise ExceptionFogifySDK("There is no scenarios")
        if name is None:
            selected_scenarios = self.scenarios[0]
        else:
            for i in self.scenarios:
                if i['name'] == name:
                    selected_scenarios = i
                    break
        selected_scenarios['actions'] = sorted(selected_scenarios['actions'], key=lambda x: x['position'])

        pbar = tqdm(total=sum([int(i['time']) for i in selected_scenarios['actions']]))
        start = datetime.datetime.now()
        for i in selected_scenarios['actions']:
            for j in range(i['time']):
                time.sleep(1)
                pbar.update(1)
            try:
                action = i['action'] if 'action' in i else {}
                type_action = action['type'] if 'type' in action else ""
                params = action['parameters'] if 'parameters' in action else {}
                params['instance_type'] = i['instance_type'] if 'instance_type' in i else ""
                params['instances'] = i['instances'] if 'instances' in i else ""
                if action != "NOOP":
                    self.action(type_action.upper(), **params)
                print("The action %s is executed." % type_action)
            except Exception as e:
                print("There was a problem at the scenario execution process %s" % e)
                print("The input data is %s" % action)
        pbar.close()
        print("Scenario is finished")
        stop = datetime.datetime.now()
        if remove_previous_metrics:
            self.get_metrics()
        return start, stop

    def add_node(self, name: str, cpu_cores: int, cpu_freq: int, memory: str, disk=""):
        self.check_docker_swarm_existence()
        for i in self.nodes:
            if i['name'] == name:
                raise ExceptionFogifySDK("The device already exists")
        self.nodes.append(
            dict(
                name=name,
                capabilities=dict(
                    processor=dict(
                        cores=int(cpu_cores),
                        clock_speed=int(cpu_freq)),
                    memory=memory,
                    disk=disk
                )
            )
        )

    def add_network(self, name: str, uplink: dict, downlink: dict, capacity: int = None):
        self.check_docker_swarm_existence()
        for i in self.networks:
            if i['name'] == name:
                raise ExceptionFogifySDK("The network already exists")
        self.networks.append(
            dict(
                name=name,
                uplink=uplink,
                downlink=downlink,
                capacity=capacity
            )
        )

    def add_bidirectional_network(self, name: str, bidirectional: dict, capacity: int = None):
        self.check_docker_swarm_existence()
        for i in self.networks:
            if i['name'] == name:
                raise ExceptionFogifySDK("The network already exists")
        self.networks.append(
            dict(
                name=name,
                bidirectional=bidirectional,
                capacity=capacity
            )
        )

    def add_link(self, network_name: str, from_node: str, to_node: str, properties: dict, bidirectional: bool = True):
        self.check_docker_swarm_existence()
        exists = False
        for i in self.networks:
            if network_name == i["name"]:
                exists = True
                break
        if not exists:
            raise ExceptionFogifySDK("The network does not exist")

        links = i['links'] if 'links' in i else []
        links.append({
            "from_node": from_node,
            "to_node": to_node,
            "bidirectional": bidirectional,
            "properties": properties
        })

        i['links'] = links
        res = []
        for j in self.networks:
            if network_name == j["name"]:
                res.append(i)
            else:
                res.append(j)
        self.networks = res

    def add_topology_node(self, label: str, service: str, device: str, networks: list = [], replicas: int = 1):
        self.check_docker_swarm_existence()
        if service not in self.services:
            raise ExceptionFogifySDK('There is no service with name %s in swarm file.' % service)

        if label in [i['label'] for i in self.topology]:
            raise ExceptionFogifySDK('There is another topology node with %s in your model.' % label)

        if device not in [i['name'] for i in self.nodes]:
            raise ExceptionFogifySDK('There is no device with name %s in your model.' % device)

        for network in networks:
            if network not in [i['name'] for i in self.networks]:
                raise ExceptionFogifySDK('There is no network with name %s in your model.' % network)

        if label in [i['label'] for i in self.topology]:
            raise ExceptionFogifySDK('There is another topology node with %s in your model.' % label)

        self.topology.append(
            dict(
                service=service,
                node=device,
                networks=networks,
                label=label,
                replicas=replicas
            )
        )

    def plot(self, ax, service: str = None, metric: str = None, func=None, label: str = None, duration: dict = {},
             style: dict = {}):

        df = self.get_metrics_from(service)
        df.timestamp = pd.to_datetime(df['timestamp'])
        if 'from' in duration:
            df = df[df.timestamp >= duration['from']]
        if 'to' in duration:
            df = df[df.timestamp <= duration['to']]
        metric_line = df.set_index('timestamp')[metric]
        if func == 'diff':
            metric_line = metric_line.diff()
        metric_line.plot(ax=ax, x='timestamp', label=label, **style)
        return self

    def plot_annotations(self, ax, start=None, stop=None, label: str = 'annotation', colors_gist: str = 'gist_yarg',
                         linestyle: str = '--'):
        import matplotlib.pyplot as plt
        ad = self.get_annotations().annotations
        ad.timestamp = pd.to_datetime(ad['timestamp']).dt.tz_localize(None)
        if start:
            ad = ad[ad.timestamp >= start]
        if stop:
            ad = ad[ad.timestamp <= stop]
        dates = ad.timestamp
        N = len(ad['annotation'])

        if type(colors_gist) == list:
            colors = colors_gist
        else:
            cmap = plt.cm.get_cmap(colors_gist, N)
            colors = [cmap(i) for i in range(N)]
        for xc, c, annot in zip(dates, colors, ad[label]):
            ax.axvline(x=xc, color=c, label=annot, linestyle=linestyle)
        return self

    def info(self):
        url = self.get_url("/topology/")
        return requests.get(url, headers={}).json()

    def clean_annotations(self):
        return requests.delete(self.get_url("/annotations/")).json()

    def get_annotations(self):
        data = requests.get(self.get_url("/annotations/")).json()
        self.annotations = pd.DataFrame.from_records(data)
        return self
