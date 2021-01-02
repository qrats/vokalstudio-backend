import os
from datetime import datetime
import subprocess
from app import celery
from src.utils.s3 import download_file


@celery.task()
def media_processor(media):
    try:
        print(f"start: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}, {media.url}")
        file_name = media.url.split('/')[-1]
        media_path = f"/tmp/{file_name}"

        if file_name.endswith('.mp3'):
            media_bucket = 'virtualstudio-audio'
            media_key = 'audio/' + file_name
        else:
            media_bucket = 'virtualstudio-video'
            media_key = 'video/' + file_name


        download_file(media_bucket, media_key, media_path)

        """ Get and Update length """
        a = str(subprocess.check_output('/usr/bin/ffprobe -i  "' + media_path + '" 2>&1 | /usr/bin/grep "Duration"', shell=True))
        a = a.split(",")[0].split("Duration:")[1].strip()
        length = a.split('.')[0]
        print(f"Length: {length}")
        media.length = datetime.strptime(length, '%H:%M:%S').time()
        media.save()

        os.remove(media_path)
        print(f"End: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}")
    except Exception as e:
        print(e)
