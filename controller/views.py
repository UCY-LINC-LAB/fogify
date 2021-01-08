import os
import socket

import requests
import yaml
from flask import current_app as app
from flask import request
from flask.views import MethodView

from connectors import get_connector_class
from controller.models import Status, Annotation
from models.actions import StressAction, VerticalScalingAction, CommandAction
from models.base import NetworkGenerator, Network
from utils.general import AsyncTask
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
        path = os.getcwd() + app.config['UPLOAD_FOLDER']
        t = AsyncTask(self, 'remove')
        t.start()
        return {"message": "The topology is down."}

    @ConnectorClass.check_status("available")
    def post(self):
        """ Introduce a new deployment to the fogify"""

        path = os.getcwd() + app.config['UPLOAD_FOLDER']

        Annotation.create(Annotation.TYPES.START.value)
        if 'file' in request.files:
            file = request.files['file']
            if not os.path.exists(path):
                os.mkdir(path)

            file.save(os.path.join(path, "docker-compose.yaml"))
        f = open(os.path.join(path, "docker-compose.yaml"), "r")
        infra = yaml.load(f)

        # application = infra.copy()
        from models.base import FogifyModel
        model = FogifyModel(infra)

        connector = ConnectorClass(model,
                                   path=path,
                                   frequency=int(os.environ['CPU_FREQ']) if 'CPU_FREQ' in os.environ else 2400,
                                   cpu_oversubscription=int(os.environ[
                                                                'CPU_OVERSUBSCRIPTION_PERCENTAGE']) if 'CPU_OVERSUBSCRIPTION_PERCENTAGE' in os.environ else 0,
                                   ram_oversubscription=int(os.environ[
                                                                'RAM_OVERSUBSCRIPTION_PERCENTAGE']) if 'RAM_OVERSUBSCRIPTION_PERCENTAGE' in os.environ else 0
                                   )

        swarm = connector.generate_files()

        networks = NetworkGenerator(model).generate_network_rules()

        yaml.dump(networks, open(path + "fogified-network.yaml", 'w'), default_flow_style=False)

        t = AsyncTask(self, 'submition', [connector, path, model.all_networks])
        t.start()
        return {
            "message": "OK",
            "swarm": swarm,
            "networks": networks
        }

    def remove(self):
        """ A utility function that destroys a topology """
        connector = ConnectorClass(path=os.getcwd() + app.config['UPLOAD_FOLDER'])
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
        print(params)
        if 'instance_id' in params and params['instance_id'] in docker_instances:
            print("1 ", docker_instances)
            return {
                docker_instances[params['instance_id']]: [params['instance_id']]
            }
        elif 'instance_type' in params and 'instances' in params:
            instance_type = params['instance_type']
            instances = {}
            for node in docker_instances:
                print(node)
                print(instance_type)
                for i in docker_instances[node]:
                    if i.find(instance_type) >= 0:
                        if node not in instances:
                            instances[node] = []
                        instances[node] += [i]
            print("2 ", instances)
            return instances
        print("3")
        return {}

    def post(self, action_type):
        """
        request.data : {
            'params': {...}
        }
        :param action_type:
        :return:
        """
        connector = ConnectorClass(path=os.getcwd() + app.config['UPLOAD_FOLDER'])
        data = request.get_json()
        # TODO check how to define the possible containers or services
        if 'params' in data:
            params = data['params']
            if action_type == "horizontal_scaling":

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
                print("SCALE: ",params['instance_type'],service_count)
                connector.scale(params['instance_type'], service_count)

            else:
                selected_instances = self.instance_ids(params)
                commands = {}
                if action_type == "vertical_scaling":
                    vaction = VerticalScalingAction(**data['params']['action'])
                    commands['vertical_scaling'] = {vaction.get_command(): vaction.get_value()}
                    Annotation.create(Annotation.TYPES.V_SCALE.value, instance_names=params['instance_type'],
                                      params="parameters: " + vaction.get_command() + "=>" + vaction.get_value())
                if action_type == "network":
                    action = data['params']
                    commands = Network(action).network_record
                    commands['network'] = action['network']
                    Annotation.create(Annotation.TYPES.NETWORK.value, instance_names=params['instance_type'],
                                      params="parameters: " + "Network" + "=>" + commands['network'] + ", uplink=>"
                                             + commands['uplink'] + ", downlink=>" + commands['downlink'])
                if action_type == "stress":
                    service_cpu = None
                    if 'instance_type' in params:
                        service_cpu = connector.get_running_container_processing(
                            connector.instance_name(params['instance_type'])
                            # params['instance_type'] if not params['instance_type'].split(".")[
                            #     -1].isnumeric() else "".join(params['instance_type'].split(".")[:-1])
                        )
                        print("service_cpu: ", service_cpu)
                    elif 'instance_id' in params:
                        service_cpu = connector.get_running_container_processing(
                            params['instance_id'] if not params['instance_id'].split(".")[-1].isnumeric() else "".join(
                                params['instance_id'].split(".")[:-1])
                        )
                    else:
                        service_cpu = 1
                    service_cpu = 1 if not service_cpu else service_cpu
                    commands['stress'] = StressAction(**data['params']['action']).get_command(
                        service_cpu
                    )
                    Annotation.create(Annotation.TYPES.STRESS.value, instance_names=params['instance_type'],
                                      params="parameters: " + commands['stress'])

                if action_type == "command":
                    commands["command"] = CommandAction(**data['params']['action']).get_command()
                    Annotation.create(Annotation.TYPES.COMMAND.value, instance_names=params['instance_type'],
                                      params="parameters: " + commands['command'])

                action_url = 'http://%s:5500/actions/'
                for i in selected_instances:
                    print(i)
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
            if not os.path.exists(path):
                os.mkdir(path)

            file.save(os.path.join(path, "rttdata.txt"))

        res = generate_network_distribution(path, name)
        lines = res.split("\n")
        res = {}
        for l in lines:
            line = l.split("=")
            if len(line) == 2:
                res[line[0].strip()] = line[1].strip()
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
