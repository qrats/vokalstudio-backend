from src.services.marshmallow import ma
from src.models.media_objects import MediaObjectsModel


class MediaObjectsSchema(ma.SQLAlchemyAutoSchema):

    class Meta:
        model = MediaObjectsModel
