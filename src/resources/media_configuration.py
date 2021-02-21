import uuid
import json
from datetime import datetime
from flask import make_response, jsonify
from flask_restful import Resource, reqparse
from flask import current_app as app
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.users import UserModel, UserRole
from src.models.media_configuration import MediaConfigurationModel
from src.models.media_objects import MediaObjectsModel

from src.schemas.media_configuration import MediaConfigurationSchema

from src.utils.api_response import APIResponse


class GetMediaConfigurationResource(Resource):
    @jwt_required
    def get(self, user_id):
        try:
            media_configuration = MediaConfigurationModel.filter_first([
                MediaConfigurationModel.user_id == user_id
            ])
            if media_configuration is None:
                session_user = UserModel.get_first([
                    UserModel.email == get_jwt_identity()
                ])

                media_configuration = MediaConfigurationModel(
                    id=str(uuid.uuid4().hex),
                    user_id=user_id,
                    obs_profilename=session_user.name,
                )
                media_configuration.save()

            result = MediaConfigurationSchema().dumps(media_configuration)
            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class GetMediaConfigurationsResource(Resource):
    @jwt_required
    def get(self):
        try:
            session_user = UserModel.get_first([
                UserModel.email == get_jwt_identity()
            ])

            media_configuration_list = MediaConfigurationModel.filter_all([
                MediaConfigurationModel.user_id == session_user.id
            ])

            media_configurations = MediaConfigurationSchema().dumps(media_configuration_list, many=True)
            response = jsonify(json.loads(media_configurations))
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class CreateMediaConfigurationResource(Resource):
    @jwt_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('user_id', type=int, required=True, help='User id required!')
        parser.add_argument('CONFIG_VERSION', type=int)
        parser.add_argument('autoSwitchEnabledAfterInto', type=bool)
        parser.add_argument('autoSwitchMinLevel', type=int)
        parser.add_argument('intro_host_scene')
        parser.add_argument('intro_mics_fadeIn_time', type=int)
        parser.add_argument('intro_start_delay_after_streaming_start', type=int)
        parser.add_argument('obs_enable_recording', type=bool)
        parser.add_argument('obs_enable_streaming', type=bool)
        parser.add_argument('obs_host')
        parser.add_argument('obs_password')
        parser.add_argument('obs_port', type=int)
        parser.add_argument('obs_profilename')
        parser.add_argument('obs_scenecollectionname')
        parser.add_argument('recording_start_delay', type=int)
        parser.add_argument('show_start_delay')
        parser.add_argument('time_to_switch_to_intro_with_host')
        data = parser.parse_args()

        session_user = UserModel.get_first([
            UserModel.email == get_jwt_identity()
        ])
        try:

            media_configuration = MediaConfigurationModel(
                id=str(uuid.uuid4().hex),
                user_id=session_user.id,
                CONFIG_VERSION=data['CONFIG_VERSION'],
                autoSwitchEnabledAfterInto=data['autoSwitchEnabledAfterInto'],
                autoSwitchMinLevel=data['autoSwitchMinLevel'],
                intro_host_scene=data['intro_host_scene'],
                intro_mics_fadeIn_time=data['intro_mics_fadeIn_time'],
                obs_enable_recording=data['obs_enable_recording'],
                obs_enable_streaming=data['obs_enable_streaming'],
                obs_host=data['obs_host'],
                obs_password=data['obs_password'],
                obs_port=data['obs_port'],
                obs_profilename=data['obs_profilename'],
                obs_scenecollectionname=data['obs_scenecollectionname'],
                recording_start_delay=data['recording_start_delay'],
                show_start_delay=data['show_start_delay'],
                time_to_switch_to_intro_with_host=data['time_to_switch_to_intro_with_host']
            )
            media_configuration.save()

            result = MediaConfigurationSchema().dumps(media_configuration)
            response = json.loads(result)
            return make_response(response, 201)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class UpdateMediaConfigurationResource(Resource):
    @jwt_required
    def put(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument('user_id', type=int, required=True, help='User id required!')
        parser.add_argument('CONFIG_VERSION', type=int)
        parser.add_argument('autoSwitchEnabledAfterInto', type=bool)
        parser.add_argument('autoSwitchMinLevel', type=int)
        parser.add_argument('intro_host_scene')
        parser.add_argument('intro_mics_fadeIn_time', type=int)
        parser.add_argument('intro_start_delay_after_streaming_start', type=int)
        parser.add_argument('obs_enable_recording', type=bool)
        parser.add_argument('obs_enable_streaming', type=bool)
        parser.add_argument('obs_host')
        parser.add_argument('obs_password')
        parser.add_argument('obs_port', type=int)
        parser.add_argument('obs_profilename')
        parser.add_argument('obs_scenecollectionname')
        parser.add_argument('recording_start_delay', type=int)
        parser.add_argument('show_start_delay')
        parser.add_argument('time_to_switch_to_intro_with_host')
        data = parser.parse_args()

        try:
            media_configuration = MediaConfigurationModel.filter_first([
                MediaConfigurationModel.id == id
            ])
            if media_configuration is None:
                return APIResponse.error_404('Media configuration not found')

            media_configuration.user_id = data['user_id']

            media_configuration.CONFIG_VERSION = data['CONFIG_VERSION']
            media_configuration.autoSwitchEnabledAfterInto = data['autoSwitchEnabledAfterInto']
            media_configuration.autoSwitchMinLevel = data['autoSwitchMinLevel']
            media_configuration.intro_host_scene = data['intro_host_scene']
            media_configuration.intro_mics_fadeIn_time = data['intro_mics_fadeIn_time']
            media_configuration.intro_start_delay_after_streaming_start = data['intro_start_delay_after_streaming_start']
            media_configuration.obs_enable_recording = data['obs_enable_recording']
            media_configuration.obs_enable_streaming = data['obs_enable_streaming']
            media_configuration.obs_host = data['obs_host']
            media_configuration.obs_password = data['obs_password']
            media_configuration.obs_port = data['obs_port']
            media_configuration.obs_profilename = data['obs_profilename']
            media_configuration.obs_scenecollectionname = data['obs_scenecollectionname']
            media_configuration.recording_start_delay = data['recording_start_delay']
            media_configuration.show_start_delay = data['show_start_delay']
            media_configuration.time_to_switch_to_intro_with_host = data['time_to_switch_to_intro_with_host']

            media_configuration.save()
            result = MediaConfigurationSchema().dumps(media_configuration)
            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class DeleteMediaConfigurationResource(Resource):
    @jwt_required
    def delete(self, id):
        try:
            media_configuration = MediaConfigurationModel.filter_first([
                MediaConfigurationModel.id == id,
            ])
            if media_configuration is None:
                return APIResponse.error_404("Media configuration not found!")

            media_configuration.delete()
            response = {'message': 'Media configuration deleted'}
            return make_response(response, 204)

        except Exception as e:
            print(e)
            return APIResponse.error_500()


class GetMediaURLsResource(Resource):
    def get(self):
        try:
            users = UserModel.get_all([])

            media_urls = []
            for user in users:
                item = {
                    'url': f"https://api.vokalstudio.com/api/media/configuration/{user.user_id}",
                    'name': user.name
                }
                media_urls.append(item)

            response = jsonify(media_urls)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class LoadMediaConfigurationResource(Resource):
    def get(self, user_id):
        try:
            user = UserModel.get_first([
                UserModel.user_id == user_id
            ])
            if user is None:
                return APIResponse.error_404("User not found")

            media_list = MediaObjectsModel.filter_all([
                MediaObjectsModel.uploader_id == user.id
            ])

            media_configuration = MediaConfigurationModel.filter_first([
                MediaConfigurationModel.user_id == user.id
            ])

            if media_configuration is None:
                media_configuration = MediaConfigurationModel(
                    id=str(uuid.uuid4().hex),
                    user_id=user.id,
                    obs_profilename=user.name,
                )
                media_configuration.save()

            vcdownloads = []
            for media in media_list:
                item = {
                    'url': media.url,
                    'friendlyname': media.file_name,
                }
                if media.length is not None:
                    item['duration'] = media.length

                if media.image is not None:
                    item['image'] = media.image

                if media.url.endswith('.mp3'):
                    item['type'] = 'audio'
                elif media.url.endswith('.mp4'):
                    item['type'] = 'video'
                elif media.url.endswith('.jpg') or media.url.endswith('.png'):
                    item['type'] = 'image'
                else:
                    continue

                vcdownloads.append(item)

            response = {
                "CONFIG_VERSION": int(media_configuration.CONFIG_VERSION),
                "intro_host_scene": media_configuration.intro_host_scene,
                "time_to_switch_to_intro_with_host": media_configuration.time_to_switch_to_intro_with_host,
                "intro_mics_fadeIn_time": media_configuration.intro_mics_fadeIn_time,
                "show_start_delay": media_configuration.show_start_delay,
                "recording_start_delay": media_configuration.recording_start_delay,
                "intro_start_delay_after_streaming_start": media_configuration.intro_start_delay_after_streaming_start,
                "autoSwitchEnabledAfterInto": media_configuration.autoSwitchEnabledAfterInto,
                "autoSwitchMinLevel": media_configuration.autoSwitchMinLevel,
                "obs_host": media_configuration.obs_host,
                "obs_port": media_configuration.obs_port,
                "obs_password": media_configuration.obs_password,
                "obs_profilename": media_configuration.obs_profilename,
                "obs_scenecollectionname": media_configuration.obs_scenecollectionname,
                "obs_enable_streaming": media_configuration.obs_enable_streaming,
                "obs_enable_recording": media_configuration.obs_enable_recording,
                "channels": [
                    {
                        "name": "Intro",
                        "type": "introscene",
                        "obs_scene": "Intro",
                        "file": "intro.mp4",
                        "show_in_switcherpanel": True
                    }, {
                        "name": "Intro with Host",
                        "type": "intro_with_host",
                        "obs_scene": "Intro with Host",
                        "show_in_switcherpanel": True
                    }, {
                        "name": "Host 1",
                        "type": "host",
                        "obs_scene": "Camera 1",
                        "show_in_switcherpanel": True,
                        "xair": {
                            "channel": 1,
                            "initial_vol": 0.749
                        }
                    }, {
                        "name": "Host 2",
                        "type": "host",
                        "obs_scene": "Camera 2",
                        "show_in_switcherpanel": True,
                        "xair": {
                            "channel": 2,
                            "initial_vol": 0.749
                        }
                    }, {
                        "name": "Host 3",
                        "type": "host",
                        "obs_scene": "Camera 3",
                        "show_in_switcherpanel": True,
                        "xair": {
                            "channel": 3,
                            "initial_vol": 0.749
                        }
                    }, {
                        "name": "OBS Audio",
                        "type": "audio",
                        "show_in_switcherpanel": False,
                        "xair": {
                            "channel": 5,
                            "initial_vol": 0.749
                        }
                    }, {
                        "name": "Video Player",
                        "type": "dynamicvideo",
                        "obs_scene": "Videoplayer",
                        "obs_source_name": "Video Media Source",
                        "show_in_switcherpanel": False
                    }, {
                        "name": "Remote Guest 1",
                        "type": "remote_guest",
                        "obs_scene": "Remote Guest 1",
                        "show_in_switcherpanel": False
                    }, {
                        "name": "Outro",
                        "type": "outroscene",
                        "obs_scene": "Outro",
                        "file": "outro.mp4",
                        "show_in_switcherpanel": True
                    }, {
                        "name": "Blank",
                        "type": "blankscene",
                        "obs_scene": "Blank",
                        "show_in_switcherpanel": True
                    }
                ],
                "filejobs": [
                    {
                        "job": "copy",
                        "src": "Audio/womp.mp3"
                    }, {
                        "job": "copy",
                        "src": "Video/intro-outro/intro.mp4"
                    }, {
                        "job": "copy",
                        "src": "Video/intro-outro/outro.mp4"
                    }, {
                        "job": "imagetovideo",
                        "src": "sourcepath+name"
                    }, {
                        "job": "audiotomp3",
                        "src": "sourcepath+name"
                    }
                ],
                "soundboard": [
                    {
                        "filename": "womp.mp3",
                        "displayname": "WOMP!"
                    }
                ],
                "dynamicvideo": [
                    {
                        "filename": "really-bad-radio-70fbfe557b6f48c7b470e7642f8b52e5.mp4",
                        "displayname": "Some Video"
                    }, {
                        "filename": "really-bad-radio-70fbfe557b6f48c7b470e7642f8b52e5.mp4",
                        "displayname": "Some Video 2"
                    }
                ],
                "projectors": [
                    {
                        "monitorID": 3,
                        "sceneName": "background",
                        "mediaSourceName": "background video",
                        "mediaSourceFileName": "bg.mp4",
                        "mediaSourceDoLoop": True
                    },
                    {
                        "monitorID": 2,
                        "sceneName": "background 2",
                        "imageSourceName": "background image",
                        "imageSourceFileName": "bg.jpg"
                    }
                ],
                "vcdownloads": vcdownloads,
            }

            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()
