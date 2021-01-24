import os
from datetime import datetime
from app import celery
from src.utils.s3 import upload_file


@celery.task()
def media_uploader(file_path):
    try:
        print(f"Start: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}, {file_path}")
        file_name = file_path.split('/')[-1]
        extension = file_name.split('.')[-1]

        if extension in ['mp3']:
            file_type = 'audio'
        elif extension in ['mp4', 'mkv', 'mov', 'flv']:
            file_type = 'video'
        else:
            file_type = 'image'

        media_path = f"/tmp/{file_name}"
        media_bucket = f"virtualstudio-{file_type}"
        media_key = f"{file_type}/{file_name}"

        upload_file(media_path, media_bucket, media_key)
        os.remove(media_path)
        print(f"End: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(e)
