class BaseAction(object):

    def get_command(self):
        pass

    def __str__(self):
        return self.get_command()


class CommandAction(object):
    """
    With this action, users can inject terminal commands to their services
    """

    def __init__(self, command):
        self.command = command

    def get_command(self):
        return self.command


class VerticalScalingAction(BaseAction):
    """ Translates the vertical action model to Fogify agent's vertical scaling primitives """

    def __init__(self, action, value):
        self.action = action
        self.value = value

    def get_command(self):
        return str(self.action).upper()

    def get_value(self):
        return self.value


class StressAction(BaseAction):
    """ Translates the stress actions to Fogify agent's stress commands. Agents will execute these commands in the containers """

    def __init__(self, cpu=None, io=None, vm=None, vm_bytes=None, duration='1s'):
        self.cpu = cpu
        self.io = io
        self.vm = vm
        self.vm_bytes = vm_bytes
        self.timeout = duration

    def get_command(self, cpus):
        import math
        res = "cpulimit --limit {limit} -i -- stress "
        if self.cpu is not None:
            res = res.format(limit=cpus * self.cpu)
            res += " --cpu %s" % math.ceil(cpus)
        if self.io is not None:
            res = res.format(limit=cpus * self.io)
            res += " --io %s" % math.ceil(cpus)
        if self.vm is not None:
            res = res.format(limit=cpus * self.vm)
            res += " --vm %s" % math.ceil(cpus)
        if self.vm_bytes is not None:
            res += " --vm-bytes %s" % self.vm_bytes
        res += " --timeout %s" % self.timeout if self.timeout is not None else ''
        return res


class NetworkAction(BaseAction):
    """ Translates the network alteration model to Fogify agent's network primitives """

    def __init__(self, bandwidth=None, latency={}, drop=None, **kwargs):
        self.bandwidth = bandwidth
        self.latency = latency
        self.drop = drop

    def get_command(self):
        res = ""
        if self.latency != {}:
            if 'delay' in self.latency:

                res += " delay %s " % self.latency['delay']
                res += " %s " % self.latency['deviation'] if 'deviation' in self.latency else ""
                if 'correlation' in self.latency:
                    res += " %s" % self.latency['correlation']
                    res += "% " if not self.latency['correlation'].replace(" ", "").endswith("%") else " "
        res += " rate %s " % self.bandwidth if self.bandwidth else ""
        res += " loss %s " % self.drop if self.drop else ""
        return res

