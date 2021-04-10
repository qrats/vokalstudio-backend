from src.services.marshmallow import ma
from src.models.blogs import BlogsModel


class BlogsSchema(ma.SQLAlchemyAutoSchema):

    class Meta:
        model = BlogsModel
