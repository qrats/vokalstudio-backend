from src.services.marshmallow import ma
from src.models.streaming_platforms import StreamingPlatformsModel


class StreamingPlatformsSchema(ma.SQLAlchemyAutoSchema):

    class Meta:
        model = StreamingPlatformsModel
