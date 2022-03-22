import os
import threading
import time
from collections import deque
from datetime import datetime

import pyshark

from utils.docker_manager import ContainerNetworkNamespace

buffer = deque()


class SnifferHandler(object):

    def __init__(self, buffer: deque = None,
            periodicity=int(os.environ['SNIFFING_PERIODICITY']) if 'SNIFFING_PERIODICITY' in os.environ and os.environ[
                'SNIFFING_PERIODICITY'].isnumeric() else 15, ):
        self.periodicity = periodicity
        self.buffer = buffer if buffer is not None else deque()

    def start_thread_for_sniffing_storage(self):
        storage = SniffingStorage(self.buffer, self.periodicity)
        t2 = threading.Thread(target=storage.store_data)
        t2.start()

    def start_thread_for_sniffing(self, container_id, container_name, eth, network):
        def network_sniffing(_buffer, container_id, container_name, eth, network):
            with ContainerNetworkNamespace(container_id):
                sniffer = Sniffer(_buffer, container_name, eth, network)
                sniffer.sniff()

        threading.Thread(target=network_sniffing,
                         args=(self.buffer, container_id, container_name, eth, network)).start()


class Sniffer(object):

    def __init__(self, buffer: deque, id_prefix="", eth="", network=""):
        self.buffer = buffer  # capture = pyshark.LiveCapture(interface=
        self.id_prefix = id_prefix
        self.eth = eth
        self.network = network

    def sniff(self):
        capture = pyshark.LiveCapture(self.eth)

        for packet in capture.sniff_continuously():
            # adjusted output
            try:
                # get timestamp
                # get packet content
                protocol = packet.transport_layer  # protocol type
                src_addr = packet.ip.src  # source address
                src_port = packet[protocol].srcport  # source port
                dst_addr = packet.ip.dst  # destination address
                dst_port = packet[protocol].dstport  # destination port
                src_mac = packet.eth.src  # destination
                dst_mac = packet.eth.dst  # destination
                size = packet.ip.len
                packet = {"packet_id": self.id_prefix, "network_interface": self.eth, "src_mac": src_mac,
                    "dest_mac": dst_mac, "src_ip": src_addr, "dest_ip": dst_addr, "src_port": src_port,
                    "dest_port": dst_port, "protocol": protocol, "size": size, "network": self.network}
                if packet is not None:
                    self.buffer.appendleft(packet)
            except AttributeError:
                # ignore packets other than TCP, UDP and IPv4
                pass


class SniffingStorage(object):

    def __init__(self, buffer: deque, periodicity: int):
        self.buffer = buffer
        self.ip_to_info = {}
        self.periodicity = periodicity if periodicity is not None else 15

    def retrieve_packets_from_buffer(self):
        res = {}
        while len(self.buffer) > 0:
            obj = self.buffer.pop()
            if obj is not None:
                key = "%s|%s|%s|%s|%s|%s|%s" % (
                    obj["packet_id"], obj["src_ip"], obj["dest_ip"], obj["protocol"], obj["network"], obj["src_port"],
                    obj["dest_port"])

                if key not in res:
                    res[key] = {"count": 0, "size": 0}
                res[key]["count"] += 1
                res[key]["size"] += int(obj["size"]) if obj["size"] else 0
        return res

    def save_packets_to_db(self, res: {}):
        from agent.models import Packet, db
        new_res = []
        for i in res:
            vals = i.split("|")
            new_res.append(
                Packet(service_id=vals[0], src_ip=vals[1], dest_ip=vals[2], protocol=vals[3], network=vals[4],
                    src_port=vals[5], dest_port=vals[6], timestamp=datetime.now(), size=res[i]["size"],
                    count=res[i]["count"], ))
        db.session.bulk_save_objects(new_res)
        db.session.commit()

    # Sniffs and stores the traffic
    def store_data(self):
        delay = 0

        while True:
            if delay > 0:
                time.sleep(delay)
            start = datetime.now()

            res = self.retrieve_packets_from_buffer()

            self.save_packets_to_db(res)

            end = datetime.now()
            delay = self.periodicity - (end - start).total_seconds()
