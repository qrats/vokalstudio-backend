import json
from flask import make_response, jsonify
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required
from flask import current_app as app

from src.models.plans import PlansModel

from src.utils.api_response import APIResponse


class GetPaymentPlansResource(Resource):
    @jwt_required
    def get(self):
        try:
            if app.config['PAYPAL_MODE'] == 'sandbox':
                plan_list = PlansModel.filter_all([
                    PlansModel.sandbox == True
                ])
            else:
                plan_list = PlansModel.filter_all([
                    PlansModel.sandbox == False
                ])

            plans = []
            for plan in plan_list:
                item = {
                    'id': plan.id,
                    'name': plan.name,
                    'description': plan.description,
                    'frequency': plan.billing_cycles[0]['frequency'],
                    'pricing': plan.billing_cycles[0]['pricing_scheme']['fixed_price'],
                    'product_id': plan.product.id
                }
                plans.append(item)

            response = jsonify(plans)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()
