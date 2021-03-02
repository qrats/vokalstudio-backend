"""Episodes  models and database functionality"""
from src.services.db import db
from datetime import datetime
from src.models.users import UserModel


class EpisodesModel(db.Model):
    __tablename__ = "episodes"

    id = db.Column(db.String(256), primary_key=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    title = db.Column(db.String(256), nullable=False)
    description = db.Column(db.String(4096), nullable=True)
    url = db.Column(db.String(1024), nullable=True)
    image = db.Column(db.String(1024), nullable=True)
    type = db.Column(db.String(256), nullable=True, default='video')  # [video, audio]
    status = db.Column(db.String(256), nullable=True, default='pending')  # [live, pending]
    premium = db.Column(db.Boolean, nullable=True, default=False)
    duration = db.Column(db.Time, nullable=True, default=None)
    views = db.Column(db.Integer, nullable=True, default=0)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    uploader = db.relationship(UserModel, foreign_keys=uploader_id, cascade="all,delete")

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.id} ({self.title}), role: {self.url}>"

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
