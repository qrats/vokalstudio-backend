import boto3
from boto3.s3.transfer import S3Transfer
from flask import current_app as app


def create_signed_post_data(bucket_name, key_name):
    s3 = boto3.client(
        's3',
        region_name='us-east-1',
        aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY']
    )

    # Make sure everything posted is publicly readable
    fields = {"acl": "public-read"}

    # Ensure that the ACL isn't changed and restrict the user to a length
    # between 10 and 100.
    conditions = [
        {"acl": "public-read"},
        ["content-length-range", 1, 20000000000]  # 20GB
        # i changed this from 10-100 to 1-1048576 i'm quite sure these are bytes.
    ]

    # Generate the POST attributes
    signed_data = s3.generate_presigned_post(
        Bucket=bucket_name,
        Key=key_name,
        Fields=fields,
        Conditions=conditions,
        ExpiresIn=36000
    )

    return signed_data


def download_file(bucket, key, local_path):
    s3 = boto3.client(
        's3',
        region_name='us-east-1',
        aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY']
    )
    s3.download_file(bucket, key, local_path)


def upload_file(local_path, bucket, key):
    s3 = boto3.client(
        's3',
        region_name='us-east-1',
        aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY']
    )
    S3Transfer(s3).upload_file(local_path, bucket, key)
