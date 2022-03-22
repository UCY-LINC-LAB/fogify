import copy
import json
import logging
import os
import threading
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
        query = self.__compute_get_query()
        __row2dict = lambda r: {c.name: str(getattr(r, c.name)) for c in r.__table__.columns}
        res = [__row2dict(r) for r in query.all()]
        return [self.__transform_record(r) for r in res]

    def __transform_record(self, record):
        src_obj = self.ip_to_info_helper(record['src_ip'])
        dest_obj = self.ip_to_info_helper(record['dest_ip'])
        record['src_instance'] = src_obj[0].replace("monitoring_network_cache:fogify_", "") if src_obj else record[
            'src_ip']
        record['dest_instance'] = dest_obj[0].replace("monitoring_network_cache:fogify_", "") if dest_obj else record[
            'dest_ip']
        record['network'] = None if src_obj is None else src_obj[2]
        if record['network'] is None:
            record['network'] = None if dest_obj is None else dest_obj[2]
        return record

    def __compute_get_query(self):
        query = Packet.query
        from_timestamp, packet_type, service, to_timestamp = self.__retrieve_requests_parameters()
        if from_timestamp:
            query = query.filter(Packet.timestamp > datetime.fromtimestamp(int(from_timestamp)))
        if to_timestamp:
            query = query.filter(Packet.timestamp < datetime.fromtimestamp(int(to_timestamp)))
        if service is not None:
            search = "%{}%".format(service)
            query = query.filter(Packet.service_id.ilike(search))
        if packet_type:
            query = query.filter(Packet.packet_type == packet_type)
        return query

    def __retrieve_requests_parameters(self):
        from_timestamp = request.args.get('from_timestamp')
        to_timestamp = request.args.get('to_timestamp')
        service = request.args.get('service')
        packet_type = request.args.get('packet_type')
        return from_timestamp, packet_type, service, to_timestamp

    def delete(self):
        Packet.query.delete()
        return {"message": "The packets are empty now"}


class MonitoringAPI(MethodView):
    """ With this API, agents return the monitored data or remove them. """

    def get(self):
        try:
            res = {}
            query = self.__compute_get_query()
            for r in query.all():
                if r.instance_name not in res: res[r.instance_name] = []
                temp = self.__transform_record(r)
                res[r.instance_name].append(temp)
            return res
        except Exception as e:
            logging.error("An error occurred on monitoring view. The metrics did not retrieved.", exc_info=True)
            return {"Error": "{0}".format(e)}

    def __transform_record(self, r):
        temp = {i.metric_name: i.value for i in r.metrics}
        temp['count'] = r.count
        temp['timestamp'] = r.timestamp
        return temp

    def __compute_get_query(self):
        query = Record.query
        from_timestamp, service, to_timestamp = self.__retrieve_requests_parameters()
        if from_timestamp:
            query = query.filter(Record.timestamp > datetime.fromtimestamp(int(from_timestamp)))
        if to_timestamp:
            query = query.filter(Record.timestamp < datetime.fromtimestamp(int(to_timestamp)))
        if service:
            query = query.filter(Record.instance_name == service)
        return query

    def __retrieve_requests_parameters(self):
        from_timestamp = request.args.get('from_timestamp')
        to_timestamp = request.args.get('to_timestamp')
        service = request.args.get('service')
        return from_timestamp, service, to_timestamp

    def delete(self):
        Record.query.delete()
        Metric.query.delete()
        MetricCollector.clean_cache_ip()
        Status.update_config('0')  # remove the counter
        return {"message": "The monitorings are empty now"}


