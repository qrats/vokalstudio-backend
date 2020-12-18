from src.services.marshmallow import ma
from src.models.episodes import EpisodesModel


class EpisodesSchema(ma.SQLAlchemyAutoSchema):

    class Meta:
        model = EpisodesModel
