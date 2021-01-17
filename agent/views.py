import logging
import os
from datetime import datetime

import docker
from flask import current_app as app
from flask import request
from flask.views import MethodView
from agent.models import Status, Record, Metric, Packet
from utils.monitoring import MetricCollector
from utils.network import NetworkController


class SnifferAPI(MethodView):
    ip_to_info = {}

    def ip_to_info_helper(self, ip):
        if ip not in self.ip_to_info:
            ip_to_info = Status.query.filter_by(value=ip).first()
            self.ip_to_info[ip] = ip_to_info.name.split("|") if ip_to_info else None
        return self.ip_to_info[ip]

    def get(self):
        query = Packet.query
        from_timestamp = request.args.get('from_timestamp')
        to_timestamp = request.args.get('to_timestamp')
        service = request.args.get('service')
        packet_type = request.args.get('packet_type')
        if from_timestamp:
            query = query.filter(Packet.timestamp > datetime.fromtimestamp(int(from_timestamp)))
        if to_timestamp:
            query = query.filter(Packet.timestamp < datetime.fromtimestamp(int(to_timestamp)))
        if service is not None:
            search = "%{}%".format(service)
            query = query.filter(Packet.service_id.ilike(search))
        if packet_type:
            query = query.filter(Packet.packet_type == packet_type)
        row2dict = lambda r: {c.name: str(getattr(r, c.name)) for c in r.__table__.columns}
        res = [row2dict(r) for r in query.all()]
        for r in res:
            src_obj = self.ip_to_info_helper(r['src_ip'])
            dest_obj = self.ip_to_info_helper(r['dest_ip'])
            r['src_instance'] = src_obj[0] if src_obj else r['src_ip']
            r['dest_instance'] = dest_obj[0] if dest_obj else r['dest_ip']
            r['network'] = None if src_obj is None else src_obj[2]
            if r['network'] is None:
                r['network'] = None if dest_obj is None else dest_obj[2]
        return res

    def delete(self):
        Packet.query.delete()
        return {"message": "The packets are empty now"}


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
                if r.instance_name not in res: res[r.instance_name] = []
                temp = {i.metric_name: i.value for i in r.metrics}
                temp['count'] = r.count
                temp['timestamp'] = r.timestamp
                res[r.instance_name].append(temp)
            return res
        except Exception as e:
            logging.error("An error occurred on monitoring view. The metrics did not retrieved.",
                          exc_info=True)
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
        connector=app.config['CONNECTOR']
        path = connector.path
        MetricCollector().remove_record_file(path + "metrics/")
        return {"message": "The topology is down."}

    def post(self):
        connector = app.config['CONNECTOR']
        if 'file' in request.files:
            file = request.files['file']
        NetworkController(connector).save_network_rules(file)
        return {"message": "OK"}


class ActionsAPI(MethodView):
    """ Fogify Controller send ad-hoc actions through ActionAPI """

    def get_common_requirements(self):
        connector = app.config['CONNECTOR']
        net_controller = NetworkController(connector)
        network_rules = net_controller.read_network_rules()
        return connector, net_controller, network_rules

    def get_rules_and_container_data(self, connector, instance, network_rules):
        instance_name = connector.instance_name(instance.name)
        if instance_name.rfind("_") > 0:
            service_name = instance_name[:instance_name.rfind("_")]
        elif instance_name.rfind(".") > 0:
            service_name = instance_name[:instance_name.rfind(".")]
        service_network_rule = network_rules[service_name] if service_name in network_rules else {}
        return instance_name, service_name, service_network_rule

    def merge_links(self, old_links, new_links):
        if len(old_links) == 0: return new_links

        new_link_dict = {new_link['from_node'] + "___" + new_link['to_node']: new_link['command'] for new_link in new_links}
        old_link_dict = {old_link['from_node'] + "___" + old_link['to_node']: old_link['command'] for old_link in old_links}
        old_link_dict.update(new_link_dict)
        fin_link = []
        for key, value in old_link_dict.items():
            fin_link.append(dict(from_node=key.split("___")[0], to_node=key.split("___")[1], command=value))
        return fin_link

    def common_link_and_network(self, commands, instances):
        if 'network' not in commands: return {}

        links = commands['links'] if 'links' in commands else []
        uplink = commands['uplink'] if 'uplink' in commands else None
        downlink = commands['downlink'] if 'downlink' in commands else None
        network = commands['network']

        connector, net_controller, network_rules = self.get_common_requirements()
        for instance in instances:
            instance_name, service_name, ser_net_rule = self.get_rules_and_container_data(connector, instance, network_rules)
            if network != 'all':
                ser_net_rule[network]['links'] = self.merge_links(ser_net_rule[network]['links'], links)
                if uplink: ser_net_rule[network]['uplink'] = uplink
                if downlink: ser_net_rule[network]['downlink'] = downlink
                network_rules[service_name] = ser_net_rule
                net_controller.save_network_rules(network_rules)
            net_controller.execute_network_commands(service_name, instance.id, instance.name, ser_net_rule, "False")

    def link(self, commands, instances):
        commands = commands['links']
        self.common_link_and_network(commands, instances)

    def network(self, commands, instances):
        command = commands['network']
        self.common_link_and_network(command, instances)


    def stress(self, commands, instances):
        for instance in instances:
            instance.exec_run(commands['stress'], detach=True)

    def vertical_scaling(self, commands, instances):
        for instance in instances:
            res = {}
            if 'CPU' in commands['vertical_scaling']:
                rate = int(commands['vertical_scaling']['CPU'][1:]) / 100
                current = int(instance.attrs['HostConfig']['CpuQuota'])
                dif = rate * current
                fin = current - dif if commands['vertical_scaling'][0] == '-' else current + dif
                res = {'cpu_quota': fin}
            elif 'MEMORY' in commands['vertical_scaling']:
                res = {'mem_limit': commands['vertical_scaling']['MEMORY']}
            instance.update(**res)

    def command(self, commands, instances):
        for instance in instances:
            instance.exec_run(commands['command'], detach=True)


    def post(self):
        client = docker.from_env()
        instances = []
        obj_json = request.get_json()

        for instance in obj_json['instances']:
            instances += [i for i in client.containers.list() if i.name.find(instance) > -1]

        commands = obj_json['commands']

        if 'links' in commands: self.link(commands, instances)

        if 'network' in commands: self.network(commands, instances)

        if 'stress' in commands: self.stress(commands, instances)

        if 'vertical_scaling' in commands: self.vertical_scaling(commands, instances)

        if 'command' in commands: self.command(commands, instances)

        return {"message": "OK"}


class DistributionAPI(MethodView):
    """ Through this API controller disseminates a new network delay distribution """

    def post(self, name):
        path = os.getcwd() + app.config['UPLOAD_FOLDER']

        if 'file' in request.files:
            file = request.files['file']
            if not os.path.exists(path): os.mkdir(path)

            file.save(os.path.join(path, name + ".dist"))

        NetworkController.inject_network_distribution(os.path.join(path, name + ".dist"))
        return {"success": True}
