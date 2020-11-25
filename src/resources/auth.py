import json
from datetime import datetime
from flask import make_response, jsonify
from flask_restful import Resource, reqparse
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, jwt_refresh_token_required, \
    get_jwt_identity, get_raw_jwt
from src.models.revoked_tokens import RevokedTokenModel
from src.models.users import UserModel, UserRole

from src.utils.hash import generate_hash, verify_hash

from src.utils.api_response import *

from src.utils.auth_token import generate_confirmation_token, confirm_token
from src.utils.email import send_registration_email


class SignUpResource(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('email', required=True, help='Email required!')
        parser.add_argument('password', required=True, help='Password required!')
        roles = ("Admin", "User")
        parser.add_argument('role', choices=roles, required=True, help='Invalid role!')
        parser.add_argument('first_name')
        parser.add_argument('last_name')
        data = parser.parse_args()

        try:
            user = UserModel.get_first([
                UserModel.email == data['email']
            ])

            if user is not None:
                if user.verified:
                    return error_409("User already exist!")
            else:
                user = UserModel(email=data['email'])

            user.password = generate_hash(data['password'])
            user.role = UserRole.USER
            user.first_name = data['first_name']
            user.last_name = data['last_name']
            user.verified = False

            token = generate_confirmation_token(data['email'])
            payload = {
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
            send_registration_email(payload, token)
            user.save()

            response = {'message': 'Email sent!'}
            return make_response(response, 201)
        except Exception as e:
            print(e)
            return error_500()


class SignInResource(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('email', required=True, help='Email required!')
        parser.add_argument('password', required=True, help='Password required!')
        data = parser.parse_args()

        try:
            email = data['email']

            user = UserModel.get_first([
                UserModel.email == email
            ])
            if user is None:
                return error_404("User not found!")

            if user.verified:
                if verify_hash(data['password'], user.password):
                    response = {
                        'access_token': create_access_token(identity=email),
                        'refresh_token': create_refresh_token(identity=email)
                    }
                    return make_response(response, 200)
                else:
                    return error_400("Invalid password!")
            else:
                return error_403("Account is not confirmed yet!")

        except Exception as e:
            print(e)
            return error_500()


class SignOutResource(Resource):
    @jwt_required
    def post(self):
        jti = get_raw_jwt()['jti']
        try:
            revoked_token = RevokedTokenModel(jti=jti)
            revoked_token.add()
            response = {'message': 'Token revoked'}
            return make_response(response, 204)
        except Exception as e:
            print(e)
            return error_500()


class TokenRefreshResource(Resource):
    @jwt_refresh_token_required
    def post(self):
        try:
            email = get_jwt_identity()
            response = {
                'access_token': create_access_token(identity=email),
                'refresh_token': create_refresh_token(identity=email)
            }
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return error_500()


class UserVerifyResource(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('token', required=True, help='Token required!')
        data = parser.parse_args()

        try:
            email = confirm_token(data['token'])

            if email is None:
                return error_404("The link has been expired or invalid.")

            user = UserModel.get_first([UserModel.email == email])
            if user.verified:
                return error_400("User already verified.")

            user.verified = True
            user.verified_at = datetime.utcnow()
            user.save()
            response = {"message": "User has been verified."}
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return error_500()


class ResendVerifyEmailResource(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('email', required=True, help='Email required!')
        data = parser.parse_args()

        try:
            email = data['email']
            user = UserModel.get_first([UserModel.email == email])
            if user.verified:
                return error_404("User not found.")

            payload = {
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
            token = generate_confirmation_token(email)
            send_registration_email(payload, token)
            response = {"message": "Email resent."}
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return error_500()


class UpdateEmailResource(Resource):
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('old_email', required=True, help='Old email required!')
        parser.add_argument('new_email', required=True, help='New email required!')
        data = parser.parse_args()

        try:
            user = UserModel.get_first([UserModel.email == data['old_email']])
            if user is None:
                return error_404("User not found")

            new_user = UserModel.get_first([UserModel.email == data['new_email']])
            if new_user is not None:
                return error_409("Email already exist.")

            user.email = data['new_email']
            token = generate_confirmation_token(data['new_email'])
            send_registration_email(data['new_email'], token)
            user.save()
        except Exception as e:
            print(e)
            return error_500()
