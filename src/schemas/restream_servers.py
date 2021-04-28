from src.services.marshmallow import ma
from src.models.restream_servers import RestreamServersModel

from src.schemas.subscriptions import AdminSubscriptionsSchema
from marshmallow import fields


class RestreamServersSchema(ma.SQLAlchemyAutoSchema):

    class Meta:
        model = RestreamServersModel

        fields = (
            'id',
            'state',
            'public_ip',
            'public_dns',
            'created_at',
            'updated_at',
        )


class AdminRestreamServersSchema(ma.SQLAlchemyAutoSchema):
    subscription = fields.Nested(AdminSubscriptionsSchema)

    class Meta:
        model = RestreamServersModel
        exclude = ("reservation",)


