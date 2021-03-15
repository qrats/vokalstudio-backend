import os
import json
from datetime import datetime
import subprocess
import requests
from app import celery
from src.utils.s3 import download_file, upload_file
from src.models.episodes import EpisodesModel
from src.models.uploading_platforms import UploadingPlatformsModel
from src.models.users import UserModel
from flask import current_app as app

import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload


@celery.task()
def video_processor(episode_id, episode_url):
    try:
        print(f"start: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}, {episode_url}")
        file_name = episode_url.split('/')[-1]
        extension = file_name.split('.')[-1]
        video_bucket = 'virtualstudio-video'
        audio_bucket = 'virtualstudio-audio'
        video_key = 'video/' + file_name
        audio_key = 'audio/' + file_name.replace(f'.{extension}', '.mp3')
        video_path = f"/tmp/{file_name}"
        audio_path = video_path.replace(f'.{extension}', '.mp3')

        download_file(video_bucket, video_key, video_path)

        """ Convert and Upload audio version """
        cmd = ["/usr/bin/ffmpeg", "-i", "{}".format(video_path), "-f", "mp3", "-ab", "192000", "-vn",
               "{}".format(audio_path), "-y"]
        subprocess.call(cmd)

        upload_file(audio_path, audio_bucket, audio_key)

        """ Upload on services if active """
        episode = EpisodesModel.filter_first([
            EpisodesModel.id == episode_id
        ])

        """ Upload on vokalnow if active """
        platform = UploadingPlatformsModel.filter_first([
            UploadingPlatformsModel.service == 'VokalNow',
            UploadingPlatformsModel.user_id == episode.uploader_id,
            UploadingPlatformsModel.active == True
        ])
        if platform is not None:
            uploader = UserModel.get_first([
                UserModel.id == platform.user_id
            ])
            payload = {
                'show_id': uploader.user_id,
                'title': episode.title,
                'description': episode.description,
                'premium': 'free',
                'publish_time': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                'status': 'pending',
                'episode_bucket': 'virtualstudio-video',
                'episode_path': video_key,
                'premiere': False,
                'indexed': '#'
            }
            if episode.image is not None:
                payload['image_bucket'] = 'virtualstudio-image'
                payload['image_path'] = f"image/{os.path.basename(episode.image)}"

            ret = requests.post('https://api.vokalnow.com/api/studio/episodes', data=payload)
            print(ret.text)

        """ Upload on youtube if active """
        platform = UploadingPlatformsModel.filter_first([
            UploadingPlatformsModel.service == 'Youtube',
            UploadingPlatformsModel.user_id == episode.uploader_id,
            UploadingPlatformsModel.active == True
        ])

        if platform is not None:
            upload_to_youtube(video_path, platform.refresh_token, episode.title, episode.description)

        """ Upload on podbean if active """
        platform = UploadingPlatformsModel.filter_first([
            UploadingPlatformsModel.service == 'PodBean',
            UploadingPlatformsModel.user_id == episode.uploader_id,
            UploadingPlatformsModel.active == True
        ])
        if platform is not None:
            upload_to_podbean(episode.url, episode.image, platform.refresh_token, episode.title, episode.description)

        os.remove(video_path)
        os.remove(audio_path)

        print(f"End: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(e)

@celery.task()
def audio_processor(episode_id, episode_url):
    try:
        print(f"start: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}, {episode_url}")
        file_name = episode_url.split('/')[-1]
        audio_path = f"/tmp/{file_name}"
        audio_bucket = 'virtualstudio-audio'
        audio_key = 'audio/' + file_name

        download_file(audio_bucket, audio_key, audio_path)

        """ Upload on connected services """
        episode = EpisodesModel.filter_first([
            EpisodesModel.id == episode_id
        ])

        """ Upload on vokalnow if active """
        platform = UploadingPlatformsModel.filter_first([
            UploadingPlatformsModel.service == 'VokalNow',
            UploadingPlatformsModel.user_id == episode.uploader_id,
            UploadingPlatformsModel.active == True
        ])
        if platform is not None:
            uploader = UserModel.get_first([
                UserModel.id == platform.user_id
            ])
            payload = {
                'show_id': uploader.user_id,
                'title': episode.title,
                'description': episode.description,
                'premium': 'free',
                'publish_time': datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                'status': 'pending',
                'episode_bucket': 'virtualstudio-audio',
                'episode_path': audio_key,
                'premiere': False,
                'indexed': '#'
            }
            if episode.image is not None:
                payload['image_bucket'] = 'virtualstudio-image'
                payload['image_path'] = f"image/{os.path.basename(episode.image)}"

            ret = requests.post('https://api.vokalnow.com/api/studio/episodes', data=payload)
            print(ret.text)

        """ Upload on podbean if active """
        platform = UploadingPlatformsModel.filter_first([
            UploadingPlatformsModel.service == 'PodBean',
            UploadingPlatformsModel.user_id == episode.uploader_id,
            UploadingPlatformsModel.active == True
        ])
        if platform is not None:
            upload_to_podbean(episode.url, episode.image, platform.refresh_token, episode.title, episode.description)

        os.remove(audio_path)
        print(f"End: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(e)


def upload_to_youtube(video_path, refresh_token, title, description):

    credentials = Credentials.from_authorized_user_info({
        'refresh_token': refresh_token,
        "client_id": app.config['GOOGLE_CLIENT_ID'],
        "client_secret": app.config['GOOGLE_CLIENT_SECRET'],
    })
    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=credentials, cache_discovery=False)

    body = dict(
        snippet=dict(
            title=title,
            description=description,
        ),
        status=dict(
            privacyStatus='public'  # public, private, unlisted
        )
    )

    response = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True)
    ).execute()
    print(response)


def upload_to_podbean(audio_url, image_url, refresh_token, title, description):
    try:
        auth = (app.config['PODBEAN_CLIENT_ID'], app.config['PODBEAN_CLIENT_SECRET'])
        url = 'https://api.podbean.com/v1/oauth/token'
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }

        r = requests.post(url, auth=auth, data=data)
        token = json.loads(r.content)

        url = 'https://api.podbean.com/v1/episodes'
        data = {
            'access_token': token['access_token'],
            'title': title,
            'content': description,
            'status': 'publish',
            'type': 'public',
            'remote_media_url': audio_url
        }
        if image_url is not None:
            data['logo_key'] = image_url
        r = requests.post(url, auth=auth, data=data)
        print(r.content)
    except Exception as e:
        print(e)
