import os
import socket
import traceback

from flask_api import exceptions
import requests
import yaml
from flask import current_app as app
from flask import request
from flask.views import MethodView
from FogifyModel.base import FogifyModel
from connectors import get_connector_class, get_connector
from controller.models import Status, Annotation
from FogifyModel.actions import StressAction, VerticalScalingAction, CommandAction
from FogifyModel.base import Network
from utils.async_task import AsyncTask
from utils.inter_communication import Communicator
from utils.network import NetworkController
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
        connector = get_connector()
        return connector.return_deployment()

    @ConnectorClass.check_status("running")
    def delete(self):
        """ Remove a Fogify deployment"""
        Status.update_config('submit_delete')
        Annotation.create(Annotation.TYPES.STOP.value)
        connector = get_connector()
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

        try:
            connector = get_connector(model=model)
            controller_response = connector.generate_files()
            yaml.dump(controller_response, open(path + "fogified-swarm.yaml", 'w'), default_flow_style=False)
            networks = model.generate_network_rules()
        except Exception as ex:
            print("controller error")
            print(ex)
            print(traceback.format_exc())
            raise exceptions.APIException("Fogify could not generate the orchestrator files."
                                          "Please check your fogify model again.")


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
        file = open(path + "fogified-network.yaml", 'rb')
        Communicator(connector).agents__forward_network_file(file)

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
        return Communicator(get_connector()).agents__delete_metrics()

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

            return Communicator(get_connector()).agents__get_metrics(query)

        except Exception as e:
            return {
                "Error": "{0}".format(e)
            }


class ActionsAPI(MethodView):
    """ This API class applies the actions to a running topology"""

    def links(self,  params):
        """
        {'network': 'internet', 'links': [{'from_node': 'cloud-server', 'to_node': 'mec-svc-1', 'bidirectional': False, 
        'properties': {'latency': {'delay': '1500ms'}}}], 'instance_type': 'cloud-server', 'instances': 1}

        """
        if 'links' not in params: return {}
        if 'network' not in params: return {}

        commands = {}
        commands['network'] = params['network']
        res = []
        for link in params['links']:
            res.extend(Network.get_link(link))
        commands['links'] = res

        Annotation.create(Annotation.TYPES.UPDATE_LINKS.value, instance_names=params['instance_type'],
                          params="parameters: " + "Network" + "=>" + commands['network'] + ", link number=>"
                                 + str(len(commands['links'])))
        return commands

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
        new_params = {i: params[i] for i in params if i not in ['instance_type', 'network', 'instance_id', 'instances']}
        network = params['network']
        if not new_params and 'network' in params:
            new_params = params['network']
            network = new_params['network']
        if not new_params: return {}

        commands = Network(new_params).network_record

        commands['network'] = network
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
        connector = get_connector()
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
        if action_type == "links": commands["links"] = self.links(params)

        Communicator(get_connector()).agents__perform_action(commands, **params)

        return {"message": "OK"}


class ControlAPI(MethodView):
    """ This API is only for internal use between Agents and Controller"""

    def get(self, service):
        if service.lower() == "controller-properties":
            try:
                return {"credits": get_connector().get_manager_info()}
            except Exception as ex:
                print(ex)
                return {"credits": ""}
        else:
            return {"message": "error"}

    def post(self, service):
        commands = {
            'network': 'all',
            'links':[]
        }
        Communicator(get_connector()).agents__perform_action(commands, instance_type=service)
        return {"message": "OK"}


class DistributionAPI(MethodView):
    """This API generates a network delay distribution from a network delay trace file (ping)"""

    def post(self, name):
        path = os.getcwd() + app.config['UPLOAD_FOLDER']

        if 'file' in request.files:
            file = request.files['file']
            if not os.path.exists(path): os.mkdir(path)
            file.save(os.path.join(path, "rttdata.txt"))

        res = NetworkController.generate_network_distribution(path, name)
        lines = res.split("\n")
        res = {}
        for line in lines:
            line_arr = line.split("=")
            if len(line_arr) == 2: res[line_arr[0].strip()] = line_arr[1].strip()

        Communicator(get_connector()).agents__disseminate_net_distribution(
            name, open(os.path.join(path, name + ".dist"), 'rb'))

        return {"generated-distribution": res}


class SnifferAPI(MethodView):
    def delete(self):
        """ Removes the stored monitoring data """
        return Communicator(get_connector()).agents__delete_packets()

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
            return Communicator(get_connector()).agents__get_packets(query)
        except Exception as e:
            return {
                "Error": "{0}".format(e)
            }
