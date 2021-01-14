"""Media configuration models and database functionality"""
from src.services.db import db
from datetime import datetime
from src.models.users import UserModel


class MediaConfigurationModel(db.Model):
    __tablename__ = "media_configuration"

    id = db.Column(db.String(256), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    CONFIG_VERSION = db.Column(db.String(256), nullable=False, default="2")
    autoSwitchEnabledAfterInto = db.Column(db.Boolean, nullable=True, default=True)
    autoSwitchMinLevel = db.Column(db.Integer, nullable=False, default=2500)
    intro_host_scene = db.Column(db.String(1024), nullable=True, default="Camera 2")
    intro_mics_fadeIn_time = db.Column(db.Integer, nullable=False, default=1)
    intro_start_delay_after_streaming_start = db.Column(db.Integer, nullable=False, default=4)
    obs_enable_recording = db.Column(db.Boolean, nullable=True, default=True)
    obs_enable_streaming = db.Column(db.Boolean, nullable=True, default=True)
    obs_host = db.Column(db.String(256), nullable=True, default="localhost")
    obs_password = db.Column(db.String(256), nullable=True, default="secret")
    obs_port = db.Column(db.Integer, nullable=False, default=4445)
    obs_profilename = db.Column(db.String(256), nullable=False)
    obs_scenecollectionname = db.Column(db.String(256), nullable=False, default="Vokal Automated Default")
    recording_start_delay = db.Column(db.Integer, nullable=False, default=1)
    show_start_delay = db.Column(db.Integer, nullable=False, default=2)
    time_to_switch_to_intro_with_host = db.Column(db.Integer, nullable=False, default=5)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship(UserModel, foreign_keys=user_id)

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
