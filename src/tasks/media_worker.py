import os
from datetime import datetime
import subprocess
from app import celery
from src.utils.s3 import download_file, upload_file
from src.models.media_objects import MediaObjectsModel


def get_length(media_path):
    try:
        """ Get and Update length """
        a = str(subprocess.check_output('/usr/bin/ffprobe -i  "' + media_path + '" 2>&1 | /usr/bin/grep "Duration"',
                                        shell=True))
        a = a.split(",")[0].split("Duration:")[1].strip()
        length = a.split('.')[0]
        print(f"Length: {length}")
        length = datetime.strptime(length, '%H:%M:%S').time()
        return length
    except Exception as e:
        print(e)


@celery.task()
def media_processor(media_id):
    try:
        media = MediaObjectsModel.filter_first([
            MediaObjectsModel.id == media_id
        ])

        print(f"Start: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}, {media.url}")
        file_name = media.url.split('/')[-1]
        media_path = f"/tmp/{file_name}"

        if file_name.endswith('.mp3'):
            media_bucket = 'virtualstudio-audio'
            media_key = 'audio/' + file_name
        else:
            media_bucket = 'virtualstudio-video'
            media_key = 'video/' + file_name

        download_file(media_bucket, media_key, media_path)
        media.length = get_length(media_path)
        media.save()

        os.remove(media_path)
        print(f"End: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(e)


@celery.task()
def media_uploader(media_id):
    try:
        media = MediaObjectsModel.filter_first([
            MediaObjectsModel.id == media_id
        ])

        print(f"Start: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}, {media.url}")
        file_name = media.url.split('/')[-1]

        media_path = f"/tmp/{file_name}"
        media_bucket = f"virtualstudio-{media.type}"
        media_key = f"{media.type}/{file_name}"

        upload_file(media_path, media_bucket, media_key)
        if media.type != "image":
            media.length = get_length(media_path)
            media.save()

        os.remove(media_path)
        print(f"End: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(e)
