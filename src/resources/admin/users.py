import json
from flask import make_response, jsonify
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, jwt_refresh_token_required, get_jwt_identity

from src.models.users import UserModel, UserRole
from src.schemas.users import UserSchema, AdminUsersSchema

from src.utils.api_response import APIResponse
from src.utils.hash import generate_hash
from src.utils.api_response import APIResponse
from src.utils.permissions import admin_required


class GetUsersResource(Resource):
    @jwt_required
    @admin_required
    def get(self):
        """
        Get all Users
        ---
        tags:
          - user
        description: Get all users
        operationId: getUsers
        security:
          - bearerAuth: []
        responses:
          200:
            description: Success
          401:
            description: Unauthorized
          500:
            description: Internal server error
          """
        try:
            users = UserModel.get_all([])
            result = AdminUsersSchema().dumps(users, many=True)

            response = jsonify(json.loads(result))
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class GetUserResource(Resource):
    @jwt_required
    @admin_required
    def get(self, id):
        """
        Get single user
        ---
        tags:
          - user
        description: Get user by id.
        operationId: getUser
        security:
          - bearerAuth: []
        parameters:
          - in: path
            name: id
            schema:
              type: integer
            required: true
            description: User id
        responses:
          200:
            description: Success
          401:
            description: Unauthorized.
          404:
            description: User not found
          500:
            description: Internal server error
        """
        try:
            user = UserModel.get_first([
                UserModel.id == id,
            ])
            if user is None:
                return APIResponse.error_404()

            result = AdminUsersSchema().dumps(user)

            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class UpdateUserResource(Resource):
    @jwt_required
    @admin_required
    def put(self, id):
        """
        Update user
        ---
        tags:
          - user
        description: Update user.
        operationId: updateUser
        security:
          - bearerAuth: []
        parameters:
          - in: path
            name: id
            schema:
              type: integer
            required: true
            description: User id
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  email:
                    type: string
                  name:
                    type: string
                  user_id:
                    type: string
                  role:
                    type: string
                    enum:
                      - User
                      - Admin
                  phone_number:
                    type: string
                  verified:
                    type: boolean
                  verified:
                    type: boolean
                required:
                  - email
                  - name
                  - user_id
                  - role
                example:
                  email: new@mail.com
                  name: New Name
                  user_id: new-name
                  role: User
                  phone_number: 1(123)456-789
                  verified: true
                  active: true
          description: email, name, user_id and role must be specified.
          required: true
        responses:
          200:
            description: User updated
          401:
            description: Unauthorized
          404:
            description: User not found
          500:
            description: Internal server error
        """
        parser = reqparse.RequestParser()
        parser.add_argument('email', required=True, help='Email required!')
        parser.add_argument('name', required=True, help='Name required!')
        parser.add_argument('user_id', required=True, help='User id required!')
        roles = ("Admin", "User")
        parser.add_argument('role', choices=roles, required=True, help='Invalid role!')
        parser.add_argument('phone_number')
        parser.add_argument('verified', type=bool)
        parser.add_argument('active', type=bool)
        data = parser.parse_args()

        try:
            user = UserModel.get_first([
                UserModel.id == id,
            ])
            if user is None:
                return APIResponse.error_404()

            duplicated_user = UserModel.get_first([
                UserModel.user_id == data['user_id'],
                UserModel.user_id != user.user_id
            ])
            if duplicated_user is not None:
                return APIResponse.error_400("User id duplicated")

            duplicated_user = UserModel.get_first([
                UserModel.email == data['email'],
                UserModel.email != user.email
            ])
            if duplicated_user is not None:
                return APIResponse.error_400("Email duplicated")

            user.email = data['email']
            user.user_id = data['user_id']
            user.role = data['role']
            user.name = data['name']
            user.phone_number = data['phone_number']
            if data['verified'] is not None:
                user.verified = data['verified']

            if data['active'] is not None:
                user.active = data['active']

            user.save()

            result = AdminUsersSchema().dumps(user)

            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class DeleteUserResource(Resource):
    @jwt_required
    @admin_required
    def delete(self, id):
        """
        Delete user
        ---
        tags:
          - user
        description: Delete user by id.
        operationId: deleteUser
        security:
          - bearerAuth: []
        parameters:
          - in: path
            name: id
            schema:
              type: integer
            required: true
            description: user id
        responses:
          204:
            description: Deleted
          401:
            description: Unauthorized.
          404:
            description: user not found
          500:
            description: Internal server error
        """
        try:
            user = UserModel.get_first([
                UserModel.id == id,
            ])
            if user is None:
                return APIResponse.error_404()

            user.delete()
            response = {'message': 'User deleted!'}
            return make_response(response, 204)

        except Exception as e:
            print(e)
            return APIResponse.error_500()
