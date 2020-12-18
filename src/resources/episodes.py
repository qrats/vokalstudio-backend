import uuid
import json
from datetime import datetime
from flask import make_response, jsonify
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.users import UserModel
from src.models.episodes import EpisodesModel
from src.schemas.episodes import EpisodesSchema

from src.utils.api_response import APIResponse


class GetEpisodeResource(Resource):
    @jwt_required
    def get(self, id):
        try:
            episode_obj = EpisodesModel.filter_first([
                EpisodesModel.id == id
            ])

            if episode_obj is None:
                return APIResponse.error_404()

            episode = EpisodesSchema().dumps(episode_obj)
            response = jsonify(json.loads(episode))
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class GetEpisodesResource(Resource):
    @jwt_required
    def get(self):
        try:
            user = UserModel.get_first([
                UserModel.email == get_jwt_identity()
            ])

            if user.role == 'Admin':
                episode_list = EpisodesModel.filter_all([])
            else:
                episode_list = EpisodesModel.filter_all([
                    EpisodesModel.uploader_id == user.id
                ])

            episodes = EpisodesSchema().dumps(episode_list, many=True)
            response = jsonify(json.loads(episodes))
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class CreateEpisodesResource(Resource):
    @jwt_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('uploader_id', required=True, help='uploader_id required!')
        parser.add_argument('title', required=True, help='Title required!')
        parser.add_argument('url', required=True, help='URL required!')
        parser.add_argument('description')
        parser.add_argument('image')
        parser.add_argument('type')
        parser.add_argument('status')
        parser.add_argument('premium')
        data = parser.parse_args()

        try:
            episode = EpisodesModel(
                id=str(uuid.uuid4().hex),
                uploader_id=data['uploader_id'],
                title=data['title'],
                description=data['description'],
                url=data['url'],
                image=data['image'],
                status=data['status'],
                type=data['type'],
                premium=True if data['premium'].lower() == 'true' else False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            episode.save()

            result = EpisodesSchema().dumps(episode)
            response = json.loads(result)
            return make_response(response, 201)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class UpdateEpisodesResource(Resource):
    @jwt_required
    def put(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument('uploader_id', required=True, help='uploader_id required!')
        parser.add_argument('title', required=True, help='Title required!')
        parser.add_argument('url', required=True, help='URL required!')
        parser.add_argument('description')
        parser.add_argument('image')
        parser.add_argument('type')
        parser.add_argument('status')
        parser.add_argument('premium')
        data = parser.parse_args()

        try:
            episode = EpisodesModel.filter_first([
                EpisodesModel.id == id
            ])

            if episode is None:
                return APIResponse.error_404()

            if episode.url != data['url']:
                pass

            episode.title = data['title']
            episode.description = data['description']
            episode.url = data['url']
            episode.image = data['image']
            episode.type = data['type']
            episode.status = data['status']
            episode.premium = True if data['premium'].lower() == 'true' else False
            episode.save()

            result = EpisodesSchema().dumps(episode)
            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class DeleteEpisodesResource(Resource):
    @jwt_required
    def delete(self, id):
        try:
            episode = EpisodesModel.filter_first([
                EpisodesModel.id == id
            ])

            if episode is None:
                return APIResponse.error_404()

            episode.delete()
            response = {'message': 'Episode deleted!'}
            return make_response(response, 204)

        except Exception as e:
            print(e)
            return APIResponse.error_500()
