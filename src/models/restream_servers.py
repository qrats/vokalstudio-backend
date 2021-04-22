"""RestreamServers models and database functionality"""
from src.services.db import db
from datetime import datetime
from src.models.subscriptions import SubscriptionsModel


class RestreamServersModel(db.Model):
    __tablename__ = "restream_servers"

    id = db.Column(db.String(256), primary_key=True)
    subscription_id = db.Column(db.String(256), db.ForeignKey('subscriptions.id'))
    instance_id = db.Column(db.String(256), nullable=False)
    state = db.Column(db.String(256), nullable=False, default="pending")  # pending/running
    public_ip = db.Column(db.String(256), nullable=True)
    public_dns = db.Column(db.String(256), nullable=True)
    reservation = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    subscription = db.relationship(SubscriptionsModel, foreign_keys=subscription_id)

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.id} ({self.instance_id})>"

    def save(self):
        try:
            db.session.add(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise Exception(e)

    def delete(self):
        try:
            db.session.delete(self)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise Exception(e)

    @classmethod
    def filter_first(cls, filters):
        return cls.query.filter(*filters).first()

    @classmethod
    def filter_all(cls, filters):
        return cls.query.filter(*filters).order_by(cls.created_at.desc()).all()
