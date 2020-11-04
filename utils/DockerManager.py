import json
import subprocess


def get_host_data_path(container_id):
    try:
        return subprocess.getoutput(
            "docker inspect --format='{{.GraphDriver.Data.MergedDir}}' %s" % container_id)
    except Exception:
        return None

def get_pid_from_container(container_id):
    try:
        res = subprocess.getoutput(
            "docker inspect %s --format '{{.State.Pid}}' " % container_id)
        if res.split(" ")[-1].startswith("State"):
            raise Exception("Failure due to the state of the container", res)
        return res
    except Exception as ex:
        print(ex)

def get_container_ip_property(container_id, property):
    container = get_pid_from_container(container_id)
    pid = get_pid_from_container(container).split(" ")[-1]
    eth = subprocess.check_output(
        ['/bin/sh', '-c', 'nsenter -t %s -n ip a | grep %s | tail -n 1' % (pid, property)]).decode()
    return eth
def get_containers_adapter_for_network(container_id, network):
    try:
        networks = json.loads(subprocess.getoutput(
            "docker inspect --format='{{json .NetworkSettings.Networks}}' %s"%container_id))
        if network in networks:
            ip = networks[network]['IPAMConfig']['IPv4Address']
        # container = client.containers.get(container_id)
        eth = get_container_ip_property(container_id, ip).split()[-1]
        return eth
    except Exception as ex:
        print(ex)


def get_ips_for_service(service):
    # TODO refactoring
    if not service.startswith("fogify_"):
        service="fogify_"+service
    res = [json.loads(s) for s in subprocess.getoutput("""docker stack ps -f "desired-state=running" --format '{ "{{.Name}}": "{{.ID}}" }' fogify""").split("\n")]

    temp = []
    for i in res:
        for j in i:
            if j.startswith(service):
                temp.append(i[j])
    res={}
    for i in temp:
        nets = json.loads(subprocess.getoutput("""docker inspect --format='{{json .NetworksAttachments}}' %s""" %i))
        nets = nets if nets else []
        for net in nets:
            net_name = net['Network']['Spec']['Name']
            addresses = net['Addresses']
            if net_name not in res:
                res[net_name]=[]
            res[net_name]+=[address.replace("/24","") for address in addresses]
    return res