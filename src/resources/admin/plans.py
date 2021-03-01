import json
from datetime import datetime
from flask import make_response, jsonify
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from flask import current_app as app

from src.models.plans import PlansModel
from src.models.products import ProductsModel

from src.schemas.plans import PlansSchema

from src.utils.api_response import APIResponse
from src.utils.paypal.plan import Plan

from src.utils.permissions import admin_required


class GetPlanResource(Resource):
    @jwt_required
    @admin_required
    def get(self, id):
        """
        Get single plan
        ---
        tags:
          - Plan
        description: Get plan by id.
        operationId: getProduct
        security:
          - bearerAuth: []
        parameters:
          - in: path
            name: id
            schema:
              type: string
            required: true
            description: Plan id
        responses:
          200:
            description: Success
          401:
            description: Unauthorized.
          403:
            description: Permission denied.
          404:
            description: Plan not found
          500:
            description: Internal server error
        """
        try:
            if app.config['PAYPAL_MODE'] == 'sandbox':
              plan = PlansModel.filter_first([
                  PlansModel.id == id,
                  PlansModel.sandbox == True
              ])
            else:
              plan = PlansModel.filter_first([
                PlansModel.id == id,
                PlansModel.sandbox == False
              ])

            if plan is None:
                return APIResponse.error_404()

            result = PlansSchema().dumps(plan)
            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class GetPlansResource(Resource):
    @jwt_required
    @admin_required
    def get(self):
        """
        Get all plans
        ---
        tags:
          - Plan
        description: Get all plans
        operationId: getPlans
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
                plan_list = PlansModel.filter_all([
                    PlansModel.sandbox == True
                ])
            else:
                plan_list = PlansModel.filter_all([
                    PlansModel.sandbox == False
                ])

            plans = PlansSchema().dumps(plan_list, many=True)
            response = jsonify(json.loads(plans))
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class CreatePlanResource(Resource):
    @jwt_required
    @admin_required
    def post(self):
        """
        Create plan
        ---
        tags:
          - Plan
        description: Create plan
        operationId: createPlan
        security:
          - bearerAuth: []
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  product_id:
                    type: string
                  name:
                    type: string
                  description:
                    type: string
                  price:
                    type: float
                required:
                  - product_id
                  - name
                  - description
                  - price
                example:
                  product_id: PROD-XXCD1234QWER65782
                  name: New Plan
                  description: New plan description
                  price: 19.0
          description: https://developer.paypal.com/docs/api/subscriptions/v1/#plans_create
          required: true
        responses:
          201:
            description: Product created
          401:
            description: Unauthorized
          403:
            description: Permission denied.
          500:
            description: Internal server error
        """
        parser = reqparse.RequestParser()
        parser.add_argument('product_id', required=True, type=str, help='Product id required!')
        parser.add_argument('name', required=True, type=str, help='Name required!')
        parser.add_argument('description', required=True, type=int,  help='Description required!')
        parser.add_argument('price', required=True, type=str, help='Price required!')
        data = parser.parse_args()

        try:
            if app.config['PAYPAL_MODE'] == 'sandbox':
                product = ProductsModel.filter_first([
                    ProductsModel.id == data['product_id'],
                    ProductsModel.sandbox == True
                ])
            else:
                product = ProductsModel.filter_first([
                    ProductsModel.id == data['product_id'],
                    ProductsModel.sandbox == False
                ])

            if product is None:
                return APIResponse.error_404("Product not found.")

            plan = Plan(
                product_id=product.id,
                name=data['name'],
                description=data['description'],
                price=str(data['price'])
            )
            pln = plan.create()

            p = plan.details(pln['id'])

            new_plan = PlansModel(
                id=p['id'],
                name=p['name'],
                description=p['description'],
                product_id=p['product_id'],
                status=p['status'],
                billing_cycles=plan.billing_cycles,
                payment_preferences=plan.payment_preferences,
                taxes=plan.taxes,
                links=p['links'],
                quantity_supported=False,
                create_time=datetime.strptime(p['create_time'], '%Y-%m-%dT%H:%M:%SZ'),
                update_time=datetime.strptime(p['update_time'], '%Y-%m-%dT%H:%M:%SZ')
            )
            new_plan.save()

            if app.config['PAYPAL_MODE'] == 'sandbox':
                new_plan.sandbox = True
            else:
                new_plan.sandbox = False

            new_plan.save()

            result = PlansSchema().dumps(plan)
            response = json.loads(result)
            return make_response(response, 201)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class UpdatePlanResource(Resource):
    @jwt_required
    @admin_required
    def put(self, id):
        """
        Update plan description
        ---
        tags:
          - Plan
        description: Update plan description by id
        operationId: updatePlan
        security:
          - bearerAuth: []
        parameters:
          - in: path
            name: id
            schema:
              type: string
            required: true
            description: Plan id
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  description:
                    type: string
                  price:
                    type: float
                example:
                  description: New plan description
                  prince: 49.0
          description: price and description specified.
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
        parser.add_argument('description', required=True, type=int, help='Description required!')
        parser.add_argument('price', required=True, type=str, help='Price required!')
        data = parser.parse_args()

        try:
            if app.config['PAYPAL_MODE'] == 'sandbox':
                plan = PlansModel.filter_first([
                    PlansModel.id == id,
                    PlansModel.sandbox == True
                ])
            else:
                plan = PlansModel.filter_first([
                    PlansModel.id == id,
                    PlansModel.sandbox == False
                ])

            if plan is None:
                return APIResponse.error_404('Plan not found')

            pln = Plan(
              product_id=plan.product_id,
              name=plan.name,
              description=plan.description
            )

            req_data = []
            if plan.description != data['description']:
                req_data.append({"op": "replace", "path": f"/description", "value": data['description']})
                plan.description = data['description']
                if not pln.update(plan.id, req_data):
                    return APIResponse.error_500("Plan update failed.")
                p = pln.details(plan.id)

                plan.update_time = datetime.strptime(p['update_time'], '%Y-%m-%dT%H:%M:%SZ')
                plan.save()

            if plan.billing_cycles[0].get('pricing_scheme').get('fixed_price').get('value') != data.get('price'):
                pricing_scheme = plan.billing_cycles[0].get('pricing_scheme')
                pricing_scheme['fixed_price']['value'] = data.get('price')
                if not pln.update_price(plan.id, pricing_schemes=[pricing_scheme]):
                    return APIResponse.error_500("Plan update failed.")

                p = pln.details(plan.id)
                plan.update_time = datetime.strptime(p['update_time'], '%Y-%m-%dT%H:%M:%SZ')
                plan.billing_cycles = p.get('billing_cycles')
                plan.save()

            result = PlansSchema().dumps(plan)
            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class UpdatePlanStatusResource(Resource):
    @jwt_required
    @admin_required
    def put(self, id):
        """
        Update plan status
        ---
        tags:
          - Plan
        description: Update plan status by id
        operationId: updatePlanStatus
        security:
          - bearerAuth: []
        parameters:
          - in: path
            name: id
            schema:
              type: string
            required: true
            description: Plan id
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    enum:
                    - ACTIVE
                    - INACTIVE
                example:
                  status: ACTIVE
          description: status must be specified.
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
        parser.add_argument('status', required=True, type=str, help='Status required!')
        data = parser.parse_args()

        try:
            if app.config['PAYPAL_MODE'] == 'sandbox':
                plan = PlansModel.filter_first([
                    PlansModel.id == id,
                    PlansModel.sandbox == True
                ])
            else:
                plan = PlansModel.filter_first([
                    PlansModel.id == id,
                    PlansModel.sandbox == False
                ])

            if plan is None:
                return APIResponse.error_404('Plan not found')

            if plan.status != data.get('status'):
                pln = Plan(
                    product_id=plan.product_id,
                    name=plan.name,
                    description=plan.description
                )

                if data.get('status') == 'ACTIVE':
                    if not pln.activate(plan.id):
                        return APIResponse.error_500("Plan activation failed.")
                else:
                    if not pln.deactivate(plan.id):
                        return APIResponse.error_500("Plan deactivation failed.")

                p = pln.details(plan.id)
                plan.update_time = datetime.strptime(p['update_time'], '%Y-%m-%dT%H:%M:%SZ')
                plan.status = p.get('status')
                plan.save()

            result = PlansSchema().dumps(plan)
            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class DeletePlanResource(Resource):
    @jwt_required
    @admin_required
    def delete(self, id):
        """
        Delete plan
        ---
        tags:
          - Plan
        description: Delete plan by id.
        operationId: deletePlan
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
                plan = PlansModel.filter_first([
                    PlansModel.id == id,
                    PlansModel.sandbox == True
                ])
            else:
                plan = PlansModel.filter_first([
                    PlansModel.id == id,
                    PlansModel.sandbox == False
                ])

            if plan is None:
                return APIResponse.error_404("Product not found!")

            if plan.status != 'INACTIVE':
                pln = Plan(
                    product_id=plan.product_id,
                    name=plan.name,
                    description=plan.description
                )
                pln.deactivate(plan.id)

            plan.delete()
            response = {'message': 'Product deleted'}
            return make_response(response, 204)

        except Exception as e:
            print(e)
            return APIResponse.error_500()
