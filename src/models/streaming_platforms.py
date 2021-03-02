"""Streaming models and database functionality"""
from src.services.db import db
from datetime import datetime
from src.models.users import UserModel


class StreamingPlatformsModel(db.Model):
    __tablename__ = "streaming_platforms"

    id = db.Column(db.String(256), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    active = db.Column(db.Boolean, nullable=True)
    service = db.Column(db.String(256), nullable=True)
    service_email = db.Column(db.String(256), nullable=True)
    image = db.Column(db.String(256), nullable=True)
    stream_key = db.Column(db.String(256), nullable=True)
    ingestion_address = db.Column(db.String(256), nullable=True)
    channel_id = db.Column(db.String(256), nullable=False, default=None)
    channel_name = db.Column(db.String(256), nullable=False, default=None)
    title = db.Column(db.String(256), nullable=True)
    description = db.Column(db.String(4096), nullable=True)
    refresh_token = db.Column(db.String(1024), nullable=True)
    extra = db.Column(db.JSON, nullable=True)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship(UserModel, foreign_keys=user_id, cascade="all,delete")

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.id}>"

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
