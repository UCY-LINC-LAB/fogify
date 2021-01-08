from .ClusterConnectors import *


def get_connector_class() -> BasicConnector:
    connector_class = os.environ['CONNECTOR'] if 'CONNECTOR' in os.environ else 'SwarmConnector'
    print("CONNECTOR CLASS: ", connector_class)
    ConnectorClass = getattr(ClusterConnectors, connector_class, getattr(ClusterConnectors, 'SwarmConnector'))
    print("CLASS OBJECT: ", ConnectorClass)
    return ConnectorClass
