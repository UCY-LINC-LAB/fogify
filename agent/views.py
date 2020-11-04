import os
from datetime import datetime

import docker
from flask import request
from flask.views import MethodView

from flask import current_app as app

from agent.models import Status, Record, Metric
from utils.monitoring import MetricCollector
from utils.network import apply_network_rule, read_network_rules, apply_default_rules, \
    inject_network_distribution


class MonitoringAPI(MethodView):
    """ With this API, agents return the monitored data or remove them. """

    def get(self):
        try:
            res = {}
            query = Record.query
            from_timestamp = request.args.get('from_timestamp')
            to_timestamp = request.args.get('to_timestamp')
            service = request.args.get('service')
            if from_timestamp:
                query = query.filter(Record.timestamp > datetime.fromtimestamp(int(from_timestamp)))
            if to_timestamp:
                query = query.filter(Record.timestamp < datetime.fromtimestamp(int(to_timestamp)))
            if service:
                query = query.filter(Record.instance_name == service)

            for r in query.all():
                if r.instance_name not in res:
                    res[r.instance_name] = []
                temp = {}
                temp['count'] = r.count
                temp['timestamp'] = r.timestamp
                for i in r.metrics:
                    temp[i.metric_name] = i.value
                res[r.instance_name].append(temp)
            return res
        except Exception as e:
            return {
                "Error": "{0}".format(e)
            }

    def delete(self):
        Record.query.delete()
        Metric.query.delete()
        Status.update_config('0')  # remove the counter
        return {"message": "The monitorings are empty now"}


class TopologyAPI(MethodView):
    """ Fogify Controller communicate with the agents through this API to apply network rules or to clean a deployment """

    def delete(self):
        path = os.getcwd() + app.config['UPLOAD_FOLDER']
        MetricCollector().remove_record_file(path + "metrics/")
        return {"message": "The topology is down."}

    def post(self):
        path = os.getcwd() + app.config['UPLOAD_FOLDER']

        if 'file' in request.files:
            file = request.files['file']
            if not os.path.exists(path):
                os.mkdir(path)

            file.save(os.path.join(path, "network.yaml"))

        return {"message": "OK"}


class ActionAPI(MethodView):
    """ Fogify Controller send ad-hoc actions through ActionAPI """
    def post(self):
        client = docker.from_env()
        instances = []
        for instance in request.get_json()['instances']:
            instances += [i for i in client.containers.list() if i.name.find(instance) > -1]

        commands = request.json['commands']

        if 'network_reset' in commands and commands['network_reset'] == 'true':
            infra = read_network_rules(os.getcwd() + app.config['UPLOAD_FOLDER'])
            service_name = request.get_json()['instances'][0]
            for instance in instances:
                apply_default_rules(infra, service_name, instance.name,
                                    instance.attrs['Config']['Labels']['com.docker.swarm.task.id'])

        if 'uplink' in commands and 'downlink' in commands and 'network' in commands:
            for instance in instances:
                apply_network_rule(instance.name,
                                   commands['network'],
                                   commands['downlink'],
                                   commands['uplink'],
                                   instance.attrs['Config']['Labels']['com.docker.swarm.task.id'][:10],
                                   "FALSE")

        if 'stress' in commands:
            for instance in instances:
                instance.exec_run(commands['stress'], detach=True)
            pass
        if 'vertical_scaling' in commands:
            for instance in instances:
                res = {}
                if 'CPU' in commands['vertical_scaling']:
                    rate = int(commands['vertical_scaling']['CPU'][1:]) / 100
                    current = int(instance.attrs['HostConfig']['CpuQuota'])
                    dif = rate * current
                    if commands['vertical_scaling'][0] == '-':
                        fin = current - dif
                    else:
                        fin = current + dif
                    res = {'cpu_quota': fin}
                elif 'MEMORY' in commands['vertical_scaling']:
                    res = {'mem_limit': commands['vertical_scaling']['MEMORY']}
                instance.update(**res)

        if 'command' in commands:
            for instance in instances:
                instance.exec_run(commands['command'], detach=True)

        return {"message": "OK"}


class DistributionAPI(MethodView):
    """ Through this API controller disseminates a new network delay distribution """
    def post(self, name):
        path = os.getcwd() + app.config['UPLOAD_FOLDER']

        if 'file' in request.files:
            file = request.files['file']
            if not os.path.exists(path):
                os.mkdir(path)

            file.save(os.path.join(path, name + ".dist"))

        inject_network_distribution(os.path.join(path, name + ".dist"))
        return {"success": True}
