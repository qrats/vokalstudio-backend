"""Blogs  models and database functionality"""
from src.services.db import db
from datetime import datetime


class BlogsModel(db.Model):
    __tablename__ = "blogs"

    slug = db.Column(db.String(1024), primary_key=True)
    title = db.Column(db.String(1024), nullable=False)
    content = db.Column(db.String(16000000), nullable=False)
    author = db.Column(db.String(256), nullable=True)
    type = db.Column(db.String(256), nullable=True, default='blog')
    status = db.Column(db.String(256), nullable=True, default='draft')  # [draft, published, archived]

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.slug} ({self.title}), title: {self.title}>"

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
