from time import sleep

import requests
import os
def get_random_metrics(data_size=10, filesize=1000000, file="/data/yellow_tripdata_2018-01.csv"):
    import random
    data = []
    f = open(file, "r")

    offset = random.randrange(filesize)
    f.seek(offset)  # go to random position


    for i in range(0,data_size):
        f.readline()  # discard - bound to be partial line
        random_line = f.readline()
        data+=[random_line]

    f.close()
    return data
service_to_network = {
'mec-svc-1': 'edge-net-1', 'mec-svc-2': 'edge-net-2'
}

def propagate_to_edge(data):
    sent = False
    for fog_node in ['mec-svc-1', 'mec-svc-2']:
        try:
            requests.post("http://tasks.%s.%s:8000/"%(fog_node, service_to_network[fog_node]), data=str(data), timeout=10)
            sent = True
            break
        except:
            continue
    if not sent:
        try:
            requests.post("http://tasks.cloud-server.internet:8000/", data=str(data))
        except Exception as e:
            print(e)
            print("data is lost")
            # sleep(5)
            # propagate(data=data)


def propagate(data):
    try:
        requests.post("http://tasks.cloud-server.internet:8000/", data=str(data))
    except Exception as e:
        print(e)
        print("data is lost")
        sleep(5)
        propagate(data=data)
