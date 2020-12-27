from src.services.marshmallow import ma
from src.models.authorized_users import AuthorizedUsersModel


class AuthorizedUsersSchema(ma.SQLAlchemyAutoSchema):

    class Meta:
        model = AuthorizedUsersModel
