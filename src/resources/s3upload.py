import os
import uuid
import re
from datetime import datetime
from flask import make_response, jsonify, current_app
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required

from src.utils.api_response import APIResponse
from src.utils.s3 import create_signed_post_data


class S3SignedDataResource(Resource):
    @jwt_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('file_name', required=True, help='File name required!')
        parser.add_argument('category', required=True, help='Category required!')
        parser.add_argument('unique')
        data = parser.parse_args()

        try:
            if data['unique'].lower() == 'true':
                prefix = f"{data['file_name'].split('.')[0][:20]}~{str(uuid.uuid4().hex)}"
            else:
                prefix = f"{data['file_name'].split('.')[0]}"

            filename = f"{prefix}.{data['file_name'].split('.')[-1]}"
            filename = re.sub('\ |\?|\!|\/|\;|\:', '', filename)

            bucket_name = f"virtualstudio-{data['category']}"
            key = f"{data['category']}/{filename}"

            signed_data = create_signed_post_data(bucket_name, key)
            return make_response(signed_data, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()

    @jwt_required
    def put(self):
        parser = reqparse.RequestParser()
        parser.add_argument('file_name', required=True, help='File name required!')
        parser.add_argument('category', required=True, help='Category required!')
        parser.add_argument('url', required=True, help='Url required!')
        data = parser.parse_args()

        try:
            prefix = data['url'].split('/')[-1].split('.')[0]
            filename = f"{prefix}.{data['file_name'].split('.')[-1]}"
            filename = re.sub('\ |\?|\!|\/|\;|\:', '', filename)

            bucket_name = f"virtualstudio-{data['category']}"
            key = f"{data['category']}/{filename}"

            signed_data = create_signed_post_data(bucket_name, key)
            return make_response(signed_data, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()
