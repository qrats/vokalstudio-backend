import os
import json
from datetime import datetime
from flask import make_response, jsonify
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.blogs import BlogsModel
from src.schemas.blogs import BlogsSchema

from src.utils.api_response import APIResponse


class GetBlogResource(Resource):
    @jwt_required
    def get(self, slug):
        try:
            blog_obj = BlogsModel.filter_first([
                BlogsModel.slug == slug,
                BlogsModel.status == 'published'
            ])

            if blog_obj is None:
                return APIResponse.error_404()

            blog = BlogsSchema().dumps(blog_obj)
            response = jsonify(json.loads(blog))
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class GetBlogsResource(Resource):
    @jwt_required
    def get(self):
        try:
            blog_list = BlogsModel.filter_all([
                BlogsModel.status == 'published'
            ])

            blogs = BlogsSchema().dumps(blog_list, many=True)
            response = jsonify(json.loads(blogs))
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()
