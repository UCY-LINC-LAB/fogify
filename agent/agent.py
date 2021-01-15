import os

from flask_sqlalchemy import SQLAlchemy

from connectors import get_connector
from utils.async_task import AsyncTask
from utils.network import NetworkController



class Agent(object):
    """ The agent class that includes essential functionalities, namely,
   the agent's API, monitoring thread and docker's listener"""

    db = None

    def __init__(self, args, app):
        """
        It instantiates the agent and starts the API server
        :param args:
        :param app:
        """
        db_path = os.getcwd() + '/agent_database.db'

        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path

        Agent.db = SQLAlchemy(app)
        if os.path.exists(db_path): os.remove(db_path)
        os.mknod(db_path)

        app.config['UPLOAD_FOLDER'] = "/current_agent/"
        os.environ['UPLOAD_FOLDER'] = "/current_agent/"
        if not os.path.exists(os.getcwd() + app.config['UPLOAD_FOLDER']):
            os.mkdir(os.getcwd() + app.config['UPLOAD_FOLDER'])

        connector = get_connector()
        app.config['CONNECTOR'] = connector
        node_labels = {}

        if 'LABELS' in os.environ:
            node_labels = {i.split(":")[0]: i.split(":")[1]
                           for i in os.environ['LABELS'].split(",") if len(i.split(":")) == 2}

        connector.inject_labels(node_labels, HOST_IP=os.environ['HOST_IP'] if 'HOST_IP' in os.environ else None)

        from utils.monitoring import MetricCollector
        from agent.views import MonitoringAPI, ActionsAPI, TopologyAPI, DistributionAPI, SnifferAPI

        # Add the api routes
        app.add_url_rule('/topology/', view_func=TopologyAPI.as_view('Topology'))
        app.add_url_rule('/monitorings/', view_func=MonitoringAPI.as_view('Monitoring'))
        app.add_url_rule('/actions/', view_func=ActionsAPI.as_view('Action'))
        app.add_url_rule('/packets/', view_func=SnifferAPI.as_view('Packet'))
        app.add_url_rule('/generate-network-distribution/<string:name>/',
                         view_func=DistributionAPI.as_view('NetworkDistribution'))

        # The thread that runs the monitoring agent
        metricController = MetricCollector()
        metricControllerTask = AsyncTask(metricController, 'save_metrics', [args.agent_ip, connector])
        metricControllerTask.start()

        # The thread that inspect containers and apply network QoS
        networkController = NetworkController(connector)
        networkControllerTask = AsyncTask(networkController, 'listen', [])
        networkControllerTask.start()

        # Starts the server
        app.run(debug=False, host='0.0.0.0', port=5500)

        self.args = args
