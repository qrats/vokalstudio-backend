import json
from urllib import parse
from datetime import datetime
from flask import make_response, jsonify
from flask import current_app as app
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.models.users import UserModel, UserRole
from src.models.plans import PlansModel
from src.models.subscriptions import SubscriptionsModel
from src.models.streaming_platforms import StreamingPlatformsModel
from src.models.uploading_platforms import UploadingPlatformsModel


from src.schemas.subscriptions import SubscriptionsSchema

from src.utils.api_response import APIResponse
from src.utils.paypal.subscription import Subscription as PaypalSubscription


class GetSubscriptionsResource(Resource):
    @jwt_required
    def get(self):
        try:
            session_user = UserModel.get_first([
                UserModel.email == get_jwt_identity()
            ])

            if app.config['PAYPAL_MODE'] == 'sandbox':
                subscription_list = SubscriptionsModel.filter_all([
                    SubscriptionsModel.sandbox == True,
                    SubscriptionsModel.status != 'APPROVAL_PENDING',
                    SubscriptionsModel.user_id == session_user.id
                ])
            else:
                subscription_list = SubscriptionsModel.filter_all([
                    SubscriptionsModel.sandbox == False,
                    SubscriptionsModel.status != 'APPROVAL_PENDING',
                    SubscriptionsModel.user_id == session_user.id
                ])

            subscriptions = SubscriptionsSchema().dumps(subscription_list, many=True)
            response = jsonify(json.loads(subscriptions))
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class CreateSubscriptionResource(Resource):
    @jwt_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('plan_name', required=True, help='plan_name required!')
        parser.add_argument('return_url', required=True, help='return_url required!')
        parser.add_argument('cancel_url', required=True, help='cancel_url required!')
        data = parser.parse_args()

        try:
            session_user = UserModel.get_first([
                UserModel.email == get_jwt_identity()
            ])

            if app.config['PAYPAL_MODE'] == 'sandbox':
                plan = PlansModel.filter_first([
                    PlansModel.sandbox == True,
                    PlansModel.name == data['plan_name']
                ])
            else:
                plan = PlansModel.filter_first([
                    PlansModel.sandbox == False,
                    PlansModel.name == data['plan_name']
                ])

            application_context = {
                "brand_name": "Vokal Studio",
                "locale": "en-US",
                "shipping_preference": "NO_SHIPPING",
                "user_action": "SUBSCRIBE_NOW",
                "payment_method": {
                    "payer_selected": "PAYPAL",
                    "payee_preferred": "IMMEDIATE_PAYMENT_REQUIRED"
                },
                "return_url": data['return_url'],
                "cancel_url": data['cancel_url']
            }

            sub = PaypalSubscription(
                plan_id=plan.id,
                application_context=application_context
            )

            s = sub.create()

            s_details = sub.details(s['id'])

            s_obj = SubscriptionsModel(
                id=s_details['id'],
                user_id=session_user.id,
                plan_id=plan.id,
                status=s_details['status'],
                links=s_details['links'],
                start_time=datetime.strptime(s_details['start_time'], '%Y-%m-%dT%H:%M:%SZ'),
                create_time=datetime.strptime(s_details['create_time'], '%Y-%m-%dT%H:%M:%SZ')
            )

            if app.config['PAYPAL_MODE'] == 'sandbox':
                s_obj.sandbox = True
            else:
                s_obj.sandbox = False

            s_obj.save()

            approve_link = next(item for item in s_details['links'] if item["rel"] == "approve")
            return make_response(approve_link, 201)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class UpdateSubscriptionResource(Resource):
    @jwt_required
    def put(self, id):
        parser = reqparse.RequestParser()
        parser.add_argument('ba_token', required=True, help='ba_token required!')
        parser.add_argument('token', required=True, help='token required!')
        data = parser.parse_args()

        try:
            session_user = UserModel.get_first([
                UserModel.email == get_jwt_identity()
            ])

            if app.config['PAYPAL_MODE'] == 'sandbox':
                subscription = SubscriptionsModel.filter_first([
                    SubscriptionsModel.user_id == session_user.id,
                    SubscriptionsModel.id == id,
                    SubscriptionsModel.sandbox == True
                ])
            else:
                subscription = SubscriptionsModel.filter_first([
                    SubscriptionsModel.user_id == session_user.id,
                    SubscriptionsModel.id == id,
                    SubscriptionsModel.sandbox == False
                ])

            approve_link = next(item for item in subscription.links if item["rel"] == "approve")
            ba_token = parse.parse_qs(parse.urlparse(approve_link['href']).query)['ba_token'][0]
            if ba_token != data['ba_token']:
                return APIResponse.error_403()

            sub = PaypalSubscription(plan_id=subscription.plan_id)
            s_details = sub.details(id)

            subscription.status = s_details['status']
            subscription.subscriber = s_details['subscriber']
            subscription.billing_info = s_details['billing_info']
            subscription.links = s_details['links']
            subscription.update_time = datetime.strptime(s_details['update_time'], '%Y-%m-%dT%H:%M:%SZ')
            subscription.save()

            # Remove pending approvals
            if app.config['PAYPAL_MODE'] == 'sandbox':
                subscriptions = SubscriptionsModel.filter_all([
                    SubscriptionsModel.user_id == session_user.id,
                    SubscriptionsModel.status == 'APPROVAL_PENDING',
                    SubscriptionsModel.sandbox == True
                ])
            else:
                subscriptions = SubscriptionsModel.filter_first([
                    SubscriptionsModel.user_id == session_user.id,
                    SubscriptionsModel.status == 'APPROVAL_PENDING',
                    SubscriptionsModel.sandbox == False
                ])

            for sub in subscriptions:
                sub.delete()

            # Unsubscribe non-PRO
            if subscription.plan.name == 'PRO' and subscription.status == 'ACTIVE':
                if app.config['PAYPAL_MODE'] == 'sandbox':
                    subscriptions = SubscriptionsModel.filter_all([
                        SubscriptionsModel.user_id == session_user.id,
                        SubscriptionsModel.status == 'ACTIVE',
                        SubscriptionsModel.sandbox == True
                    ])
                else:
                    subscriptions = SubscriptionsModel.filter_first([
                        SubscriptionsModel.user_id == session_user.id,
                        SubscriptionsModel.status == 'ACTIVE',
                        SubscriptionsModel.sandbox == False
                    ])

                for sub in subscriptions:
                    if sub.plan.name != 'PRO':
                        s = PaypalSubscription(plan_id=sub.plan_id)
                        s.unsubscribe(sub.id)

                        s_details = s.details(sub.id)
                        sub.status = s_details['status']
                        sub.update_time = datetime.strptime(s_details['update_time'], '%Y-%m-%dT%H:%M:%SZ')
                        sub.save()

            result = SubscriptionsSchema().dumps(subscription)
            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class CancelSubscriptionResource(Resource):
    @jwt_required
    def get(self, id):
        try:
            session_user = UserModel.get_first([
                UserModel.email == get_jwt_identity()
            ])

            if app.config['PAYPAL_MODE'] == 'sandbox':
                subscription = SubscriptionsModel.filter_first([
                    SubscriptionsModel.user_id == session_user.id,
                    SubscriptionsModel.id == id,
                    SubscriptionsModel.sandbox == True
                ])

                plan = PlansModel.filter_first([
                    PlansModel.id == subscription.plan_id,
                    PlansModel.sandbox == True
                ])
            else:
                subscription = SubscriptionsModel.filter_first([
                    SubscriptionsModel.user_id == session_user.id,
                    SubscriptionsModel.id == id,
                    SubscriptionsModel.sandbox == False
                ])

                plan = PlansModel.filter_first([
                    PlansModel.id == subscription.plan_id,
                    PlansModel.sandbox == False
                ])

            sub = PaypalSubscription(plan_id=subscription.plan_id)
            sub.unsubscribe(id)

            s_details = sub.details(id)
            subscription.status = s_details['status']
            subscription.update_time = datetime.strptime(s_details['update_time'], '%Y-%m-%dT%H:%M:%SZ')
            subscription.save()

            if plan.name == 'PRODUCER' or plan.name == 'PRO':
                platforms = UploadingPlatformsModel.filter_all([
                    UploadingPlatformsModel.user_id == session_user.id,
                    UploadingPlatformsModel.active == True,
                ])

                for platform in platforms:
                    platform.active = False
                    platform.save()

            if plan.name == 'SYNDICATION' or plan.name == 'PRO':
                platforms = StreamingPlatformsModel.filter_all([
                    StreamingPlatformsModel.user_id == session_user.id,
                    StreamingPlatformsModel.active == True,
                ])

                for platform in platforms:
                    platform.active = False
                    platform.save()

            result = SubscriptionsSchema().dumps(subscription)
            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class ActivateSubscriptionResource(Resource):
    @jwt_required
    def get(self, id):
        try:
            session_user = UserModel.get_first([
                UserModel.email == get_jwt_identity()
            ])

            if app.config['PAYPAL_MODE'] == 'sandbox':
                subscription = SubscriptionsModel.filter_first([
                    SubscriptionsModel.user_id == session_user.id,
                    SubscriptionsModel.id == id,
                    SubscriptionsModel.sandbox == True
                ])
            else:
                subscription = SubscriptionsModel.filter_first([
                    SubscriptionsModel.user_id == session_user.id,
                    SubscriptionsModel.id == id,
                    SubscriptionsModel.sandbox == False
                ])

            sub = PaypalSubscription(plan_id=subscription.plan_id)
            sub.resubscribe(id)

            s_details = sub.details(id)
            subscription.status = s_details['status']
            subscription.update_time = datetime.strptime(s_details['update_time'], '%Y-%m-%dT%H:%M:%SZ')
            subscription.save()

            # Unsubscribe non-PRO
            if subscription.plan.name == 'PRO' and subscription.status == 'ACTIVE':
                if app.config['PAYPAL_MODE'] == 'sandbox':
                    subscriptions = SubscriptionsModel.filter_all([
                        SubscriptionsModel.user_id == session_user.id,
                        SubscriptionsModel.status == 'ACTIVE',
                        SubscriptionsModel.sandbox == True
                    ])
                else:
                    subscriptions = SubscriptionsModel.filter_first([
                        SubscriptionsModel.user_id == session_user.id,
                        SubscriptionsModel.status == 'ACTIVE',
                        SubscriptionsModel.sandbox == False
                    ])

                for sub in subscriptions:
                    if sub.plan.name != 'PRO':
                        s = PaypalSubscription(plan_id=sub.plan_id)
                        s.unsubscribe(sub.id)

                        s_details = s.details(sub.id)
                        sub.status = s_details['status']
                        sub.update_time = datetime.strptime(s_details['update_time'], '%Y-%m-%dT%H:%M:%SZ')
                        sub.save()

            result = SubscriptionsSchema().dumps(subscription)
            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()
