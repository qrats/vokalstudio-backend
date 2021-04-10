import os
import json
import re
from datetime import datetime
from flask import make_response, jsonify
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.blogs import BlogsModel
from src.schemas.blogs import BlogsSchema, BlogDetailSchema

from src.utils.api_response import APIResponse


class AdminGetBlogResource(Resource):
    @jwt_required
    def get(self, slug):
        try:
            blog_obj = BlogsModel.filter_first([
                BlogsModel.slug == slug
            ])

            if blog_obj is None:
                return APIResponse.error_404()

            blog = BlogDetailSchema().dumps(blog_obj)
            response = jsonify(json.loads(blog))
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class AdminGetBlogsResource(Resource):
    @jwt_required
    def get(self):
        try:
            blog_list = BlogsModel.filter_all([])

            blogs = BlogsSchema().dumps(blog_list, many=True)
            response = jsonify(json.loads(blogs))
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class AdminCreateBlogResource(Resource):
    @jwt_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('title', required=True, help='Title required!')
        parser.add_argument('content', required=True, help='Content required!')
        parser.add_argument('author')
        parser.add_argument('type')
        parser.add_argument('status')
        data = parser.parse_args()

        try:
            slug = re.sub('[^a-zA-Z0-9]', '-', data['title']).lower()
            with open(f"/tmp/{slug}.md", "w") as text_file:
                text_file.write(data['content'])
                text_file.close()

            blog = BlogsModel(
                slug=slug,
                title=data['title'],
                content=data['content'],
                author=data['author'],
                status=data['status'],
                type=data['type'],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            blog.save()

            result = BlogDetailSchema().dumps(blog)
            response = json.loads(result)
            return make_response(response, 201)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class AdminUpdateBlogResource(Resource):
    @jwt_required
    def put(self, slug):
        parser = reqparse.RequestParser()
        parser.add_argument('title', required=True, help='Title required!')
        parser.add_argument('content', required=True, help='Content required!')
        parser.add_argument('author')
        parser.add_argument('type')
        parser.add_argument('status')
        data = parser.parse_args()

        try:
            blog = BlogsModel.filter_first([
                BlogsModel.slug == slug
            ])

            if blog is None:
                return APIResponse.error_404()

            slug = re.sub('[^a-zA-Z0-9]', '-', data['title']).lower()
            with open(f"/tmp/{slug}.md", "w") as text_file:
                text_file.write(data['content'])
                text_file.close()

            blog.slug = slug
            blog.title = data['title']
            blog.content = data['content']
            blog.author = data['author']
            blog.type = data['type']
            blog.status = data['status']
            blog.updated_at = datetime.utcnow()
            blog.save()

            result = BlogDetailSchema().dumps(blog)
            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class AdminDeleteBlogResource(Resource):
    @jwt_required
    def delete(self, slug):
        try:
            blog = BlogsModel.filter_first([
                BlogsModel.slug == slug
            ])

            if blog is None:
                return APIResponse.error_404()

            os.remove(f"/tmp/{slug}.md")
            blog.delete()
            response = {'message': 'Blog deleted!'}
            return make_response(response, 204)

        except Exception as e:
            print(e)
            return APIResponse.error_500()
