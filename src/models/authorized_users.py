"""Authorized users models and database functionality"""
from src.services.db import db
from datetime import datetime
from src.models.users import UserModel


class AuthorizedUsersModel(db.Model):
    __tablename__ = "authorized_users"

    id = db.Column(db.String(256), primary_key=True)
    first_name = db.Column(db.String(256), nullable=False)
    last_name = db.Column(db.String(256), nullable=False)
    email = db.Column(db.String(256), nullable=False)
    password = db.Column(db.String(256), nullable=False)

    invited_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    inviter = db.relationship(UserModel, foreign_keys=invited_by, cascade="all,delete")

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.id} ({self.first_name} {self.last_name})>"

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
