import json
from os.path import exists
from time import sleep

import dateutil.parser as p
import docker
import requests

from agent.models import Status, Metric, db, Record
from connectors import get_connector_class
from utils import docker_manager
from utils.docker_manager import get_container_ip_property, get_ip_from_network_object, \
    ContainerNetworkNamespace

ConnectorClass = get_connector_class()


class MetricCollector(object):

    def get_custom_metrics(self, instance):
        path = docker_manager.get_host_data_path(instance['id'])
        metrics = {}

        if not (path and exists(path + "/fogify/metrics")): return []

        with open(path + "/fogify/metrics") as json_file:
            data = json.load(json_file)
            for i in data:
                if str(data[i]).isnumeric(): metrics[i] = float(data[i])

        return [Metric(metric_name=metric, value=metrics[metric]) for metric in metrics]

    def millis_interval(self, start, end):
        """start and end are datetime instances"""
        diff = end - start
        millis = diff.days * 24 * 60 * 60 * 1000
        millis += diff.seconds * 1000
        millis += diff.microseconds / 1000
        return millis

    def get_docker_metrics(self, agent_ip):
        try:
            return requests.get("http://%s:9090/api/v1.3/docker/" % agent_ip).json()
        except Exception: return []

    def is_instance_of_fogify(self, instance):
        for alias in instance['aliases']:
            if alias.startswith('fogify_'):
                return alias

    def cpu_util_val(self, instance_name, instance):
        last_cpu_record = None
        last_stat = instance['stats'][-1]
        cpu_specs = instance['spec']['cpu']
        record = Record.query.filter_by(instance_name=instance_name).order_by(Record.count.desc()).limit(1).first()
        if not record: return 0

        for i in record.metrics:
            if i.metric_name == 'cpu':
                last_cpu_record = i
                break

        if not last_cpu_record: return 0

        timedif = abs(self.millis_interval(p.parse(instance['stats'][-1]['timestamp']).replace(tzinfo=None),
                                           record.timestamp.replace(tzinfo=None)))
        if timedif == 0: timedif = 1

        rate = (float(last_stat['cpu']['usage']['total']) - float(last_cpu_record.value)) / timedif
        val = 1.0
        if 'quota' in cpu_specs:
            val = cpu_specs['quota']
        elif 'mask' in cpu_specs:
            mask = int(cpu_specs['mask'].split("-")[-1]) + 1
            period = float(cpu_specs['period'] if 'period' in cpu_specs else 1.0)
            val = float( mask / period)
        cpu_util_val = 10*float(rate/val)
        # cpu_util_val /= 10000
        return cpu_util_val

    def get_ip(self, container, cadv_net, nets):
        search = "%{}%".format(container.name + "|" + cadv_net["name"] + "|")
        conf = Status.query.filter(Status.name.like(search)).first()

        if conf is not None: return conf.value

        with ContainerNetworkNamespace(container.id):
            eth_ip = get_container_ip_property(cadv_net["name"])

        if not eth_ip: return

        ip = eth_ip[eth_ip.find("inet ") + len("inet "):eth_ip.rfind("/")]
        if ip in nets:
            Status.update_config(ip, container.name + "|" + cadv_net["name"] + "|" + nets[ip])
        else:
            Status.update_config(ip, container.name + "|" + cadv_net["name"] + "|")
        return ip

    def get_default_metrics(self, instance_name, instance_obj, machine):
        last_stat = instance_obj['stats'][-1]
        mem_specs = instance_obj['spec']['memory']['limit'] if 'limit' in instance_obj['spec']['memory'] else \
            machine['memory_capacity']
        cpu_util = Metric(metric_name="cpu_util", value=float(self.cpu_util_val(instance_name, instance_obj)))
        cpu = Metric(metric_name="cpu", value=float(last_stat['cpu']['usage']['total']))
        memory = Metric(metric_name="memory", value=float(last_stat['memory']['usage']))
        memory_util = Metric(metric_name="memory_util", value=float(last_stat['memory']['usage']) / float(mem_specs))
        disk = Metric(metric_name="disk_bytes", value=float(last_stat['filesystem'][0]['usage']))
        return [cpu_util, cpu, memory, memory_util, disk]

    def get_network_metrics(self, instance):
        last_stat = instance['stats'][-1]
        client = docker.from_env()
        container = client.containers.get(instance["id"])
        res = []
        for network in container.attrs["NetworkSettings"]["Networks"]:
            ip = get_ip_from_network_object(container.attrs["NetworkSettings"]["Networks"][network])
            nets = {ip: network}

        for cadv_net in last_stat['network']['interfaces']:
            ip = self.get_ip(container, cadv_net, nets)

            if not (ip in nets and nets[ip] != 'ingress'): continue
            res.append(Metric(metric_name="network_rx_" + nets[ip], value=int(cadv_net['rx_bytes'])))
            res.append(Metric(metric_name="network_tx_" + nets[ip], value=int(cadv_net['tx_bytes'])))
        return res

    def save_metrics(self, agent_ip):
        interval = 5
        machine = requests.get("http://%s:9090/api/v1.3/machine" % agent_ip).json()
        print("Monitoring Agent Instantiation")

        while (True):
            count = Status.query.filter_by(name="counter").first()
            count = 0 if count is None else int(count.value)
            docker_instances = self.get_docker_metrics(agent_ip)
            for i in docker_instances:
                try:
                    instance_obj = docker_instances[i]
                    alias = self.is_instance_of_fogify(instance_obj)
                    if not alias: continue
                    instance_name = ConnectorClass.instance_name(alias)
                    r = Record(timestamp=p.parse(instance_obj['stats'][-1]['timestamp']), count=count,
                               instance_name=instance_name)
                    r.metrics.extend(self.get_default_metrics(instance_name, instance_obj, machine))
                    r.metrics.extend(self.get_network_metrics(instance_obj))
                    r.metrics.extend(self.get_custom_metrics(instance_obj))
                    db.session.add(r)
                    db.session.commit()
                except Exception as ex:
                    import traceback
                    print("error", ex)
                    traceback.print_tb(ex.__traceback__)
                    continue
            count += 1
            Status.update_config(str(count))
            sleep(interval)
