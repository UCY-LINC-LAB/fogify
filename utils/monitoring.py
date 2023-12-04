import json
from os.path import exists
from time import sleep

import dateutil.parser as p
import docker
import requests

from agent.models import Status, Metric, db, Record
from utils.async_task import AsyncTask
from utils.docker_manager import get_container_ip_property, get_ip_from_network_object, ContainerNetworkNamespace
from utils.logging import FogifyLogger

logger = FogifyLogger(__name__)


class cAdvisorHandler(object):

    def __init__(self, ip, port, project, client=docker.from_env()):
        self.ip = ip
        self.port = port
        self.project = project
        self.current_instance = None
        self.metrics = []
        self.machine = []
        self.instance_name = None
        self.current_instance = {}
        self.retrieve_machine_info()
        self.client = client

    def retrieve_docker_metrics(self):
        containers = [i for i in self.client.containers.list() if i.name.startswith("fogify_")]
        res = {}
        for container in containers:
            try:
                stats = self.get_stats_from_cadvisor(container)
                print(stats)
                res.update(stats)
            except Exception:
                logger.warning("Monitoring agent did not capture the metrics this time")
                continue

        self.metrics = res

    def get_stats_from_cadvisor(self, container):
        print("http://%s:%s/api/v2.0/stats/%s?type=docker" % (self.ip, self.port, container.id))
        stats = requests.get("http://%s:%s/api/v2.0/stats/%s?type=docker" % (self.ip, self.port, container.id)).json()
        #print(stats)
        key = f'/system.slice/docker-{container.id}.scope'
        #print(key)
        #print(stats[key])
        stats[key] = {"stats": stats[key], "aliases": [container.name], "id": container.id,
            "limits": dict(memory=container.attrs['HostConfig']['Memory'],
                           cpu=container.attrs['HostConfig']['NanoCpus'])}
        return stats

    def retrieve_machine_info(self):
        self.machine = requests.get("http://%s:%s/api/v1.3/machine" % (self.ip, self.port)).json()

    def set_current_instance_name(self, instance_name: str):
        self.instance_name = instance_name

    def set_current_instance(self, instance):
        self.current_instance = instance

    def return_project_alias(self):
        for alias in self.current_instance['aliases']:
            if alias.startswith(self.project):
                return alias
        return None

    def get_last_stats(self):
        return self.current_instance['stats'][-1]

    def get_last_stats_cpu_usage(self):
        return float(self.get_last_stats()['cpu']['usage']['total'])

    def get_last_stats_disk_usage(self):
        return float(self.get_last_stats()['filesystem'][0]['usage'])

    def get_last_stats_timestamp(self):
        return self.get_last_stats()['timestamp']

    def get_last_stats_memory_usage(self):
        return float(self.get_last_stats()['memory']['usage'])

    def get_last_stats_memory_util(self):
        return 100 * self.get_last_stats_memory_usage() / self.get_mem_quota()

    def get_last_saved_record(self, instance_name):
        return Record.query.filter_by(instance_name=instance_name).order_by(Record.count.desc()).limit(1).first()

    def get_last_stats_cpu_util(self):
        record = self.get_last_saved_record(self.instance_name)

        if not record: return 0
        last_cpu_record = record.get_metric_by_name("cpu")

        timedif = abs(self.millis_interval(p.parse(self.get_last_stats_timestamp()).replace(tzinfo=None),
                                           record.timestamp.replace(tzinfo=None)))
        if timedif == 0: timedif = 1

        rate = (float(self.get_last_stats_cpu_usage()) - float(last_cpu_record.value)) / timedif
        val = self.get_cpu_quota()
        cpu_util_val = 0
        if val:
            cpu_util_val = 100000 * float(rate / val)
        return cpu_util_val

    def get_last_stats_networks(self):
        return self.get_last_stats()['network']['interfaces']

    def get_cpu_specs(self):
        return float(self.current_instance['limits']['cpu'])

    def get_mem_specs(self):
        return self.current_instance['limits']['memory']  # self.current_instance['spec']['memory']

    def get_mem_quota(self):
        mem_specs = self.get_mem_specs()
        if not mem_specs:
            mem_specs = self.machine['memory_capacity']
        return float(mem_specs)

    def get_cpu_quota(self):
        cpu_specs = self.get_cpu_specs()
        if not cpu_specs: return
        return cpu_specs

    def get_cpu_mask(self):
        try:
            return int(self.get_cpu_specs()['mask'].split("-")[-1]) + 1
        except Exception:
            logger.warning('There is no mask in cpu specs', exc_info=True)
            return 0

    def get_cpu_period(self):
        cpu_specs = self.get_cpu_specs()
        return float(cpu_specs['period'] if cpu_specs and 'period' in cpu_specs else 1.0)

    def get_cpu_mask_to_period_ratio(self):
        return self.get_cpu_mask() / self.get_cpu_period()

    def get_mem_quota(self):
        memory = self.get_mem_specs()
        mem_specs = memory if memory else self.machine['memory_capacity']
        return float(mem_specs)

    def millis_interval(self, start, end):
        """start and end are datetime instances"""
        diff = end - start
        millis = diff.days * 24 * 60 * 60 * 1000
        millis += diff.seconds * 1000
        millis += diff.microseconds / 1000
        return millis

    def get_metrics(self):
        return self.metrics


