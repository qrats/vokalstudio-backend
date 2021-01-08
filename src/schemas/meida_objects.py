from src.services.marshmallow import ma
from src.models.media_objects import MediaObjectsModel
from src.schemas.users import UserSchema

from marshmallow import fields


class MediaObjectsSchema(ma.SQLAlchemyAutoSchema):
    uploader = fields.Nested(UserSchema)

    class Meta:
        model = MediaObjectsModel
