"""Subscriptions models and database functionality"""
from src.services.db import db
from datetime import datetime
from src.models.users import UserModel


class PaymentsModel(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.String(256), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    amount = db.Column(db.Float, nullable=False, default=0.0)
    funding_source = db.Column(db.String(256), nullable=False, default='paypal')
    invoice_id = db.Column(db.String(256), nullable=True)
    product = db.Column(db.JSON, nullable=True)
    payer = db.Column(db.JSON, nullable=True)

    create_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship(UserModel, foreign_keys=user_id, cascade="all,delete")

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.id} ({self.amount})>"

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
        return cls.query.filter(*filters).all()
