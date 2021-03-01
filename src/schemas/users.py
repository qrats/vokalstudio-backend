from marshmallow import fields, Schema, validate
from marshmallow_enum import EnumField

from src.services.marshmallow import ma
from src.models.users import UserRole
from src.models.users import UserModel


class UserSchema(ma.Schema):
    role = EnumField(UserRole, by_value=True)

    class Meta:
        fields = (
            'id',
            'email',
            'role',
            'name',
            'user_id',
            'image',
            'phone_number',
            'verified'
        )


class AdminUsersSchema(ma.SQLAlchemyAutoSchema):
    role = EnumField(UserRole, by_value=True)

    class Meta:
        model = UserModel
        exclude = ("password", )
