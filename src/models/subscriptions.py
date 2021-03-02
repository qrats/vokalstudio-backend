"""Subscriptions models and database functionality"""
from src.services.db import db
from datetime import datetime
from src.models.plans import PlansModel
from src.models.users import UserModel


class SubscriptionsModel(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(db.String(256), primary_key=True)
    sandbox = db.Column(db.Boolean, nullable=False, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    plan_id = db.Column(db.String(256), db.ForeignKey('plans.id'))
    status = db.Column(db.String(256), nullable=False, default="APPROVAL_PENDING")
    subscriber = db.Column(db.JSON, nullable=True)
    billing_info = db.Column(db.JSON, nullable=True)
    plan_overridden = db.Column(db.Boolean, nullable=True, default=False)
    links = db.Column(db.JSON, nullable=True)

    start_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    create_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    plan = db.relationship(PlansModel, foreign_keys=plan_id)
    user = db.relationship(UserModel, foreign_keys=user_id)

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.id} ({self.plan_id})>"

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
        return cls.query.filter(*filters).order_by(cls.create_time.desc()).all()
