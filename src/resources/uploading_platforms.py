import uuid
import json
from datetime import datetime
from flask import current_app as app
from flask import make_response, jsonify
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.users import UserModel, UserRole
from src.models.uploading_platforms import UploadingPlatformsModel

from src.schemas.uploading_platforms import UploadingPlatformsSchema

from src.utils.api_response import APIResponse

import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2.credentials import Credentials


class GetUploadingPlatformResource(Resource):
    @jwt_required
    def get(self, id):
        try:
            uploading_platform = UploadingPlatformsModel.filter_first([
                UploadingPlatformsModel.id == id
            ])
            if uploading_platform is None:
                return APIResponse.error_404()

            result = UploadingPlatformsSchema().dumps(uploading_platform)
            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class GetUploadingPlatformsResource(Resource):
    @jwt_required
    def get(self):
        try:
            session_user = UserModel.get_first([
                UserModel.email == get_jwt_identity()
            ])

            if session_user.role == UserRole.ADMIN:
                uploading_platform_list = UploadingPlatformsModel.filter_all([])
            else:
                uploading_platform_list = UploadingPlatformsModel.filter_all([
                    UploadingPlatformsModel.user_id == session_user.id
                ])

            uploading_platforms = UploadingPlatformsSchema().dumps(uploading_platform_list, many=True)
            response = jsonify(json.loads(uploading_platforms))
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class CreateUploadingPlatformResource(Resource):
    @jwt_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('service', required=True, help='Service required!')
        parser.add_argument('image', required=True, help='Image required!')
        parser.add_argument('service_email')
        parser.add_argument('refresh_token')
        parser.add_argument('active')
        data = parser.parse_args()

        session_user = UserModel.get_first([
            UserModel.email == get_jwt_identity()
        ])
        try:
            uploading_platform = UploadingPlatformsModel(
                id=str(uuid.uuid4().hex),
                service=data['service'],
                image=data['image'],
                service_email=data['service_email'],
                refresh_token=data['refresh_token'],
                active=False,
                user_id=session_user.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            if data['service'] == 'Youtube':
                info = {
                    'refresh_token': data['refresh_token'],
                    "client_id": app.config['GOOGLE_CLIENT_ID'],
                    "client_secret": app.config['GOOGLE_CLIENT_SECRET'],
                }
                credentials = Credentials.from_authorized_user_info(info)
                youtube = googleapiclient.discovery.build("youtube", "v3", credentials=credentials)
                request = youtube.channels().list(
                    part="snippet,contentDetails,statistics",
                    mine=True
                )
                response = request.execute()

                if response['pageInfo']['totalResults'] > 0:
                    uploading_platform.channel_id = response['items'][0]['id']
                    uploading_platform.channel_name = response['items'][0]['snippet']['title']

            uploading_platform.save()

            result = UploadingPlatformsSchema().dumps(uploading_platform)
            response = json.loads(result)
            return make_response(response, 201)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class UpdateUploadingPlatformResource(Resource):
    @jwt_required
    def put(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument('service', required=True, help='Service required!')
        parser.add_argument('service_email', required=True, help='Service email required!')
        parser.add_argument('refresh_token', required=True, help='Refresh token required!')
        parser.add_argument('image', required=True, help='Image required!')
        parser.add_argument('active', required=True, type=bool, help='Active required!')
        data = parser.parse_args()

        try:
            uploading_platform = UploadingPlatformsModel.filter_first([
                UploadingPlatformsModel.id == id
            ])
            if uploading_platform is None:
                return APIResponse.error_404('Uploading platform not found')

            uploading_platform.service = data['service']
            uploading_platform.service_email = data['service_email']
            uploading_platform.refresh_token = data['refresh_token']
            uploading_platform.image = data['image']
            uploading_platform.active = data['active']
            uploading_platform.updated_at = datetime.utcnow()

            uploading_platform.save()

            result = UploadingPlatformsSchema().dumps(uploading_platform)
            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class DeleteUploadingPlatformResource(Resource):
    @jwt_required
    def delete(self, id):
        try:
            uploading_platform = UploadingPlatformsModel.filter_first([
                UploadingPlatformsModel.id == id,
            ])
            if uploading_platform is None:
                return APIResponse.error_404("Uploading platform not found!")

            uploading_platform.delete()
            response = {'message': 'Uploading platform deleted'}
            return make_response(response, 204)

        except Exception as e:
            print(e)
            return APIResponse.error_500()
