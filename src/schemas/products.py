from src.services.marshmallow import ma
from src.models.products import ProductsModel


class ProductsSchema(ma.SQLAlchemyAutoSchema):

    class Meta:
        model = ProductsModel
