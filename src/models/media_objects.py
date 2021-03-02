"""Media objects models and database functionality"""
from src.services.db import db
from datetime import datetime
from src.models.users import UserModel


class MediaObjectsModel(db.Model):
    __tablename__ = "media_objects"

    id = db.Column(db.String(256), primary_key=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    file_name = db.Column(db.String(256), nullable=False)
    description = db.Column(db.String(4096), nullable=True)
    url = db.Column(db.String(1024), nullable=True)
    image = db.Column(db.String(1024), nullable=True)
    type = db.Column(db.String(256), nullable=True, default='video')  # [video, audio]
    duration = db.Column(db.Time, nullable=True, default=None)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    uploader = db.relationship(UserModel, foreign_keys=uploader_id, cascade="all,delete")

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.id} ({self.file_name})>"

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
