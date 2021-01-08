import json
import os
import time
from collections import deque
from datetime import datetime

from agent.models import Packet, db, Status


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
                    # src_port=vals[3],
                    # dest_port=vals[4],
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
