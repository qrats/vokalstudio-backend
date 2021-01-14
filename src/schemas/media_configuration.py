from src.services.marshmallow import ma
from src.models.media_configuration import MediaConfigurationModel


class MediaConfigurationSchema(ma.SQLAlchemyAutoSchema):

    class Meta:
        model = MediaConfigurationModel
