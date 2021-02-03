import uuid
import json
from datetime import datetime
from flask import make_response, jsonify
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.users import UserModel
from src.models.payments import PaymentsModel
from src.schemas.payments import PaymentsSchema

from src.utils.api_response import APIResponse


class GetPaymentResource(Resource):
    @jwt_required
    def get(self, id):
        try:
            payment_obj = PaymentsModel.filter_first([
                PaymentsModel.id == id
            ])

            if payment_obj is None:
                return APIResponse.error_404()

            payment = PaymentsSchema().dumps(payment_obj)
            response = jsonify(json.loads(payment))
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class GetPaymentsResource(Resource):
    @jwt_required
    def get(self):
        try:
            user = UserModel.get_first([
                UserModel.email == get_jwt_identity()
            ])

            if user.role == 'Admin':
                payment_list = PaymentsModel.filter_all([])
            else:
                payment_list = PaymentsModel.filter_all([
                    PaymentsModel.user_id == user.id
                ])

            payments = PaymentsSchema().dumps(payment_list, many=True)
            response = jsonify(json.loads(payments))
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class DeletePaymentsResource(Resource):
    @jwt_required
    def delete(self, id):
        try:
            payment = PaymentsModel.filter_first([
                PaymentsModel.id == id
            ])

            if payment is None:
                return APIResponse.error_404()

            payment.delete()
            response = {'message': 'Payment deleted!'}
            return make_response(response, 204)

        except Exception as e:
            print(e)
            return APIResponse.error_500()
