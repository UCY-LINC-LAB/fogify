import os

import requests
from flask_sqlalchemy import SQLAlchemy
import subprocess

from utils.general import AsyncTask
from utils.network import NetworkController


class Agent(object):
    """ The agent class that includes essential functionalities, namely,
   the agent's API, monitoring thread and docker's listener"""

    db = None

    # TODO build automatically the docker swarm cluster
    # def initiate_swarm_worker(self):
    #    action_url = 'http://%s:5000/control/' % os.environ['CONTROLLER_IP'] if 'CONTROLLER_IP' in os.environ else '0.0.0.0'
    #    command = requests.get(action_url, headers={'Content-Type': "application/json"})["swarm-ca"]
    #    print(subprocess.getoutput(command))

    def __init__(self, args, app):
        """
        It instantiates the agent and starts the API server
        :param args:
        :param app:
        """
        db_path = os.getcwd() + '/agent_database.db'

        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path

        Agent.db = SQLAlchemy(app)
        if os.path.exists(db_path):
            os.remove(db_path)
        os.mknod(db_path)

        app.config['UPLOAD_FOLDER'] = "/current_agent/"
        if not os.path.exists(os.getcwd() + app.config['UPLOAD_FOLDER']):
            os.mkdir(os.getcwd() + app.config['UPLOAD_FOLDER'])
        from utils.monitoring import MetricCollector
        from agent.views import MonitoringAPI, ActionAPI, TopologyAPI, DistributionAPI

        # Add the api routes
        app.add_url_rule('/topology/', view_func=TopologyAPI.as_view('Topology'))
        app.add_url_rule('/monitorings/', view_func=MonitoringAPI.as_view('Monitoring'))
        app.add_url_rule('/actions/', view_func=ActionAPI.as_view('Action'))
        app.add_url_rule('/generate-network-distribution/<string:name>/',
                         view_func=DistributionAPI.as_view('NetworkDistribution'))

        # The thread that runs the monitoring agent
        metricController = MetricCollector()
        metricControllerTask = AsyncTask(metricController, 'save_metrics', [
            args.agent_ip])
        metricControllerTask.start()

        # The thread that inspect containers and apply network QoS
        networkController = NetworkController()
        networkControllerTask = AsyncTask(networkController, 'submition',
                                          [os.getcwd() + app.config['UPLOAD_FOLDER']])
        networkControllerTask.start()

        # Starts the server
        app.run(debug=False, host='0.0.0.0', port=5500)

        self.args = args
