import os
import socket

import requests
import yaml
from flask import current_app as app
from flask import request
from flask.views import MethodView
from models.base import FogifyModel
from connectors import get_connector_class
from controller.models import Status, Annotation
from models.actions import StressAction, VerticalScalingAction, CommandAction
from models.base import NetworkGenerator, Network
from utils.async_task import AsyncTask
from utils.network import generate_network_distribution

ConnectorClass = get_connector_class()


class AnnotationAPI(MethodView):
    """ Stores and returns the capture action's timestamps for a deployment"""

    def get(self):
        return [annotation.to_dict() for annotation in Annotation.query.all()]

    def delete(self):
        Annotation.query.delete()
        return {"message": "Annotations are clear"}


class TopologyAPI(MethodView):
    """ This class is responsible for topology deployment API calls"""

    def get(self):
        """ Returns the current status of the fogify deployment"""
        return ConnectorClass.return_deployment()

    @ConnectorClass.check_status("running")
    def delete(self):
        """ Remove a Fogify deployment"""
        Status.update_config('submit_delete')
        Annotation.create(Annotation.TYPES.STOP.value)
        connector = ConnectorClass(path=os.getcwd() + app.config['UPLOAD_FOLDER'])
        t = AsyncTask(self, 'remove', [connector])
        t.start()
        return {"message": "The topology is down."}

    @ConnectorClass.check_status("available")
    def post(self):
        """ Introduce a new deployment to the fogify"""

        path = os.getcwd() + app.config['UPLOAD_FOLDER']

        Annotation.create(Annotation.TYPES.START.value)

        if 'file' in request.files:
            file = request.files['file']
            if not os.path.exists(path): os.mkdir(path)
            file.save(os.path.join(path, "docker-compose.yaml"))
        f = open(os.path.join(path, "docker-compose.yaml"), "r")
        infra = yaml.load(f)

        model = FogifyModel(infra)

        connector = ConnectorClass(model,
                                   path=path,
                                   frequency=int(os.environ['CPU_FREQ']) if 'CPU_FREQ' in os.environ else 2400,
                                   cpu_oversubscription=int(os.environ[
                                                                'CPU_OVERSUBSCRIPTION_PERCENTAGE']) if 'CPU_OVERSUBSCRIPTION_PERCENTAGE' in os.environ else 0,
                                   ram_oversubscription=int(os.environ[
                                                                'RAM_OVERSUBSCRIPTION_PERCENTAGE']) if 'RAM_OVERSUBSCRIPTION_PERCENTAGE' in os.environ else 0
                                   )

        controller_response = connector.generate_files()

        networks = NetworkGenerator(model).generate_network_rules()

        yaml.dump(networks, open(path + "fogified-network.yaml", 'w'), default_flow_style=False)

        t = AsyncTask(self, 'submition', [connector, path, model.all_networks])
        t.start()
        return {
            "message": "OK",
            "swarm": controller_response,
            "networks": networks
        }

    def remove(self, connector):
        """ A utility function that destroys a topology """
        connector.down()
        Annotation.create(Annotation.TYPES.UNDEPLOY.value)

    def submition(self, connector, path, networks):
        """ A utility function that deploys a topology """

        nodes = connector.get_nodes()
        # add network rules
        for i in nodes:
            r = requests.post('http://' + nodes[i] + ':5500/topology/',
                              files={'file': open(path + "fogified-network.yaml", 'rb')})

        for network in networks:
            try:
                connector.create_network(network)
            except Exception:
                pass

        # submit the current deployment
        try:
            connector.deploy()
        except Exception as ex:
            print(ex)
            Status.update_config('error')

            return
        Status.update_config('running')
        Annotation.create(Annotation.TYPES.DEPLOY.value)


