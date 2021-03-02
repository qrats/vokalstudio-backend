"""Products models and database functionality"""
from src.services.db import db
from datetime import datetime


class ProductsModel(db.Model):
    __tablename__ = "products"

    id = db.Column(db.String(256), primary_key=True)
    sandbox = db.Column(db.Boolean, nullable=False, default=True)
    name = db.Column(db.String(256), nullable=False)
    description = db.Column(db.String(4096), nullable=True)
    type = db.Column(db.String(256), nullable=True, default='SERVICE')
    category = db.Column(db.String(256), nullable=True, default='SOFTWARE')
    home_url = db.Column(db.String(1024), nullable=True)
    image_url = db.Column(db.String(1024), nullable=True)
    links = db.Column(db.JSON, nullable=True)

    create_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.id} ({self.name})>"

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
