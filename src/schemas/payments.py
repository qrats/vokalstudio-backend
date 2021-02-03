from src.services.marshmallow import ma
from src.models.payments import PaymentsModel
from src.schemas.users import UserSchema

from marshmallow import fields


class PaymentsSchema(ma.SQLAlchemyAutoSchema):
    user = fields.Nested(UserSchema)

    class Meta:
        model = PaymentsModel