class MetricCollector(object):

    def get_custom_metrics(self, instance, connector):
        path = connector.get_host_data_path(instance['id'])
        metrics = {}

        if not (path and exists(path + "/fogify/metrics")): return []

        with open(path + "/fogify/metrics") as json_file:
            data = json.load(json_file)
            for i in data:
                if str(data[i]).isnumeric(): metrics[i] = float(data[i])

        return [Metric(metric_name=metric, value=metrics[metric]) for metric in metrics]

    def get_cache_ip(self, container_name, network_name):
        search = "%{}%".format(container_name + "|" + network_name + "|")
        conf = Status.query.filter(Status.name.like(search)).first()
        if conf is not None: return conf.value

    @staticmethod
    def clean_cache_ip():
        Status.query.filter(Status.name.like("%monitoring_network_cache:%")).delete(synchronize_session='fetch')
        db.session.commit()

    def set_cache_ip(self, ip, container_name, network_name):
        Status.update_config(ip, "monitoring_network_cache:" + container_name + "|" + network_name + "|")

    def get_ip(self, container, cadv_net):
        old_ip = self.get_cache_ip(container.name, cadv_net["name"])
        if old_ip: return old_ip
        with ContainerNetworkNamespace(container.id):
            eth_ip = get_container_ip_property(cadv_net["name"])

        if not eth_ip: return

        ip = eth_ip[eth_ip.find("inet ") + len("inet "):eth_ip.rfind("/")]
        self.set_cache_ip(ip, container.name, cadv_net["name"])
        return ip

    def get_default_metrics(self, cAdvisor_handler):
        cpu_util = Metric(metric_name="cpu_util", value=cAdvisor_handler.get_last_stats_cpu_util())
        cpu = Metric(metric_name="cpu", value=cAdvisor_handler.get_last_stats_cpu_usage())
        memory = Metric(metric_name="memory", value=cAdvisor_handler.get_last_stats_memory_usage())
        memory_util = Metric(metric_name="memory_util", value=cAdvisor_handler.get_last_stats_memory_util())
        disk = Metric(metric_name="disk_bytes", value=cAdvisor_handler.get_last_stats_disk_usage())
        return [cpu_util, cpu, memory, memory_util, disk]

    def get_network_metrics(self, cAdvisor_handler: cAdvisorHandler):
        current_container = docker.from_env().containers.get(cAdvisor_handler.current_instance["id"])
        nets = self.get_ips_to_networks_dict(current_container)
        res = []
        for cadv_net in cAdvisor_handler.get_last_stats_networks():
            ip = self.get_ip(current_container, cadv_net)
            if not (ip in nets and nets[ip] != 'ingress'): continue
            res.append(Metric(metric_name="network_rx_" + nets[ip], value=int(cadv_net['rx_bytes'])))
            res.append(Metric(metric_name="network_tx_" + nets[ip], value=int(cadv_net['tx_bytes'])))
        return res

    def get_ips_to_networks_dict(self, container):
        nets = {}
        for network in container.attrs["NetworkSettings"]["Networks"]:
            ip = get_ip_from_network_object(container.attrs["NetworkSettings"]["Networks"][network])
            nets[ip] = network
        return nets

    def start_monitoring(self, agent_ip, connector, interval):
        self.shoud_run = True
        logger.info("Monitoring Agent Instantiation")
        cAdvisor_handler = cAdvisorHandler(agent_ip, '9090', 'fogify')
        while (self.shoud_run):
            count = Status.query.filter_by(name="counter").first()
            count = 0 if count is None else int(count.value)
            count += 1
            cAdvisor_handler.retrieve_docker_metrics()
            metrics = cAdvisor_handler.get_metrics()
            self.store_metrics(cAdvisor_handler, connector, count, metrics)
            Status.update_config(str(count))
            sleep(interval)

    def start_monitoring_thread(self, agent_ip, connector, interval):
        self.running_thread = AsyncTask(self, 'start_monitoring', [agent_ip, connector, interval])
        self.running_thread.start()

    def stop_running_thread(self):
        if self.running_thread:
            self.shoud_run = False
            self.running_thread.stop()

    def store_metrics(self, cAdvisor_handler, connector, count, metrics):
        for i in metrics:
            try:
                current_instance = metrics[i]
                cAdvisor_handler.set_current_instance(metrics[i])
                alias = cAdvisor_handler.return_project_alias()
                if not alias: continue

                instance_name = connector.instance_name(alias)

                cAdvisor_handler.set_current_instance_name(instance_name)

                r = Record(timestamp=p.parse(cAdvisor_handler.get_last_stats_timestamp()), count=count,
                           instance_name=instance_name)

                r.metrics.extend(self.get_default_metrics(cAdvisor_handler))
                r.metrics.extend(self.get_network_metrics(cAdvisor_handler))
                r.metrics.extend(self.get_custom_metrics(current_instance, connector))

                db.session.merge(r)
                db.session.commit()
            except Exception:
                logger.warning("An error occurred in monitoring agent. The metrics will not be stored at this time.",
                              exc_info=True)
                continue
