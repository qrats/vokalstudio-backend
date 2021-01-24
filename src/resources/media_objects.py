import os
import uuid
import json
import subprocess
from datetime import datetime
from flask import make_response, jsonify
from flask import current_app as app
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.datastructures import FileStorage

from src.models.users import UserModel, UserRole
from src.models.media_objects import MediaObjectsModel

from src.schemas.meida_objects import MediaObjectsSchema

from src.utils.api_response import APIResponse
from src.tasks.media_worker import media_uploader


class GetMediaObjectResource(Resource):
    @jwt_required
    def get(self, id):
        try:
            media_object = MediaObjectsModel.filter_first([
                MediaObjectsModel.id == id
            ])
            if media_object is None:
                return APIResponse.error_404()

            result = MediaObjectsSchema().dumps(media_object)
            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class GetMediaObjectsResource(Resource):
    @jwt_required
    def get(self):
        try:
            session_user = UserModel.get_first([
                UserModel.email == get_jwt_identity()
            ])

            if session_user.role == UserRole.ADMIN:
                media_object_list = MediaObjectsModel.filter_all([])
            else:
                media_object_list = MediaObjectsModel.filter_all([
                    MediaObjectsModel.uploader_id == session_user.id
                ])

            media_objects = MediaObjectsSchema().dumps(media_object_list, many=True)
            response = jsonify(json.loads(media_objects))
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class CreateMediaObjectResource(Resource):
    @jwt_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('file_name', required=True, help='File name required!')
        parser.add_argument('description', required=True, help='Description required!')
        parser.add_argument('url', required=True, help='Url required!')
        parser.add_argument('type', required=True, help='Type required!')
        parser.add_argument('image', required=True, help='Image required!')
        data = parser.parse_args()

        session_user = UserModel.get_first([
            UserModel.email == get_jwt_identity()
        ])
        try:
            media_object = MediaObjectsModel(
                id=str(uuid.uuid4().hex),
                file_name=data['file_name'],
                description=data['description'],
                url=data['url'],
                type=data['type'],
                image=data['image'],
                uploader_id=session_user.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            if data['url'].split('.')[-1] in ['mp3', 'mp4', 'mov', 'mkv', 'flv']:
                a = str(subprocess.check_output(
                    '/usr/bin/ffprobe -i  "' + data['url'] + '" 2>&1 | /usr/bin/grep "Duration"', shell=True))
                a = a.split(",")[0].split("Duration:")[1].strip()
                duration = a.split('.')[0]
                media_object.duration = datetime.strptime(duration, '%H:%M:%S').time()

            media_object.save()
            result = MediaObjectsSchema().dumps(media_object)
            response = json.loads(result)
            return make_response(response, 201)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class UpdateMediaObjectResource(Resource):
    @jwt_required
    def put(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument('file_name', required=True, help='File name required!')
        parser.add_argument('description', required=True, help='Description required!')
        parser.add_argument('url', required=True, help='Url required!')
        parser.add_argument('type', required=True, help='Type required!')
        parser.add_argument('image', required=True, help='Image required!')
        data = parser.parse_args()

        try:
            media_object = MediaObjectsModel.filter_first([
                MediaObjectsModel.id == id
            ])
            if media_object is None:
                return APIResponse.error_404('Media object not found')

            media_object.file_name = data['file_name']
            media_object.description = data['description']
            media_object.url = data['url']
            media_object.type = data['type']
            media_object.image = data['image']
            media_object.updated_at = datetime.utcnow()

            if data['url'].split('.')[-1] in ['mp3', 'mp4', 'mov', 'mkv', 'flv']:
                a = str(subprocess.check_output(
                    '/usr/bin/ffprobe -i  "' + data['url'] + '" 2>&1 | /usr/bin/grep "Duration"', shell=True))
                a = a.split(",")[0].split("Duration:")[1].strip()
                duration = a.split('.')[0]
                media_object.duration = datetime.strptime(duration, '%H:%M:%S').time()

            media_object.save()

            result = MediaObjectsSchema().dumps(media_object)
            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class DeleteMediaObjectResource(Resource):
    @jwt_required
    def delete(self, id):
        try:
            media_object = MediaObjectsModel.filter_first([
                MediaObjectsModel.id == id,
            ])
            if media_object is None:
                return APIResponse.error_404("Media object not found!")

            media_object.delete()
            response = {'message': 'Media object deleted'}
            return make_response(response, 204)

        except Exception as e:
            print(e)
            return APIResponse.error_500()


class UploadMediaObjectsResource(Resource):
    @jwt_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('category', required=True, help='Category required!')
        parser.add_argument('file', location='files', type=FileStorage, help='Files required!')
        data = parser.parse_args()

        file = data['file']
        file_name = file.filename
        try:
            file_path = os.path.join('/tmp', file_name)
            file.save(file_path)

            session_user = UserModel.get_first([
                UserModel.email == get_jwt_identity()
            ])

            media_object = MediaObjectsModel(
                id=str(uuid.uuid4().hex),
                file_name=file_name,
                url=f"{app.config['CDN_HOST']}/{data['category']}/{file_name}",
                type=data['category'],
                uploader_id=session_user.id,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            if file_name.split('.')[-1] in ['mp3', 'mp4', 'mov', 'mkv', 'flv']:
                a = str(subprocess.check_output(
                    '/usr/bin/ffprobe -i  "' + file_path + '" 2>&1 | /usr/bin/grep "Duration"', shell=True))
                a = a.split(",")[0].split("Duration:")[1].strip()
                duration = a.split('.')[0]
                media_object.duration = datetime.strptime(duration, '%H:%M:%S').time()

            media_uploader.delay(file_path)
            media_object.save()

            result = MediaObjectsSchema().dumps(media_object)
            response = json.loads(result)
            return make_response(response, 201)
        except Exception as e:
            print(e)
            return APIResponse.error_500()
