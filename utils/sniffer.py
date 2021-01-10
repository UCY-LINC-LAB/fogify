import argparse
import fcntl
import socket
import struct
import textwrap
from collections import deque

import netifaces as ni
import time
from collections import deque
from datetime import datetime
from agent.models import Packet, db
buffer = deque()


class Sniffer(object):

    def __init__(self, buffer: deque, id_prefix=""):
        self.buffer = buffer
        self.id_prefix = id_prefix

    # Unpacks ethernet frame
    def ethernet_frame(self, data_tuple):
        dest_mac, src_mac, proto = struct.unpack('! 6s 6s H', data_tuple[0][:14])
        return len(data_tuple[0]), data_tuple[1][0], self.get_mac_addr(dest_mac), self.get_mac_addr(
            src_mac), socket.htons(proto), data_tuple[0][14:]

    # fromats mac address
    def get_mac_addr(self, byte_addr):
        bytes_str = map('{:02x}'.format, byte_addr)
        return ':'.join(bytes_str).upper()

    # Unpacks IPv4 packet
    def ipv4_packet(self, data):
        version_header_length = data[0]
        version = version_header_length >> 4
        header_length = (version_header_length & 15) * 4
        ttl, proto, src, target = struct.unpack("! 8x B B 2x 4s 4s", data[:20])
        return version, header_length, ttl, proto, self.ipv4(src), self.ipv4(target), data[header_length:]

    # Returns properly formatted IPv4 address
    def ipv4(self, addr):
        return ".".join(map(str, addr))

    # Unpacks ICMP packet
    def icmp_packet(self, data):
        icmp_type, code, checksum = struct.unpack("! B B H", data[:4])
        return icmp_type, code, checksum, data[4:]

    # Unpacks TCP segment
    def tcp_segment(self, data):
        (src_port, dest_port, sequence, acknowledgement, offset_reserved_flags) = struct.unpack('! H H L L H',
                                                                                                data[:14])
        offset = (offset_reserved_flags >> 12) * 4
        flag_urg = (offset_reserved_flags & 32) >> 5
        flag_ack = (offset_reserved_flags & 16) >> 4
        flag_psh = (offset_reserved_flags & 8) >> 3
        flag_rst = (offset_reserved_flags & 4) >> 2
        flag_syn = (offset_reserved_flags & 2) >> 1
        flag_fin = offset_reserved_flags & 1
        return src_port, dest_port, sequence, acknowledgement, flag_urg, flag_ack, flag_psh, flag_rst, flag_syn, flag_fin, data[
                                                                                                                           offset:]

    # Unpacks UDP segment
    def udp_segment(self, data):
        src_port, dest_port, size = struct.unpack('! H H 2x H', data[:8])
        return src_port, dest_port, size, data[8:]

    # Formats multi-line data
    def format_multi_line(self, prefix, string, size=80):
        size -= len(prefix)
        if isinstance(string, bytes):
            string = ''.join(r'\x{:02x}'.format(byte) for byte in string)
            if size % 2:
                size -= 1
        return '\n'.join([prefix + line for line in textwrap.wrap(string, size)])

    # Returns my global IP
    def get_my_macs(self):
        nic = ni.interfaces()
        mac_addresses = []
        for item in nic:
            try:
                mac = str(ni.ifaddresses(str(item))[ni.AF_LINK][0]['addr']).upper()
                mac_addresses.append(mac)
            except Exception as e:
                print(e)
        return mac_addresses

    def sniff(self):
        conn = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(3))
        mac_addresses = self.get_my_macs()
        while True:
            raw_data, address = conn.recvfrom(65535)
            packet = self.create_packet(raw_data, address, mac_addresses)
            if packet is not None:
                self.buffer.appendleft(
                    packet
                )

    def create_packet(self, raw_data, address, mac_addresses):

        s, network_interface, dest_mac, src_mac, eth_proto, data = self.ethernet_frame((raw_data, address))

        # Skip non selected network interfaces
        if network_interface == 'lo':
            return None

        # pid is also a counter
        is_outgoing = (str(src_mac) in mac_addresses)
        src_ip, dest_ip, src_port, dest_port, size, payload = None, None, None, None, None, None
        # 8 for IPv4
        if eth_proto == 8:
            version, header_length, ttl, proto, src_ip, dest_ip, data = self.ipv4_packet(data)

            # 6 for TCP
            if proto == 6:
                src_port, dest_port, sequence, acknowledgement, flag_urg, flag_ack, flag_psh, flag_rst, flag_syn, flag_fin, payload = self.tcp_segment(
                    data)
                protocol = "TCP"


            # 17 for UDP
            elif proto == 17:
                src_port, dest_port, size, payload = self.udp_segment(data)
                protocol = "UDP"


            # 1 for ICMP
            elif proto == 1:
                icmp_type, code, checksum, payload = self.icmp_packet(data)
                protocol = "ICMP"


        else:
            protocol = str(eth_proto)
            return None

        return {
            "packet_id": self.id_prefix,
            "network_interface": network_interface,
            "src_mac": src_mac,
            "dest_mac": dest_mac,
            "src_ip": src_ip,
            "dest_ip": dest_ip,
            "src_port": src_port,
            "dest_port": dest_port,
            "protocol": protocol,
            "size": len(payload) if payload else size,
            "out": is_outgoing
        }

        # outbound_traffic.appendleft(x) if out else inbound_traffic.appendleft(x)
        # update_json(x, OUTBOUND) if out else update_json(x, INBOUND)

    def get_ip_address(self, ifname):
        s = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(3))
        return socket.inet_ntoa(fcntl.ioctl(s.fileno(), bytes(0x8915), struct.pack('256s', ifname[:15]))[20:24])

    def controller(self):
        parser = argparse.ArgumentParser(fromfile_prefix_chars='=', add_help=False)
        parser.add_argument('-ni', '--network-interface', action='store_true')
        parser.add_argument('--help', action='store_true', dest='help')
        known, unknown = parser.parse_known_args()
        return known, unknown

    def check_unknown_flags(self, unknown):
        unknown_flags = []
        for item in unknown:
            if item[0] == "-":
                unknown_flags.append(item)
        return unknown_flags

    def check_interfaces(self, selected_interfaces):
        nic = ni.interfaces()
        for i in selected_interfaces:
            if i not in nic:
                print("Interface", i, "does not exist")
                quit()

    def display_info(self):
        nic = ni.interfaces()
        for item in nic:
            try:
                print("Network interface:", str(item))
                print("IP in", item, "network interface:", ni.ifaddresses(str(item))[ni.AF_INET][0]['addr'])
                print("MAC in", item, "network interface:", ni.ifaddresses(str(item))[ni.AF_LINK][0]['addr'])
                print("--------------\n")
            except Exception as e:
                print(e)


