from sqlalchemy import Index
from sqlalchemy.orm import relationship

from .agent import Agent

db = Agent.db


class Status(db.Model):
    """
    This class saves status of crucial parameters of Agent's Execution
    """
    name = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.String(50))

    @classmethod
    def update_config(cls, value, name="counter"):
        status = Status(name=name, value=value)
        db.session.merge(status)
        db.session.commit()


class Metric(db.Model):
    """
    Metric is combination of a metric name and a measurement at a specific timestamp
    """
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    metric_name = db.Column(db.String(250))
    value = db.Column(db.Float())
    record_id = db.Column(db.Integer, db.ForeignKey('record.id'))


class Packet(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    service_id = db.Column(db.String(250))
    src_ip = db.Column(db.String(250))
    dest_ip = db.Column(db.String(250))
    protocol = db.Column(db.String(250))
    size = db.Column(db.Integer())
    count = db.Column(db.Integer())
    out = db.Column(db.Boolean())
    timestamp = db.Column(db.DateTime())


class Record(db.Model):
    """
    It represents the monitoring measurement. A measurement is connected with multiple Records.
    """
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    instance_name = db.Column(db.String(250))
    timestamp = db.Column(db.DateTime())
    metrics = relationship("Metric", backref='record')
    count = db.Column(db.Integer())
    __table_args__ = (
        db.Index('timestamp_service', timestamp.desc(), instance_name),
    )

    def get_metric_by_name(self, name: str) -> Metric:
        for i in self.metrics:
            if i.metric_name == name:
                return i

db.create_all()
