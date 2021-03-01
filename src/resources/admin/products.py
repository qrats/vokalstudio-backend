import json
from datetime import datetime
from flask import make_response, jsonify
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import current_app as app

from src.models.products import ProductsModel

from src.schemas.products import ProductsSchema

from src.utils.api_response import APIResponse
from src.utils.paypal.product import Product

from src.utils.permissions import admin_required


class GetProductResource(Resource):
    @jwt_required
    @admin_required
    def get(self, id):
        """
        Get single product
        ---
        tags:
          - Product
        description: Get product by id.
        operationId: getProduct
        security:
          - bearerAuth: []
        parameters:
          - in: path
            name: id
            schema:
              type: string
            required: true
            description: Product id
        responses:
          200:
            description: Success
          401:
            description: Unauthorized.
          403:
            description: Permission denied.
          404:
            description: Product not found
          500:
            description: Internal server error
        """
        try:
            if app.config['PAYPAL_MODE'] == 'sandbox':
              product = ProductsModel.filter_first([
                  ProductsModel.id == id,
                  ProductsModel.sandbox == True
              ])
            else:
              product = ProductsModel.filter_first([
                ProductsModel.id == id,
                ProductsModel.sandbox == False
              ])

            if product is None:
                return APIResponse.error_404()

            result = ProductsSchema().dumps(product)
            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class GetProductsResource(Resource):
    @jwt_required
    @admin_required
    def get(self):
        """
        Get all products
        ---
        tags:
          - Product
        description: Get all products
        operationId: getProducts
        security:
          - bearerAuth: []
        responses:
          200:
            description: Success
          401:
            description: Unauthorized
          403:
            description: Permission denied.
          500:
            description: Internal server error
          """
        try:
            if app.config['PAYPAL_MODE'] == 'sandbox':
                product_list = ProductsModel.filter_all([
                    ProductsModel.sandbox == True
                ])
            else:
                product_list = ProductsModel.filter_all([
                    ProductsModel.sandbox == False
                ])

            products = ProductsSchema().dumps(product_list, many=True)
            response = jsonify(json.loads(products))
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class CreateProductsResource(Resource):
    @jwt_required
    @admin_required
    def post(self):
        """
        Create product
        ---
        tags:
          - Product
        description: Create product
        operationId: createProduct
        security:
          - bearerAuth: []
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  name:
                    type: string
                  type:
                    type: string
                  category:
                    type: string
                  description:
                    type: string
                  image_url:
                    type: string
                  home_url:
                    type: string
                required:
                  - name
                  - type
                  - category
                example:
                  name: New Product
                  type: SERVICE
                  category: SOFTWARE
                  description: New product description
          description: https://developer.paypal.com/docs/api/catalog-products/v1/#products_create
          required: true
        responses:
          200:
            description: Product created
          401:
            description: Unauthorized
          403:
            description: Permission denied.
          500:
            description: Internal server error
        """
        parser = reqparse.RequestParser()
        parser.add_argument('name', required=True, type=str, help='Name required!')
        parser.add_argument('type', required=True, type=int,  help='Type required!')
        parser.add_argument('category', required=True, type=str,  help='Category required!')
        parser.add_argument('description')
        parser.add_argument('image_url')
        parser.add_argument('home_url')
        data = parser.parse_args()

        try:
            product = Product(
              name=data['name'],
              description=data['description'],
            )
            if data['image_url'] is not None:
              product.image_url = data['image_url']

            if data['home_url'] is not None:
              product.image_url = data['home_url']

            prod = product.create()

            p = product.details(prod['id'])

            new_product = ProductsModel(
              id=p['id'],
              name=p['name'],
              description=p['description'],
              type=p['type'],
              category=p['category'],
              links=p['links'],
              create_time=datetime.strptime(p['create_time'], '%Y-%m-%dT%H:%M:%SZ'),
              update_time=datetime.strptime(p['update_time'], '%Y-%m-%dT%H:%M:%SZ')
            )

            if app.config['PAYPAL_MODE'] == 'sandbox':
                new_product.sandbox = True
            else:
                new_product.sandbox = False

            if 'image_url' in p:
              new_product.image_url = p['image_url']

            if 'home_url' in p:
              new_product.home_url = p['home_url']

            new_product.save()

            result = ProductsSchema().dumps(product)
            response = json.loads(result)
            return make_response(response, 201)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class UpdateProductsResource(Resource):
    @jwt_required
    @admin_required
    def put(self, id):
        """
        Update product
        ---
        tags:
          - Product
        description: Update product by id
        operationId: updateProduct
        security:
          - bearerAuth: []
        parameters:
          - in: path
            name: id
            schema:
              type: string
            required: true
            description: Product id
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  category:
                    type: string
                  description:
                    type: string
                  image_url:
                    type: string
                  home_url:
                    type: string
                required:
                  - category
                example:
                  category: SOFTWARE
                  description: New product description
          description: category must be specified.
          required: true
        responses:
          200:
            description: Product updated
          401:
            description: Unauthorized
          403:
            description: Permission denied.
          500:
            description: Internal server error
        """
        parser = reqparse.RequestParser()
        parser.add_argument('category', required=True, type=str, help='Category required!')
        parser.add_argument('description')
        parser.add_argument('image_url')
        parser.add_argument('home_url')
        data = parser.parse_args()

        try:
            if app.config['PAYPAL_MODE'] == 'sandbox':
                product = ProductsModel.filter_first([
                    ProductsModel.id == id,
                    ProductsModel.sandbox == True
                ])
            else:
                product = ProductsModel.filter_first([
                    ProductsModel.id == id,
                    ProductsModel.sandbox == False
                ])

            if product is None:
                return APIResponse.error_404('Product not found')

            prod = Product(
              name=product.name,
              description=product.description
            )

            req_data = []
            if product.description != data['description']:
                req_data.append({"op": "replace", "path": f"/description", "value": data['description']})
                product.description = data['description']

            if product.category != data['category']:
                req_data.append({"op": "replace", "path": f"/category", "value": data['category']})
                product.description = data['category']

            if product.image_url != data['image_url']:
                req_data.append({"op": "replace", "path": f"/image_url", "value": data['image_url']})
                product.description = data['image_url']

            if product.home_url != data['home_url']:
                req_data.append({"op": "replace", "path": f"/home_url", "value": data['home_url']})
                product.description = data['home_url']

            if len(req_data) > 0:
                prod.update(product.id, req_data)

                p = prod.details(product.id)
                product.update_time = datetime.strptime(p['update_time'], '%Y-%m-%dT%H:%M:%SZ')
                product.save()

            result = ProductsSchema().dumps(product)
            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class DeleteProductsResource(Resource):
    @jwt_required
    @admin_required
    def delete(self, id):
        """
        Delete product
        ---
        tags:
          - Product
        description: Delete product by id.
        operationId: deleteSubscription
        security:
          - bearerAuth: []
        parameters:
          - in: path
            name: id
            schema:
              type: string
            required: true
            description: Product id
        responses:
          204:
            description: Deleted
          401:
            description: Unauthorized.
          404:
            description: Product not found
          500:
            description: Internal server error
        """
        try:
            if app.config['PAYPAL_MODE'] == 'sandbox':
                product = ProductsModel.filter_first([
                    ProductsModel.id == id,
                    ProductsModel.sandbox == True
                ])
            else:
                product = ProductsModel.filter_first([
                    ProductsModel.id == id,
                    ProductsModel.sandbox == False
                ])

            if product is None:
                return APIResponse.error_404("Product not found!")

            product.delete()
            response = {'message': 'Product deleted'}
            return make_response(response, 204)

        except Exception as e:
            print(e)
            return APIResponse.error_500()
