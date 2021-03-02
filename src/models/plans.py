"""Plans models and database functionality"""
from src.services.db import db
from datetime import datetime
from src.models.products import ProductsModel


class PlansModel(db.Model):
    __tablename__ = "plans"

    id = db.Column(db.String(256), primary_key=True)
    sandbox = db.Column(db.Boolean, nullable=False, default=True)
    product_id = db.Column(db.String(256), db.ForeignKey('products.id'))
    name = db.Column(db.String(256), nullable=False)
    description = db.Column(db.String(4096), nullable=True)
    status = db.Column(db.String(256), nullable=True, default='ACTIVE')
    billing_cycles = db.Column(db.JSON, nullable=True)
    payment_preferences = db.Column(db.JSON, nullable=True)
    taxes = db.Column(db.JSON, nullable=True)
    links = db.Column(db.JSON, nullable=True)
    quantity_supported = db.Column(db.Boolean, nullable=True, default=False)

    create_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    update_time = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = db.relationship(ProductsModel, foreign_keys=product_id)

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
