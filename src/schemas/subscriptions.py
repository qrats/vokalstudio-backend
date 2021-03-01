from src.services.marshmallow import ma
from src.models.subscriptions import SubscriptionsModel

from src.schemas.users import UserSchema
from src.schemas.plans import PlansSchema

from marshmallow import fields


class SubscriptionsSchema(ma.SQLAlchemyAutoSchema):
    user = fields.Nested(UserSchema)
    plan = fields.Nested(PlansSchema)

    class Meta:
        model = SubscriptionsModel

        fields = (
            'id',
            'status',
            'start_time',
            'update_time',
            'plan'
        )


class AdminSubscriptionsSchema(ma.SQLAlchemyAutoSchema):
    user = fields.Nested(UserSchema)
    plan = fields.Nested(PlansSchema)

    class Meta:
        model = SubscriptionsModel
        exclude = ("links",)


