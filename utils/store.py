import json
import os
import time
from collections import deque

from agent.models import Packet,  db


class DummyStorage(object):

    def __init__(self, buffer: deque):
        self.buffer = buffer

    # Sniffs and stores the traffic
    def store_data(self):
        count = 0
        while True:
            if len(self.buffer) > 0:
                obj = self.buffer.pop()
                if obj:
                    db.session.add(Packet(**obj))
            else:
                time.sleep(1)
            if count == 10:
                count=0
                db.session.commit()
            else:
                count+=1
