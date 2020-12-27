import uuid
import json
from datetime import datetime
from flask import make_response, jsonify
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.users import UserModel, UserRole
from src.models.streaming_platforms import StreamingPlatformsModel

from src.schemas.streaming_platforms import StreamingPlatformsSchema

from src.utils.api_response import APIResponse


class GetStreamingPlatformResource(Resource):
    @jwt_required
    def get(self, id):
        try:
            streaming_platform = StreamingPlatformsModel.filter_first([
                StreamingPlatformsModel.id == id
            ])
            if streaming_platform is None:
                return APIResponse.error_404()

            result = StreamingPlatformsSchema().dumps(streaming_platform)
            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class GetStreamingPlatformsResource(Resource):
    @jwt_required
    def get(self):
        try:
            session_user = UserModel.get_first([
                UserModel.email == get_jwt_identity()
            ])

            if session_user.role == UserRole.ADMIN:
                streaming_platform_list = StreamingPlatformsModel.filter_all([])
            else:
                streaming_platform_list = StreamingPlatformsModel.filter_all([
                    StreamingPlatformsModel.user_id == session_user.id
                ])

            streaming_platforms = StreamingPlatformsSchema().dumps(streaming_platform_list, many=True)
            response = jsonify(json.loads(streaming_platforms))
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class CreateStreamingPlatformResource(Resource):
    @jwt_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('service', required=True, help='Service required!')
        parser.add_argument('service_email', required=True, help='Service email required!')
        parser.add_argument('refresh_token', required=True, help='Refresh token required!')
        parser.add_argument('image', required=True, help='Image required!')
        parser.add_argument('active', required=True, help='Active required!')
        data = parser.parse_args()

        session_user = UserModel.get_first([
            UserModel.email == get_jwt_identity()
        ])
        try:

            streaming_platform = StreamingPlatformsModel(
                id=str(uuid.uuid4().hex),
                service=data['service'],
                service_email=data['service_email'],
                image=data['image'],
                refresh_token=data['refresh_token'],
                active=data['active'],
                user_id=session_user.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            streaming_platform.save()

            result = StreamingPlatformsSchema().dumps(streaming_platform)
            response = json.loads(result)
            return make_response(response, 201)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class UpdateStreamingPlatformResource(Resource):
    @jwt_required
    def put(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument('service', required=True, help='Service required!')
        parser.add_argument('service_email', required=True, help='Service email required!')
        parser.add_argument('refresh_token', required=True, help='Refresh token required!')
        parser.add_argument('image', required=True, help='Image required!')
        parser.add_argument('active', required=True, help='Active required!')
        data = parser.parse_args()

        try:
            streaming_platform = StreamingPlatformsModel.filter_first([
                StreamingPlatformsModel.id == id
            ])
            if streaming_platform is None:
                return APIResponse.error_404('Streaming platform not found')

            streaming_platform.service = data['service']
            streaming_platform.service_email = data['service_email']
            streaming_platform.refresh_token = data['refresh_token']
            streaming_platform.image = data['image']
            streaming_platform.active = data['active']
            streaming_platform.updated_at = datetime.utcnow()

            streaming_platform.save()

            result = StreamingPlatformsSchema().dumps(streaming_platform)
            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class DeleteStreamingPlatformResource(Resource):
    @jwt_required
    def delete(self, id):
        try:
            streaming_platform = StreamingPlatformsModel.filter_first([
                StreamingPlatformsModel.id == id,
            ])
            if streaming_platform is None:
                return APIResponse.error_404("Streaming platform not found!")

            streaming_platform.delete()
            response = {'message': 'Streaming platform deleted'}
            return make_response(response, 204)

        except Exception as e:
            print(e)
            return APIResponse.error_500()
