import random
from datetime import datetime
from flask_restful import Resource, reqparse
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, jwt_refresh_token_required, \
  get_jwt_identity, get_raw_jwt
from flask import current_app as app

from src.models.revoked_tokens import RevokedTokenModel
from src.models.users import UserModel, UserRole

from src.utils.hash import generate_hash, verify_hash

from src.utils.api_response import APIResponse

from src.utils.auth_token import generate_confirmation_token, confirm_token
from src.utils.email import send_registration_email


class SignUpResource(Resource):
  def post(self):
    """
    Sign up
    ---
    description: Signup with user information
    operationId: userSignup
    requestBody:
      content:
        application/json:
          schema:
            example:
              email: user@mail.com
              password: secret
              name: Test User
              role: User
            properties:
              email:
                type: string
              password:
                type: string
              name:
                type: string
            required:
              - email
              - password
              - name
            type: object
      description: email and password must be specified.
      required: true
    responses:
      '200':
        description: Signup success
      '409':
        description: Conflict user
      '500':
        description: Internal server error
    summary: Sign Up
    tags:
      - auth
    """
    parser = reqparse.RequestParser()
    parser.add_argument('email', required=True, help='Email required!')
    parser.add_argument('password', required=True, help='Password required!')
    parser.add_argument('name', required=True, help='Name required!')
    data = parser.parse_args()

    try:
      duplicated = True
      base_user_id = data['name'].lower().replace(' ', '-')

      user_id = base_user_id
      while duplicated:
        user = UserModel.get_first([
          UserModel.user_id == user_id
        ])
        if user is None:
          duplicated = False
        else:
          user_id = f"{base_user_id}-{random.randint(100,999)}"

      user = UserModel.get_first([
        UserModel.email == data['email']
      ])

      if user is not None:
        if user.verified:
          return APIResponse.error_409("User already exist!")
      else:
        user = UserModel(email=data['email'])

      user.password = generate_hash(data['password'])
      user.role = UserRole.USER
      user.user_id = user_id
      user.name = data['name']
      user.verified = False

      token = generate_confirmation_token(data['email'])
      payload = {
        'email': user.email,
        'user_id': user.user_id,
        'name': user.name,
        'service_name': app.config['SERVICE_NAME'],
        'host_name': app.config['HOST_NAME']
      }

      send_registration_email(payload, token)
      user.save()

      response = {'message': 'Email sent!'}
      return APIResponse.success_200(response)
    except Exception as e:
      print(e)
      return APIResponse.error_500()


class SignInResource(Resource):
  def post(self):
    """
    Sign in
    ---
    description: Authenticate user with supplied credentials.
    operationId: userSignin
    requestBody:
      content:
        application/json:
          example:
            login: user@mail.com
            password: secret
          schema:
            properties:
              login:
                type: string
              password:
                type: string
            type: object
            required:
              - login
              - password
    responses:
      '200':
        description: Login success
      '400':
        description: Invalid password
      '403':
        description: User not verified
      '500':
        description: Internal server error
    summary: Sign In
    tags:
      - auth
    """
    parser = reqparse.RequestParser()
    parser.add_argument('login', required=True, help='Email or User ID required!')
    parser.add_argument('password', required=True, help='Password required!')
    data = parser.parse_args()

    try:
      user_by_id = UserModel.get_first([
        UserModel.user_id == data['login']
      ])

      user_by_email = UserModel.get_first([
        UserModel.email == data['login']
      ])
      if user_by_email is None and user_by_id is None:
        return APIResponse.error_404("User not found!")

      user = user_by_id if user_by_id is not None else user_by_email

      if user.verified:
        if verify_hash(data['password'], user.password):
          response = {
            'access_token': create_access_token(identity=user.email),
            'refresh_token': create_refresh_token(identity=user.email)
          }
          return APIResponse.success_200(response)
        else:
          return APIResponse.error_400("Invalid password!")
      else:
        return APIResponse.error_403("User not verified!")

    except Exception as e:
      print(e)
      return APIResponse.error_500()


class SignOutResource(Resource):
  @jwt_required
  def post(self):
    """
    Sign out
    ---
    description: Signout user.
    operationId: userSignout
    responses:
      '204':
        description: Signout success
      '401':
        description: Unauthorized
      '500':
        description: Internal server error
    security:
      - bearerAuth: []
    summary: Sign out
    tags:
      - auth
    """
    jti = get_raw_jwt()['jti']
    try:
      revoked_token = RevokedTokenModel(jti=jti)
      revoked_token.add()
      response = {'message': 'Token revoked'}
      return APIResponse.success_204(response)
    except Exception as e:
      print(e)
      return APIResponse.error_500()


