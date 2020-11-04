import subprocess
from time import sleep
import docker
import dateutil.parser as p
import requests
from os.path import exists
import json

from agent.models import Status, Metric, db, Record
from utils import DockerManager
from utils.DockerManager import get_container_ip_property


class MetricCollector(object):

    def custom_metrics(self, container_id):
        path = DockerManager.get_host_data_path(container_id)
        res = {}
        if path and exists(path + "/fogify/metrics"):
            with open(path + "/fogify/metrics") as json_file:
                data = json.load(json_file)
                try:
                    res = {i: float(data[i]) for i in data}
                except Exception as ex:
                    pass
        return res

    def save_metrics(self, agent_ip="localhost"):
        interval = 5
        machine = requests.get("http://%s:9090/api/v1.3/machine" % agent_ip).json()
        print("Monitoring Agent Instantiation")

        def millis_interval(start, end):
            """start and end are datetime instances"""
            diff = end - start
            millis = diff.days * 24 * 60 * 60 * 1000
            millis += diff.seconds * 1000
            millis += diff.microseconds / 1000
            return millis

        while (True):

            count = Status.query.filter_by(name="counter").first()
            if count is None:
                count = 0
            else:
                count = int(count.value)

            docker_instances = requests.get("http://%s:9090/api/v1.3/docker/" % agent_ip).json()
            for i in docker_instances:
                try:
                    instance = docker_instances[i]
                    is_fogified = False
                    for alias in instance['aliases']:
                        if alias.startswith('fogify_'):
                            is_fogified = True
                            break
                    if is_fogified:
                        instance_name = alias[len("fogify_"):alias.rfind(".")]

                        record = Record.query.filter_by(instance_name=instance_name).order_by(
                            Record.count.desc()).limit(1).first()
                        last_cpu_record = None
                        if record:
                            for i in record.metrics:
                                if i.metric_name == 'cpu':
                                    last_cpu_record = i
                                    break
                        last_stat = instance['stats'][-1]

                        r = Record()
                        r.timestamp = p.parse(last_stat['timestamp'])
                        r.count = count
                        r.instance_name = instance_name
                        cpu_specs = instance['spec']['cpu']
                        mem_specs = instance['spec']['memory']['limit']
                        if last_cpu_record:
                            timedif = abs(millis_interval(r.timestamp.replace(tzinfo=None),
                                                          record.timestamp.replace(tzinfo=None)))
                            rate = (float(last_stat['cpu']['usage']['total']) - float(last_cpu_record.value)) / timedif
                            cpu_util_val = rate / (float(cpu_specs['quota']) / float(cpu_specs['period']))
                            cpu_util_val /= 10000
                        else:
                            cpu_util_val = 0
                        cpu_util = Metric(
                            metric_name="cpu_util",
                            value=float(cpu_util_val)
                        )
                        cpu = Metric(
                            metric_name="cpu",
                            value=float(last_stat['cpu']['usage']['total'])
                        )
                        memory = Metric(
                            metric_name="memory",
                            value=float(last_stat['memory']['usage'])
                        )
                        memory_util_val = float(last_stat['memory']['usage']) / float(mem_specs)
                        memory_util = Metric(
                            metric_name="memory_util",
                            value=memory_util_val
                        )
                        disk = Metric(
                            metric_name="disk_bytes",
                            value=float(last_stat['filesystem'][0]['usage'])
                        )
                        r.metrics.append(disk)
                        r.metrics.append(memory_util)
                        r.metrics.append(cpu)
                        r.metrics.append(cpu_util)
                        r.metrics.append(memory)

                        client = docker.from_env()
                        container = client.containers.get(instance["id"])
                        for cadv_net in last_stat['network']['interfaces']:
                            conf = Status.query.filter_by(name=instance["id"] + "|" + cadv_net["name"]).first()

                            if conf is None:
                                eth_ip = get_container_ip_property(instance["id"], cadv_net["name"])
                                ip = eth_ip[eth_ip.find("inet ") + len("inet "):eth_ip.rfind("/")]

                                Status.update_config(ip, instance["id"] + "|" + cadv_net["name"])
                            else:
                                ip = conf.value

                            nets = {container.attrs["NetworkSettings"]["Networks"][network]['IPAMConfig'][
                                        'IPv4Address']: network
                                    for network in container.attrs["NetworkSettings"]["Networks"]}

                            if ip in nets and nets[ip] != 'ingress':
                                net_in = Metric(metric_name="network_rx_" + nets[ip], value=int(cadv_net['rx_bytes']))

                                r.metrics.append(net_in)

                                net_out = Metric(
                                    metric_name="network_tx_" + nets[ip],
                                    value=int(cadv_net['tx_bytes'])
                                )
                                r.metrics.append(net_out)
                        cust_met = self.custom_metrics(instance['id'])
                        for custom_metric in cust_met:
                            cust_met_val = Metric(
                                metric_name=custom_metric,
                                value=float(cust_met[custom_metric])
                            )
                            r.metrics.append(cust_met_val)
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
