import psutil
import cpuinfo

class HostInfo(object):

    @classmethod
    def get_cpu_info(cls):
        res = {}
        info = cpuinfo.get_cpu_info()
        for i in ['bits', 'arch', 'count', 'brand_raw', 'hz_advertised_friendly', 'l3_cache_size', 'l2_cache_size', 'l1_cache_size', 'l1_data_cache_size', 'l1_instruction_cache_size']:
            if i in info:
                res["cpu_"+i] = str(info[i])
        return res

    @classmethod
    def get_sensors(cls):
        sensors = {}
        if hasattr(psutil, "sensors_temperatures") and psutil.sensors_temperatures():
            for i in psutil.sensors_temperatures().keys():
                sensors["sensors_temps."+i] = ""
        if hasattr(psutil, "sensors_fans"):
            for i in psutil.sensors_fans().keys():
                sensors["sensors_fans."+i] = ""

        if hasattr(psutil, "sensors_battery") and psutil.sensors_battery():
            sensors['sensors_battery_percent'] = "%s" % psutil.sensors_battery().percent
            sensors['sensors_battery_plugged'] = "%s" % psutil.sensors_battery().power_plugged

        return sensors

    @classmethod
    def get_disk_usage(cls):
        return {'disk_total': "%s" % int(psutil.disk_usage('/').total / 1073741824),
                'disk_used': "%s" % int(psutil.disk_usage('/').used / 1073741824),
                'disk_free': "%s" % int(psutil.disk_usage('/').free / 1073741824)}

    @classmethod
    def get_memory_usage(cls):
        return {
            'memory_total': "%s" % round(psutil.virtual_memory().total/float(1 << 30), 1),
            'memory_available': "%s" % round(psutil.virtual_memory().available/float(1 << 30), 1)
        }

    @classmethod
    def get_all_properties(cls):
        res = {}
        res.update(HostInfo.get_cpu_info())
        res.update(HostInfo.get_sensors())
        res.update(HostInfo.get_memory_usage())
        res.update(HostInfo.get_disk_usage())
        return res