class TopologyAPI(MethodView):
    """ Fogify Controller communicate with the agents through this API to apply network rules or to clean a deployment """

    def delete(self):
        connector = app.config['CONNECTOR']
        path = connector.path
        MetricCollector().remove_record_file(path + "metrics/")
        network_controller = app.config['NETWORK_CONTROLLER']
        network_controller.remove_cached_ips()
        os.putenv('EMULATION_IS_RUNNING', 'FALSE')
        return {"message": "The topology is down."}

    def post(self):
        network_controller = app.config['NETWORK_CONTROLLER']
        connector = app.config['CONNECTOR']
        if 'file' in request.data:
            print(request.data.to_dict())
            file = request.data['file']
            file = json.loads(file)
            print("--------------file----------------", file)
            network_controller.save_network_rules(file)
            return {"message": "OK"}
        else:
            network_rules = network_controller.read_network_rules
            os.putenv('EMULATION_IS_RUNNING', 'TRUE')
            infos = connector.get_local_containers_infos()
            for info in infos:
                threading.Thread(target=NetworkController.apply_network_qos_for_event,
                    args=(network_controller, info, network_rules, False)).start()
            return {"message": "OK"}


class ActionsAPI(MethodView):
    """ Fogify Controller send ad-hoc actions through ActionAPI """

    def get_rules_and_container_data(self, instance_name, network_rules):
        connector = app.config['CONNECTOR']
        service_name = connector.get_service_from_name(instance_name)
        service_network_rule = network_rules[service_name] if service_name in network_rules else {}
        return service_name, service_network_rule

    def merge_links(self, old_links, new_links):
        if len(old_links) == 0: return new_links
        new_link_dict = {new_link['from_node'] + "___" + new_link['to_node']: new_link['command'] for new_link in
                         new_links}
        old_link_dict = {old_link['from_node'] + "___" + old_link['to_node']: old_link['command'] for old_link in
                         old_links}
        old_link_dict.update(new_link_dict)
        fin_links = []
        for key, value in old_link_dict.items():
            fin_links.append(dict(from_node=key.split("___")[0], to_node=key.split("___")[1], command=value))
        return fin_links

    def common_link_and_network(self, commands, instances):
        if 'network' not in commands: return {}
        network, uplink, downlink, links = self.__get_link_and_network_parameters(commands)
        connector = app.config['CONNECTOR']
        network_controller = app.config['NETWORK_CONTROLLER']
        network_rules = copy.deepcopy(network_controller.read_network_rules)
        for instance in instances:
            instance_name = connector.instance_name(instance.name)
            service_name, service_network_rules = self.get_rules_and_container_data(instance_name, network_rules)
            if network != 'all':
                # Update network rules for the service
                service_network_rules[network]['links'] = self.merge_links(service_network_rules[network]['links'],
                                                                           links)
                if uplink: service_network_rules[network]['uplink'] = uplink
                if downlink: service_network_rules[network]['downlink'] = downlink
                network_rules[service_name] = service_network_rules  # net_controller.save_network_rules(network_rules)
            network_controller.execute_network_commands(service_name, instance.id, service_network_rules)

    def __get_link_and_network_parameters(self, commands):
        links = commands['links'] if 'links' in commands else []
        uplink = commands['uplink'] if 'uplink' in commands else None
        downlink = commands['downlink'] if 'downlink' in commands else None
        network = commands['network']
        return network, uplink, downlink, links

    def links(self, commands, instances):
        commands = commands['links']
        self.common_link_and_network(commands, instances)

    def network(self, commands, instances):
        command = commands['network']
        self.common_link_and_network(command, instances)

    def stress(self, commands, instances):
        for instance in instances:
            instance.exec_run(commands['stress'], detach=True)

    def vertical_scaling(self, commands, instances):
        vertical_scaling = commands['vertical_scaling']
        for instance in instances:
            res = {}
            if 'CPU' in vertical_scaling:
                rate = int(vertical_scaling['CPU'][1:]) / 100
                is_decrease = vertical_scaling['CPU'][0] == '-'
                current_quota = int(instance.attrs['HostConfig']['CpuQuota'])
                dif = rate * current_quota
                new_quota = current_quota - dif if is_decrease else current_quota + dif
                res = {'cpu_quota': new_quota}
            elif 'MEMORY' in vertical_scaling:
                res = {'mem_limit': vertical_scaling['MEMORY']}
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

        if 'links' in commands: self.links(commands, instances)
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
