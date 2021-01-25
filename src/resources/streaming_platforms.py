import uuid
import json
import requests
from datetime import datetime
from flask import current_app as app
from flask import make_response, jsonify
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.users import UserModel, UserRole
from src.models.streaming_platforms import StreamingPlatformsModel

from src.schemas.streaming_platforms import StreamingPlatformsSchema

from src.utils.api_response import APIResponse

import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2.credentials import Credentials


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
        parser.add_argument('active', required=True, type=bool, help='Active required!')
        parser.add_argument('title', required=True, help='Title required!')
        parser.add_argument('description', required=True, help='Description required!')
        parser.add_argument('custom_rtmp', type=bool, help='Active required!')
        parser.add_argument('rtmp_address')
        parser.add_argument('frame_rate')
        parser.add_argument('resolution')
        parser.add_argument('game_id')
        parser.add_argument('channel_name')
        parser.add_argument('ingestion_address')
        data = parser.parse_args()

        session_user = UserModel.get_first([
            UserModel.email == get_jwt_identity()
        ])

        try:
            channel_id = session_user.email
            channel_name = session_user.name
            extra = {}

            if data['service'] == 'VokalNow':
                stream_key = session_user.user_id
                ingestion_address = 'rtmp://stream.vokalcdn.com'
            elif data['service'] == 'Youtube':
                info = {
                    'refresh_token': data['refresh_token'],
                    "client_id": app.config['GOOGLE_CLIENT_ID'],
                    "client_secret": app.config['GOOGLE_CLIENT_SECRET'],
                }
                credentials = Credentials.from_authorized_user_info(info)
                youtube = googleapiclient.discovery.build("youtube", "v3", credentials=credentials, cache_discovery=False)

                request = youtube.liveBroadcasts().insert(
                    part="snippet,contentDetails,status",
                    body={
                        "snippet": {
                            "title": f"{data['title']}",
                            "description": f"{data['description']}",
                            "scheduledStartTime": f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
                        },
                        "contentDetails": {
                            "startWithSlate": True,
                            "enableAutoStart": True,
                            "enableAutoStop": True
                        },
                        "status": {
                            "privacyStatus": "public",
                            "selfDeclaredMadeForKids": False
                        }
                    }
                )
                try:
                    broadcast_response = request.execute()
                except Exception as e:
                    return APIResponse.error_400("The user is not enabled for live streaming.")

                request = youtube.liveStreams().insert(
                    part="snippet,cdn,contentDetails,status",
                    body={
                        "snippet": {
                            "title": f"{data['title']}",
                            "description": f"{data['description']}"
                        },
                        "cdn": {
                            "frameRate": f"{data['frame_rate']}fps",
                            "ingestionType": "rtmp",
                            "resolution": f"{data['resolution']}p"
                        },
                        "contentDetails": {
                            "isReusable": True
                        },
                    }
                )
                try:
                    stream_response = request.execute()
                except Exception as e:
                    return APIResponse.error_400("The user is not enabled for live streaming.")

                stream_key = stream_response['cdn']['ingestionInfo']['streamName']
                ingestion_address = stream_response['cdn']['ingestionInfo']['ingestionAddress']
                channel_id = stream_response['snippet']['channelId']
                channel_name = data['channel_name']

                extra = {
                    'resolution': data['resolution'],
                    'frame_rate': data['frame_rate'],
                    'broadcast_id': broadcast_response['id'],
                    'stream_id': stream_response['id']
                }

                request = youtube.liveBroadcasts().bind(
                    id=broadcast_response['id'],
                    part="snippet",
                    streamId=stream_response['id']
                )
                request.execute()

                channels = StreamingPlatformsModel.filter_all([
                    StreamingPlatformsModel.user_id == session_user.id,
                    StreamingPlatformsModel.service == data['service'],
                    StreamingPlatformsModel.channel_id == stream_response['snippet']['channelId']
                ])
                if len(channels) > 0:
                    return APIResponse.error_409('Channel already connected')
            elif data['service'] == 'Twitch':
                url = "https://id.twitch.tv/oauth2/token"
                params = {
                    'grant_type': 'refresh_token',
                    'refresh_token': data['refresh_token'],
                    'client_id': app.config['TWITCH_CLIENT_ID'],
                    'client_secret': app.config['TWITCH_CLIENT_SECRET']
                }
                r = requests.post(url, params=params)
                if r.status_code != 200:
                    return APIResponse.error_500("Failed connection to Twitch")
                token = r.json()

                headers = {
                    'Authorization': f'Bearer {token["access_token"]}',
                    'Client-ID': f'{app.config["TWITCH_CLIENT_ID"]}'
                }
                r = requests.get('https://api.twitch.tv/helix/users', headers=headers)
                if r.status_code == 200:
                    broadcaster = r.json()['data'][0]
                else:
                    return APIResponse.error_500("Failed to get broadcaster")

                url = f'https://api.twitch.tv/helix/streams/key?broadcaster_id={broadcaster["id"]}'
                r = requests.get(url, headers=headers)
                stream_key = None
                if r.status_code == 200:
                    stream_key = r.json()['data'][0]
                else:
                    APIResponse.error_500("Failed to get stream key")

                url = f'https://api.twitch.tv/helix/channels?broadcaster_id={broadcaster["id"]}'
                payload = {
                    "game_id": data['game_id'],
                    "title": data['title'],
                    "broadcaster_language": "en"
                }
                r = requests.patch(url, data=payload, headers=headers)
                if r.status_code != 204:
                    return APIResponse.error_500("Failed to update channel")

                url = f'https://api.twitch.tv/helix/channels?broadcaster_id={broadcaster["id"]}'
                r = requests.get(url, headers=headers)
                if r.status_code == 200:
                    channel = r.json()['data'][0]
                else:
                    return APIResponse.error_500("Failed to get channel information")

                channel_id = channel['broadcaster_name']
                channel_name = channel['game_name']
                stream_key = stream_key['stream_key']
                ingestion_address = data['ingestion_address']
                extra = {
                    'game_id': int(channel['game_id']),
                    'broadcaster_id': str(channel['broadcaster_id']),
                }
            else:
                return APIResponse.error_400("Service not support")

            streaming_platform = StreamingPlatformsModel(
                id=str(uuid.uuid4().hex),
                user_id=session_user.id,
                active=data['active'],
                service=data['service'],
                service_email=data['service_email'],
                image=data['image'],
                stream_key=stream_key,
                ingestion_address=ingestion_address,
                channel_id=channel_id,
                channel_name=channel_name,
                title=data['title'],
                description=data['description'],
                refresh_token=data['refresh_token'],
                extra=extra,
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
        parser.add_argument('active', required=True, type=bool, help='Active required!')
        parser.add_argument('title', required=True, help='Title required!')
        parser.add_argument('description', required=True, help='Description required!')
        parser.add_argument('frame_rate')
        parser.add_argument('resolution')
        parser.add_argument('game_id')
        parser.add_argument('ingestion_address')
        data = parser.parse_args()

        try:
            streaming_platform = StreamingPlatformsModel.filter_first([
                StreamingPlatformsModel.id == id
            ])
            if streaming_platform is None:
                return APIResponse.error_404('Streaming platform not found')

            if data['service'] == 'VokalNow':
                pass
            elif data['service'] == 'Youtube':
                info = {
                    'refresh_token': streaming_platform.refresh_token,
                    "client_id": app.config['GOOGLE_CLIENT_ID'],
                    "client_secret": app.config['GOOGLE_CLIENT_SECRET'],
                }
                credentials = Credentials.from_authorized_user_info(info)
                youtube = googleapiclient.discovery.build("youtube", "v3", credentials=credentials, cache_discovery=False)

                request = youtube.liveBroadcasts().update(
                    part="id, snippet",
                    body={
                        'id': streaming_platform.extra['broadcast_id'],
                        "snippet": {
                            "title": f"{data['title']}",
                            "description": f"{data['description']}",
                            "scheduledStartTime": f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
                        },
                    }
                )
                request.execute()

                if data['frame_rate'] is None or data['resolution'] is None:
                    part = "id, snippet"
                    body = {
                        'id': streaming_platform.extra['stream_id'],
                        "snippet": {
                            "title": f"{data['title']}",
                            "description": f"{data['description']}"
                        },
                    }
                else:
                    part = "id, snippet, cdn"
                    body = {
                        'id': streaming_platform.extra['stream_id'],
                        "snippet": {
                            "title": f"{data['title']}",
                            "description": f"{data['description']}"
                        },
                        "cdn": {
                            "frameRate": f"{data['frame_rate']}fps",
                            "ingestionType": "rtmp",
                            "resolution": f"{data['resolution']}p"
                        }
                    }
                request = youtube.liveStreams().update(part=part, body=body)
                request.execute()

                extra = streaming_platform.extra
                extra['frame_rate'] = data['frame_rate']
                extra['resolution'] = data['resolution']
                streaming_platform.extra = extra
            if data['service'] == 'Twitch':
                url = "https://id.twitch.tv/oauth2/token"
                params = {
                    'grant_type': 'refresh_token',
                    'refresh_token': streaming_platform.refresh_token,
                    'client_id': app.config['TWITCH_CLIENT_ID'],
                    'client_secret': app.config['TWITCH_CLIENT_SECRET']
                }
                r = requests.post(url, params=params)
                if r.status_code != 200:
                    return APIResponse.error_500("Failed connection to Twitch")

                token = r.json()
                streaming_platform.refresh_token = token['refresh_token']

                headers = {
                    'Authorization': f'Bearer {token["access_token"]}',
                    'Client-ID': f'{app.config["TWITCH_CLIENT_ID"]}'
                }
                url = f"https://api.twitch.tv/helix/channels?broadcaster_id={streaming_platform.extra['broadcaster_id']}"

                payload = {
                    "game_id": streaming_platform.extra['game_id'],
                    "title": data['title'],
                    "broadcaster_language": "en"
                }
                if data['game_id'] != streaming_platform.extra['game_id']:
                    streaming_platform.extra['game_id'] = data['game_id']
                    payload['game_id'] = data['game_id']

                r = requests.patch(url, data=payload, headers=headers)
                if r.status_code != 204:
                    return APIResponse.error_500("Failed to update channel")

                url = f"https://api.twitch.tv/helix/channels?broadcaster_id={streaming_platform.extra['broadcaster_id']}"
                r = requests.get(url, headers=headers)
                if r.status_code == 200:
                    channel = r.json()['data'][0]
                else:
                    return APIResponse.error_500("Failed to get channel information")

                streaming_platform.channel_id = channel['broadcaster_name']
                streaming_platform.channel_name = channel['game_name']
                streaming_platform.ingestion_address = data['ingestion_address']
            else:
                APIResponse.error_400("Unsupported service!")

            streaming_platform.title = data['title']
            streaming_platform.description = data['description']
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


class GetConnectedRTMPLinksResource(Resource):
    def get(self, user_id):
        try:
            session_user = UserModel.get_first([
                UserModel.user_id == user_id
            ])

            streaming_platform_list = StreamingPlatformsModel.filter_all([
                StreamingPlatformsModel.user_id == session_user.id
            ])

            streaming_platforms = []
            for streaming_platform in streaming_platform_list:
                item = {
                    'service': streaming_platform.service,
                    'rtmp_address': f"{streaming_platform.ingestion_address}/{streaming_platform.stream_key}",
                    'channel_id': streaming_platform.channel_id,
                    'channel_name': streaming_platform.channel_name
                }

                if item['service'] == "Twitch":
                    item['rtmp_address'] = f"rtmp://{item['rtmp_address']}"

                streaming_platforms.append(item)

            response = jsonify(streaming_platforms)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()