class MonitoringAPI(MethodView):
    """ This class is responsible for Monitoring API"""

    def delete(self):
        """ Removes the stored monitoring data """
        connector = ConnectorClass()
        nodes = connector.get_nodes()
        res = {}
        for i in nodes:
            try:
                r = requests.delete('http://' + nodes[i] + ':5500/monitorings/').json()
                res.update(r)
            except ConnectionError as e:
                print('The agent of node ' + str(i) + ' is offline')
        return {"message": "The monitorings are empty now"}

    def get(self):
        """ Returns the stored monitoring data """
        try:
            query = ""
            from_timestamp = request.args.get('from_timestamp')
            to_timestamp = request.args.get('to_timestamp')
            service = request.args.get('service')
            query += "from_timestamp=" + from_timestamp + "&" if from_timestamp else ""
            query += "to_timestamp=" + to_timestamp + "&" if to_timestamp else ""
            query += "service=" + service if service else ""
            connector = ConnectorClass()
            nodes = connector.get_nodes()
            res = {}
            for i in nodes:
                try:
                    url = 'http://' + nodes[i] + ':5500/monitorings/'
                    url = url + "?" + query if query != "" else url
                    r = requests.get(url).json()
                    res.update(r)
                except ConnectionError as e:
                    print('The agent of node ' + str(i) + ' is offline')
            return res
        except Exception as e:
            return {
                "Error": "{0}".format(e)
            }


class ActionsAPI(MethodView):
    """ This API class applies the actions to a running topology"""

    def instance_ids(self, params):
        docker_instances = ConnectorClass().get_all_instances()

        if 'instance_id' in params and params['instance_id'] in docker_instances:
            return {docker_instances[params['instance_id']]: [params['instance_id']]}

        if 'instance_type' in params and 'instances' in params:
            instance_type = params['instance_type']
            instances = {}
            for node in docker_instances:
                for i in docker_instances[node]:
                    if i.find(instance_type) >= 0:
                        if node not in instances: instances[node] = []
                        instances[node] += [i]
            return instances
        return {}

    def horizontal_scaling(self, connector,  params):
        instances = int(params['instances'])
        if params['type'] == 'up':
            service_count = int(connector.count_services(params['instance_type'])) + instances
            Annotation.create(Annotation.TYPES.H_SCALE_UP.value, instance_names=params['instance_type'],
                              params="num of instances: " + str(instances))
        else:
            service_count = int(connector.count_services(params['instance_type'])) - instances
            service_count = 0 if service_count < 0 else service_count
            Annotation.create(Annotation.TYPES.H_SCALE_DOWN.value, instance_names=params['instance_type'],
                              params="num of instances: " + str(instances))
        connector.scale(params['instance_type'], service_count)

    def vertical_scaling(self, params):
        vaction = VerticalScalingAction(**params['action'])
        Annotation.create(Annotation.TYPES.V_SCALE.value, instance_names=params['action']['instance_type'],
                          params="parameters: " + vaction.get_command() + "=>" + vaction.get_value())
        return {vaction.get_command(): vaction.get_value()}

    def network(self, params):
        commands = Network(params).network_record
        commands['network'] = params['network']
        Annotation.create(Annotation.TYPES.NETWORK.value, instance_names=params['instance_type'],
                          params="parameters: " + "Network" + "=>" + commands['network'] + ", uplink=>"
                                 + commands['uplink'] + ", downlink=>" + commands['downlink'])
        return commands

    def stress(self, connector, params):
        if 'instance_id' in params: name = params['instance_id']
        if 'instance_type' in params: name = params['instance_type']
        service_cpu = connector.get_running_container_processing(
            connector.instance_name(name).split(".")[0]
        )
        if not service_cpu: service_cpu = 1

        commands = StressAction(**params['action']).get_command(service_cpu)
        Annotation.create(Annotation.TYPES.STRESS.value, instance_names=params['instance_type'],
                          params="parameters: " + commands)
        return commands

    def command(self, params):
        commands = {"command": CommandAction(**params['action']).get_command()}
        Annotation.create(Annotation.TYPES.COMMAND.value, instance_names=params['instance_type'],
                          params="parameters: " + commands['command'])
        return commands

    def post(self, action_type: str):
        """
        request.data : {
            'params': {...}
        }
        :param action_type:
        :return:
        """
        connector = ConnectorClass(path=os.getcwd() + app.config['UPLOAD_FOLDER'])
        data = request.get_json()
        action_type = action_type.lower()

        if 'params' not in data: return {"message": "NOT OK"}
        params = data['params']

        if action_type == "horizontal_scaling":
            self.horizontal_scaling(connector,  params)
            return {"message": "OK"}

        commands = {}

        if action_type == "vertical_scaling": commands['vertical_scaling'] = self.vertical_scaling(params)
        if action_type == "network": commands["network"] = self.network(params)
        if action_type == "stress": commands["stress"] = self.stress(connector, params)
        if action_type == "command": commands["command"] = self.command(params)

        selected_instances = self.instance_ids(params)
        action_url = 'http://%s:5500/actions/'
        for i in selected_instances:
            requests.post(
                action_url % socket.gethostbyname(i), json={
                    'instances': selected_instances[i],
                    'commands': commands
                }, headers={'Content-Type': "application/json"}
            )

        return {"message": "OK"}


