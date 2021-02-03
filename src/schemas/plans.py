from src.services.marshmallow import ma
from src.models.plans import PlansModel

from src.schemas.products import ProductsSchema
from marshmallow import fields


class PlansSchema(ma.SQLAlchemyAutoSchema):
    product = fields.Nested(ProductsSchema)

    class Meta:
        model = PlansModel
