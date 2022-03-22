import os

from . import materialized_connectors
from .base import BasicConnector


def get_connector_class():
    connector_class = os.environ['CONNECTOR'] if 'CONNECTOR' in os.environ else 'SwarmConnector'
    connector_class = getattr(materialized_connectors, connector_class,
                              getattr(materialized_connectors, 'SwarmConnector'))
    return connector_class


def get_connector(**kwargs) -> BasicConnector:
    default_params = dict(model=None,
        path=os.getcwd() + os.environ['UPLOAD_FOLDER'] if 'UPLOAD_FOLDER' in os.environ else "",
        frequency=float(os.environ['CPU_FREQ']) if 'CPU_FREQ' in os.environ else 2400.0, cpu_oversubscription=float(
            os.environ['CPU_OVERSUBSCRIPTION_PERCENTAGE']) if 'CPU_OVERSUBSCRIPTION_PERCENTAGE' in os.environ else 0.0,
        ram_oversubscription=float(
            os.environ['RAM_OVERSUBSCRIPTION_PERCENTAGE']) if 'RAM_OVERSUBSCRIPTION_PERCENTAGE' in os.environ else 0.0,
        node_name=os.environ['MANAGER_NAME'] if 'MANAGER_NAME' in os.environ else 'localhost',
        host_ip=os.environ['HOST_IP'] if 'HOST_IP' in os.environ else None)
    default_params.update(kwargs)
    return get_connector_class()(**default_params)