class SniffingStorage(object):

    def __init__(self, buffer: deque, periodicity: int):
        self.buffer = buffer
        self.ip_to_info = {}
        self.periodicity = periodicity if periodicity is not None else 15

    # Sniffs and stores the traffic
    def store_data(self):
        delay = 0

        while True:
            if delay > 0:
                time.sleep(delay)
            res = {}
            start = datetime.now()
            while len(self.buffer) > 0:
                obj = self.buffer.pop()
                if obj is not None:

                    key = "%s|%s|%s|%s|%s" % (obj["packet_id"],
                                              obj["src_ip"],
                                              obj["dest_ip"],
                                              obj["protocol"],
                                              obj["out"]
                                              )

                    if key not in res:
                        res[key] = {
                            "count": 0,
                            "size": 0
                        }
                    res[key]["count"] += 1
                    res[key]["size"] += int(obj["size"]) if obj["size"] else 0
                obj = None
            new_res = []
            for i in res:
                vals = i.split("|")
                new_res.append(Packet(
                    service_id=vals[0],
                    src_ip=vals[1],
                    dest_ip=vals[2],
                    protocol=vals[3],
                    out=vals[4].lower() == 'true',
                    timestamp=datetime.now(),
                    size=res[i]["size"],
                    count=res[i]["count"],
                ))
            db.session.bulk_save_objects(new_res)
            db.session.commit()

            end = datetime.now()
            delay = self.periodicity - (end - start).total_seconds()
