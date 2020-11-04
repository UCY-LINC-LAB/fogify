from enum import Enum
from datetime import datetime
from controller.controller import Controller

db = Controller.db

class Status(db.Model):
    """
    This class saves status of crucial parameters of Agent's Execution
    """
    name = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(50))

    @classmethod
    def update_config(cls, value, name="infrastructure"):
        status = Status(name=name, value=value)
        db.session.merge(status)
        db.session.commit()




class Annotation(db.Model):
    """ Model for the annotations. Annotations capture the actions that the Users apply to the Fogify"""
    class TYPES(Enum):
        START = "START"
        DEPLOY = "DEPLOY"
        STOP = "STOP"
        UNDEPLOY = "UNDEPLOY"
        STRESS = "STRESS"
        NETWORK = "NETWORK"
        COMMAND = "COMMAND"
        H_SCALE_UP = "H_SCALE_UP"
        H_SCALE_DOWN = "H_SCALE_DOWN"
        V_SCALE = "V_SCALE"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    instance_name = db.Column(db.String(250), nullable=True)
    timestamp = db.Column(db.DateTime(), default=datetime.now)
    annotation = db.Column(db.String(250))
    params = db.Column(db.String(500), nullable=True)

    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "annotation": self.annotation,
            "instance_name": self.instance_name,
            "params": self.params
        }

    @classmethod
    def create(cls, annotation ,instance_names="Topology", params=None):
        if type(instance_names) == list:
            for i in instance_names:
                a = Annotation(annotation=annotation, instance_name=i, params=params)
                db.session.add(a)
        else:
            a = Annotation(annotation=annotation, instance_name=instance_names, params=params)
            db.session.add(a)
        db.session.commit()

db.create_all()
Status.update_config('available')