class TokenRefreshResource(Resource):
  @jwt_refresh_token_required
  def post(self):
    """
    Refresh Token
    ---
    description: Refresh access token.
    operationId: tokenRefresh
    responses:
      '204':
        description: Token refresh success
      '401':
        description: Refresh token not provided or invalid
      '500':
        description: Internal server error
    security:
      - bearerAuth: []
    summary: Refresh access token
    tags:
      - auth
    """
    try:
      email = get_jwt_identity()
      response = {
        'access_token': create_access_token(identity=email),
        'refresh_token': create_refresh_token(identity=email)
      }
      return APIResponse.success_200(response)
    except Exception as e:
      print(e)
      return APIResponse.error_500()


class UserVerifyResource(Resource):
  def post(self):
    """
    User Verify
    ---
    description: Verify email for sign up.
    operationId: signupVerify
    parameters:
      - description: Token in verification email sent for sign up.
        in: path
        name: verifyToken
        required: true
        schema:
          type: string
    responses:
      '200':
        description: Email verify success
      '400':
        description: User already verified.
      '404':
        description: Invalid or expired token.
      '500':
        description: Internal server error
    summary: Verify email
    tags:
      - auth
    """
    parser = reqparse.RequestParser()
    parser.add_argument('token', required=True, help='Token required!')
    data = parser.parse_args()

    try:
      email = confirm_token(data['token'])

      if email is None:
        return APIResponse.error_404("The link has been expired or invalid.")

      user = UserModel.get_first([UserModel.email == email])
      if user.verified:
        return APIResponse.error_400("User already verified.")

      user.verified = True
      user.verified_at = datetime.utcnow()
      user.save()
      response = {"message": "User has been verified."}
      return APIResponse.success_200(response)
    except Exception as e:
      print(e)
      return APIResponse.error_500()


class ResendVerifyEmailResource(Resource):
  def post(self):
    """
    Resend Email
    ---
    description: Resend verify email for sign up.
    operationId: signupEmailResend
    parameters:
      - description: Email used for sign up.
        in: path
        name: email
        required: true
        schema:
          type: string
    responses:
      '200':
        description: Email sent
      '404':
        description: Email not found.
      '500':
        description: Internal server error
    summary: Resend verify email
    tags:
      - auth
    """
    parser = reqparse.RequestParser()
    parser.add_argument('email', required=True, help='Email required!')
    data = parser.parse_args()

    try:
      email = data['email']
      user = UserModel.get_first([UserModel.email == email])

      if user is None:
        return APIResponse.error_404("User not found.")

      if user.verified:
        return APIResponse.error_400("User already verified.")

      payload = {
        'email': user.email,
        'name': user.name,
        'user_id': user.user_id
      }
      token = generate_confirmation_token(email)
      send_registration_email(payload, token)

      response = {"message": "Email resent."}
      return APIResponse.success_200(response)
    except Exception as e:
      print(e)
      return APIResponse.error_500()


class UpdateEmailResource(Resource):
  def post(self):
    """
    Update Email
    ---
    description: Update signup email.
    operationId: signupEmailUpdate
    parameters:
      - description: Email used for sign up.
        in: path
        name: old_email
        required: true
        schema:
          type: string
      - description: New email for sign up.
        in: path
        name: new_email
        required: true
        schema:
          type: string
    responses:
      '200':
        description: Email sent
      '404':
        description: Old email not found.
      '409':
        description: New email already exist.
      '500':
        description: Internal server error
    summary: '  Update email used for sign up.'
    tags:
      - auth
    """
    parser = reqparse.RequestParser()
    parser.add_argument('old_email', required=True, help='Old email required!')
    parser.add_argument('new_email', required=True, help='New email required!')
    data = parser.parse_args()

    try:
      user = UserModel.get_first([UserModel.email == data['old_email']])
      if user is None:
        return APIResponse.error_404("User not found")

      new_user = UserModel.get_first([UserModel.email == data['new_email']])
      if new_user is not None:
        return APIResponse.error_409("Email already exist.")

      user.email = data['new_email']
      token = generate_confirmation_token(data['new_email'])
      payload = {
        'email': user.email,
        'user_id': user.user_id,
        'name': user.name,
        'service_name': app.config['SERVICE_NAME'],
        'host_name': app.config['HOST_NAME']
      }
      send_registration_email(payload, token)

      user.save()
      response = {'message': 'Email updated'}
      return APIResponse.success_200(response)
    except Exception as e:
      print(e)
      return APIResponse.error_500()