class ControlAPI(MethodView):
    """ This API is only for internal use between Agents and Controller"""

    def get(self, service):
        if service.lower() == "controller-properties":
            try:
                return {"credits": ConnectorClass().get_manager_info()}
            except Exception as ex:
                print(ex)
                return {"credits": ""}
        else:
            return {"message": "error"}

    def post(self, service):
        for ser in service.split("|"):
            commands = {"instances": [ser], "network_reset": 'true'}
            action_url = 'http://%s:5500/actions/'
            docker_instances = ConnectorClass().get_all_instances()
            selected_instances = []
            for node in docker_instances:
                for docker_instance in docker_instances[node]:
                    if service in docker_instance and node not in selected_instances:
                        selected_instances.append(node)
            for i in selected_instances:
                requests.post(
                    action_url % socket.gethostbyname(i), json={
                        'instances': [ser],
                        'commands': commands
                    }, headers={'Content-Type': "application/json"}
                )

        return {"message": "OK"}


class DistributionAPI(MethodView):
    """This API generates a network delay distribution from a network delay trace file (ping)"""

    def post(self, name):
        path = os.getcwd() + app.config['UPLOAD_FOLDER']

        if 'file' in request.files:
            file = request.files['file']
            if not os.path.exists(path): os.mkdir(path)
            file.save(os.path.join(path, "rttdata.txt"))

        res = generate_network_distribution(path, name)
        lines = res.split("\n")
        res = {}
        for line in lines:
            line_arr = line.split("=")
            if len(line_arr) == 2: res[line_arr[0].strip()] = line_arr[1].strip()
        connector = ConnectorClass()
        nodes = connector.get_nodes()

        for i in nodes:
            r = requests.post('http://' + nodes[i] + ':5500/generate-network-distribution/%s/' % name,
                              files={'file': open(os.path.join(path, name + ".dist"), 'rb')})

        return {"generated-distribution": res}


class SnifferAPI(MethodView):
    def delete(self):
        """ Removes the stored monitoring data """
        connector = ConnectorClass()
        nodes = connector.get_nodes()
        res = {}
        for i in nodes:
            try:
                r = requests.delete('http://' + nodes[i] + ':5500/packets/').json()
                res.update(r)
            except ConnectionError as e:
                print('The agent of node ' + str(i) + ' is offline')
        return {"message": "The monitorings are empty now"}

    def get(self):
        """ Returns the stored monitoring data """
        try:

            query = ""
            from_timestamp = request.args.get('from_timestamp')
            to_timestamp = request.args.get('to_timestamp')
            service = request.args.get('service')
            packet_type = request.args.get('packet_type')
            query += "from_timestamp=" + from_timestamp + "&" if from_timestamp else ""
            query += "to_timestamp=" + to_timestamp + "&" if to_timestamp else ""
            query += "service=" + service if service else ""
            query += "packet_type=" + packet_type if packet_type else ""
            connector = ConnectorClass()
            nodes = connector.get_nodes()
            res = []
            for i in nodes:
                try:
                    url = 'http://' + nodes[i] + ':5500/packets/'
                    url = url + "?" + query if query != "" else url
                    r = requests.get(url).json()
                    res.extend(r)
                except ConnectionError as e:
                    print('The agent of node ' + str(i) + ' is offline')
            return {"res": res}
        except Exception as e:
            return {
                "Error": "{0}".format(e)
            }
