from src.services.marshmallow import ma
from src.models.uploading_platforms import UploadingPlatformsModel


class UploadingPlatformsSchema(ma.SQLAlchemyAutoSchema):

    class Meta:
        model = UploadingPlatformsModel
