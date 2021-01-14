import uuid
import json
from datetime import datetime
from flask import make_response, jsonify
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.users import UserModel, UserRole
from src.models.authorized_users import AuthorizedUsersModel

from src.schemas.authorized_users import AuthorizedUsersSchema

from src.utils.api_response import APIResponse
from src.utils.email import send_invitation_email
from src.utils.hash import verify_hash


class GetAuthorizedUserResource(Resource):
    @jwt_required
    def get(self, id):
        try:
            authorized_user = AuthorizedUsersModel.filter_first([
                AuthorizedUsersModel.id == id
            ])
            if authorized_user is None:
                return APIResponse.error_404()

            result = AuthorizedUsersSchema().dumps(authorized_user)
            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class GetAuthorizedUsersResource(Resource):
    @jwt_required
    def get(self):
        try:
            session_user = UserModel.get_first([
                UserModel.email == get_jwt_identity()
            ])
            
            if session_user.role == UserRole.ADMIN:
                authorized_user_list = AuthorizedUsersModel.filter_all([])
            else:
                authorized_user_list = AuthorizedUsersModel.filter_all([
                    AuthorizedUsersModel.invited_by == session_user.id
                ])

            authorized_users = AuthorizedUsersSchema().dumps(authorized_user_list, many=True)
            response = jsonify(json.loads(authorized_users))
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class CreateAuthorizedUserResource(Resource):
    @jwt_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('first_name', required=True, help='First name required!')
        parser.add_argument('last_name', required=True, help='Last name required!')
        parser.add_argument('email', required=True, help='Email required!')
        parser.add_argument('password', required=True, help='Password required!')
        data = parser.parse_args()

        session_user = UserModel.get_first([
            UserModel.email == get_jwt_identity()
        ])
        try:

            authorized_user = AuthorizedUsersModel(
                id=str(uuid.uuid4().hex),
                first_name=data['first_name'],
                last_name=data['last_name'],
                email=data['email'],
                password=data['password'],
                invited_by=session_user.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            authorized_user.save()

            result = AuthorizedUsersSchema().dumps(authorized_user)
            response = json.loads(result)
            return make_response(response, 201)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class UpdateAuthorizedUserResource(Resource):
    @jwt_required
    def put(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument('first_name', required=True, help='First name required!')
        parser.add_argument('last_name', required=True, help='Last name required!')
        parser.add_argument('email', required=True, help='Email required!')
        parser.add_argument('password', required=True, help='Password required!')
        data = parser.parse_args()

        try:

            authorized_user = AuthorizedUsersModel.filter_first([
                AuthorizedUsersModel.id == id
            ])
            if authorized_user is None:
                return APIResponse.error_404('Authorized user not found')

            authorized_user.first_name = data['first_name']
            authorized_user.last_name = data['last_name']
            authorized_user.email = data['email']
            authorized_user.password = data['password']
            authorized_user.updated_at = datetime.utcnow()

            authorized_user.save()

            result = AuthorizedUsersSchema().dumps(authorized_user)
            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class DeleteAuthorizedUserResource(Resource):
    @jwt_required
    def delete(self, id):
        try:
            authorized_user = AuthorizedUsersModel.filter_first([
                AuthorizedUsersModel.id == id,
            ])
            if authorized_user is None:
                return APIResponse.error_404("Authorized user not found!")

            authorized_user.delete()
            response = {'message': 'Authorized user deleted'}
            return make_response(response, 204)

        except Exception as e:
            print(e)
            return APIResponse.error_500()


class InviteAuthorizedUserResource(Resource):
    @jwt_required
    def get(self, id):
        session_user = UserModel.get_first([
            UserModel.email == get_jwt_identity()
        ])
        try:

            authorized_user = AuthorizedUsersModel.filter_first([
                AuthorizedUsersModel.id == id,
                AuthorizedUsersModel.invited_by == session_user.id
            ])

            if not authorized_user:
                return APIResponse.error_404("No authorized user found!")

            invite_data = {
                'email': authorized_user.email,
                'password': authorized_user.password,
                'first_name': authorized_user.first_name,
                'last_name': authorized_user.last_name,
                'studio_id': session_user.user_id
            }
            send_invitation_email(invite_data)

            result = AuthorizedUsersSchema().dumps(authorized_user)
            response = json.loads(result)
            return make_response(response, 201)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class AuthorizeUserResource(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('role', required=True, help='Role required!')
        parser.add_argument('studio_id', required=True, help='Studio id required!')
        parser.add_argument('username', required=True, help='Username required!')
        parser.add_argument('password', required=True, help='Password required!')
        data = parser.parse_args()

        try:
            if data['role'] == 'host':
                user = UserModel.get_first([
                    UserModel.email == data['email'],
                    UserModel.user_id == data['studio_id'],
                ])
                if not verify_hash(data['password'], user.password):
                    return APIResponse.error_401("Authorization failed!")
            else:
                invited_user = UserModel.get_first([
                    UserModel.user_id == data['studio_id']
                ])

                if invited_user is None:
                    return APIResponse.error_401("Authorization failed!")

                authorized_user = AuthorizedUsersModel.filter_first([
                    AuthorizedUsersModel.email == data['username'],
                    AuthorizedUsersModel.password == data['password'],
                    AuthorizedUsersModel.invited_by == invited_user.id
                ])
                if authorized_user is None:
                    return APIResponse.error_401("Authorization failed!")

            return APIResponse.success_200("Authorization success!")
        except Exception as e:
            print(e)
            return APIResponse.error_500()
