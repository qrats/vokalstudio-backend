import os
from datetime import datetime
import subprocess
from app import celery
from src.utils.s3 import download_file, upload_file
from src.models.uploading_platforms import UploadingPlatformsModel
from flask import current_app as app

import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload


@celery.task()
def video_processor(episode):
    try:
        print(f"start: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}, {episode.url}")
        file_name = episode.url.split('/')[-1]
        extension = file_name.split('.')[-1]
        video_bucket = 'virtualstudio-video'
        audio_bucket = 'virtualstudio-audio'
        video_key = 'video/' + file_name
        audio_key = 'audio/' + file_name.replace(f'.{extension}', '.mp3')
        video_path = f"/tmp/{file_name}"
        audio_path = video_path.replace(f'.{extension}', '.mp3')

        download_file(video_bucket, video_key, video_path)

        """ Get and Update length """
        a = str(subprocess.check_output('/usr/bin/ffprobe -i  "' + video_path + '" 2>&1 | /usr/bin/grep "Duration"', shell=True))
        a = a.split(",")[0].split("Duration:")[1].strip()
        length = a.split('.')[0]
        print(f"Length: {length}")
        episode.length = datetime.strptime(length, '%H:%M:%S').time()
        episode.save()

        """ Convert and Upload audio version """
        cmd = ["/usr/bin/ffmpeg", "-i", "{}".format(video_path), "-f", "mp3", "-ab", "192000", "-vn",
               "{}".format(audio_path), "-y"]
        subprocess.call(cmd)

        upload_file(audio_path, audio_bucket, audio_key)

        """ Upload on youtube if active """
        platform = UploadingPlatformsModel.filter_first([
            UploadingPlatformsModel.service == 'Youtube',
            UploadingPlatformsModel.user_id == episode.uploader_id,
            UploadingPlatformsModel.active == True
        ])

        if platform is not None:
            upload_to_youtube(video_path, platform.refresh_token, episode.title, episode.description)

        os.remove(video_path)
        os.remove(audio_path)

        print(f"End: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(e)


def audio_processor(episode):
    try:
        print(f"start: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}, {episode.url}")
        file_name = episode.url.split('/')[-1]
        audio_path = f"/tmp/{file_name}"
        audio_bucket = 'virtualstudio-audio'
        audio_key = 'audio/' + file_name

        download_file(audio_bucket, audio_key, audio_path)

        """ Get and Update length """
        a = str(subprocess.check_output('/usr/bin/ffprobe -i  "' + audio_path + '" 2>&1 | /usr/bin/grep "Duration"', shell=True))
        a = a.split(",")[0].split("Duration:")[1].strip()
        length = a.split('.')[0]
        print(f"Length: {length}")
        episode.length = datetime.strptime(length, '%H:%M:%S').time()
        episode.save()

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
    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

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
