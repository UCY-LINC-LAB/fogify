import os

from flask_sqlalchemy import SQLAlchemy


class Controller(object):
    """ The Controller includes essential functionalities of the controller API"""

    db = None

    def __init__(self, args, app):
        """
        It instantiates the Controller server
        :param args:
        :param app:
        """
        db_path = os.getcwd() + '/master_database.db'

        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_path
        self.args = args
        Controller.db = SQLAlchemy(app)
        if os.path.exists(db_path): os.remove(db_path)
        os.mknod(db_path)

        app.config['UPLOAD_FOLDER'] = "/current_infrastructure/"
        os.environ['UPLOAD_FOLDER'] = "/current_infrastructure/"

        from controller.views import TopologyAPI, \
            MonitoringAPI, \
            ActionsAPI, \
            ControlAPI, \
            AnnotationAPI, \
            DistributionAPI, \
            SnifferAPI

        # Introduce the routes of the API
        app.add_url_rule('/topology/', view_func=TopologyAPI.as_view('Topology'))
        app.add_url_rule('/monitorings/', view_func=MonitoringAPI.as_view('Monitoring'))
        app.add_url_rule('/packets/', view_func=SnifferAPI.as_view('Packets'))
        app.add_url_rule('/annotations/', view_func=AnnotationAPI.as_view('Annotations'))
        app.add_url_rule('/actions/<string:action_type>/', view_func=ActionsAPI.as_view('Action'))
        app.add_url_rule('/control/<string:service>/', view_func=ControlAPI.as_view('control'))
        app.add_url_rule('/generate-network-distribution/<string:name>/',
                         view_func=DistributionAPI.as_view('NetworkDistribution'))
        # from .models import Status
        # Status.update_config(self.initiate_swarm_manager(), "swarm-ca")
        # app.run(debug=False, host='0.0.0.0')
        self.app = app