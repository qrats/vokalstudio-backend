import uuid
import json
from datetime import datetime
from flask import make_response, jsonify
from flask_restful import Resource, reqparse
from flask import current_app as app
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.subscriptions import SubscriptionsModel
from src.models.plans import PlansModel
from src.models.users import UserModel
from src.models.restream_servers import RestreamServersModel

from src.schemas.subscriptions import AdminSubscriptionsSchema

from src.utils.api_response import APIResponse
from src.utils.paypal.subscription import Subscription
from src.utils.permissions import admin_required
from src.utils.restream_server import *


class AdminGetSubscriptionResource(Resource):
    @jwt_required
    @admin_required
    def get(self, id):
        """
        Get single subscription
        ---
        tags:
          - Subscription
        description: Get subscription by id.
        operationId: getSubscription
        security:
          - bearerAuth: []
        parameters:
          - in: path
            name: id
            schema:
              type: string
            required: true
            description: Subscription id
        responses:
          200:
            description: Success
          401:
            description: Unauthorized.
          404:
            description: Subscription not found
          500:
            description: Internal server error
        """
        try:
            if app.config['PAYPAL_MODE'] == 'sandbox':
                subscription = SubscriptionsModel.filter_first([
                    SubscriptionsModel.id == id,
                    SubscriptionsModel.sandbox == True
                ])
            else:
                subscription = SubscriptionsModel.filter_first([
                    SubscriptionsModel.id == id,
                    SubscriptionsModel.sandbox == False
                ])

            if subscription is None:
                return APIResponse.error_404()

            result = AdminSubscriptionsSchema().dumps(subscription)
            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class AdminGetSubscriptionsResource(Resource):
    @jwt_required
    @admin_required
    def get(self):
        """
        Get all subscriptions
        ---
        tags:
          - Subscription
        description: Get all subscriptions
        operationId: getSubscriptions
        security:
          - bearerAuth: []
        responses:
          200:
            description: Success
          401:
            description: Unauthorized
          500:
            description: Internal server error
          """
        try:
            if app.config['PAYPAL_MODE'] == 'sandbox':
                subscription_list = SubscriptionsModel.filter_all([
                    SubscriptionsModel.sandbox == True
                ])
            else:
                subscription_list = SubscriptionsModel.filter_all([
                    SubscriptionsModel.sandbox == False
                ])

            subscriptions = AdminSubscriptionsSchema().dumps(subscription_list, many=True)
            response = jsonify(json.loads(subscriptions))
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class AdminCreateSubscriptionResource(Resource):
    @jwt_required
    @admin_required
    def post(self):
        """
        Create subscription
        ---
        tags:
          - Subscription
        description: Create subscription
        operationId: createSubscription
        security:
          - bearerAuth: []
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  user_id:
                    type: integer
                  plan_id:
                    type: string
                  status:
                    type: string
                    enum:
                      - APPROVAL_PENDING
                      - APPROVED
                      - ACTIVE
                      - SUSPENDED
                      - CANCELLED
                      - EXPIRED
                required:
                  - user_id
                  - plan_id
                  - status
                example:
                  user_id: 5
                  plan_id: P-5ML4271244454362WXNWU5NQ
                  status: ACTIVE
          description: user_id, plan_id, status must be specified.
          required: true
        responses:
          200:
            description: Subscription created
          401:
            description: Unauthorized
          500:
            description: Internal server error
        """
        parser = reqparse.RequestParser()
        parser.add_argument('user_id', required=True, type=int, help='user_id required!')
        parser.add_argument('plan_id', required=True, type=str, help='plan_id required!')
        parser.add_argument('status', required=True, type=str,  help='status required!')
        data = parser.parse_args()

        try:
            session_user = UserModel.get_first([
                UserModel.email == get_jwt_identity()
            ])
            subscriber = {
                "name": session_user.name,
                "email_address": session_user.email,
                "payer_id": session_user.id
            }

            if app.config['PAYPAL_MODE'] == 'sandbox':
                subscription = SubscriptionsModel.filter_first([
                    SubscriptionsModel.user_id == data['user_id'],
                    SubscriptionsModel.plan_id == data['plan_id'],
                    SubscriptionsModel.sandbox == True
                ])
            else:
                subscription = SubscriptionsModel.filter_first([
                    SubscriptionsModel.user_id == data['user_id'],
                    SubscriptionsModel.plan_id == data['plan_id'],
                    SubscriptionsModel.sandbox == True
                ])

            if subscription is not None:
                return APIResponse.error_409("User already subscribed the plan.")

            subscription = SubscriptionsModel(
                id=f"{str(uuid.uuid4().hex)}",
                user_id=data['user_id'],
                plan_id=data['plan_id'],
                status=data['status'],
                billing_info=None,
                subscriber=subscriber,
                links=None,
                start_time=datetime.utcnow(),
                create_time=datetime.utcnow(),
                update_time=datetime.utcnow(),
            )

            if app.config['PAYPAL_MODE'] == 'sandbox':
                subscription.sandbox = True
            else:
                subscription.sandbox = False

            subscription.save()

            result = AdminSubscriptionsSchema().dumps(subscription)
            response = json.loads(result)
            return make_response(response, 201)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class AdminUpdateSubscriptionResource(Resource):
    @jwt_required
    @admin_required
    def put(self, id):
        """
        Update subscription
        ---
        tags:
          - Subscription
        description: Update subscription
        operationId: updateSubscription
        security:
          - bearerAuth: []
        parameters:
          - in: path
            name: id
            schema:
              type: string
            required: true
            description: Subscription id
        requestBody:
          content:
            application/json:
              schema:
                type: object
                properties:
                  status:
                    type: string
                    enum:
                      - APPROVAL_PENDING
                      - APPROVED
                      - ACTIVE
                      - SUSPENDED
                required:
                  - user_id
                  - plan_id
                  - status
                example:
                  status: SUSPENDED
          description: plan_id, status, must be specified.
          required: true
        responses:
          200:
            description: Subscription updated
          401:
            description: Unauthorized
          500:
            description: Internal server error
        """
        parser = reqparse.RequestParser()
        parser.add_argument('status', required=True, type=str, help='status required!')
        data = parser.parse_args()

        try:
            if app.config['PAYPAL_MODE'] == 'sandbox':
                subscription = SubscriptionsModel.filter_first([
                    SubscriptionsModel.id == id,
                    SubscriptionsModel.sandbox == True
                ])
            else:
                subscription = SubscriptionsModel.filter_first([
                    SubscriptionsModel.id == id,
                    SubscriptionsModel.sandbox == False
                ])

            if subscription is None:
                return APIResponse.error_404('Subscription not found')

            if app.config['PAYPAL_MODE'] == 'sandbox':
                plan_to_update = PlansModel.filter_first([
                    PlansModel.id == subscription.plan_id,
                    PlansModel.status == 'ACTIVE',
                    PlansModel.sandbox == True
                ])
            else:
                plan_to_update = PlansModel.filter_first([
                    PlansModel.id == subscription.plan_id,
                    PlansModel.status == 'ACTIVE',
                    PlansModel.sandbox == False
                ])

            if plan_to_update is None:
                return APIResponse.error_404("Plan not found.")

            if app.config['PAYPAL_MODE'] == 'sandbox':
                subscribed_list = SubscriptionsModel.filter_all([
                    SubscriptionsModel.user_id == subscription.user_id,
                    SubscriptionsModel.status == 'ACTIVE',
                    SubscriptionsModel.sandbox == True
                ])
            else:
                subscribed_list = SubscriptionsModel.filter_all([
                    SubscriptionsModel.user_id == subscription.user_id,
                    SubscriptionsModel.status == 'ACTIVE',
                    SubscriptionsModel.sandbox == False
                ])

            if data['status'] == 'ACTIVE':
                if plan_to_update.name == 'Bundle':
                    if len(subscribed_list) > 0:
                        return APIResponse.error_400(
                            "User subscribed other plans, please try again after suspending subscribed plans.")
                else:
                    for subscribed in subscribed_list:
                        if subscribed.plan.name == 'Bundle':
                            return APIResponse.error_400("Already subscribed with bundle plan")

            if subscription.status != data['status']:
                if subscription.id.startswith('I-'):
                    sub = Subscription(
                        plan_id=subscription.plan_id
                    )
                    if data['status'] == 'SUSPENDED':
                        sub.unsubscribe(subscription.id, "Suspended by admin.")
                    elif data['status'] == 'ACTIVE':
                        sub.resubscribe(subscription.id, "Subscribed by admin.")

                    s = sub.details(subscription.id)
                    subscription.status = s.get('status')
                else:
                    subscription.status = data.get('status')

                if data['status'] == "ACTIVE":
                    # Create restream server if Syndication or Bundle
                    if subscription.plan.name in ['Syndication', 'Bundle'] and subscription.status == 'ACTIVE':
                        server_info = create_server(f"rs-{subscription.id}")
                        server = RestreamServersModel(
                            id=f"{str(uuid.uuid4().hex)}",
                            subscription_id=subscription.id,
                            instance_id=server_info["InstanceId"],
                            state="pending",
                            reservation=json.loads(json.dumps(server_info, default=str)),
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                        )
                        server.save()
                else:
                    # Terminate restream servers
                    servers = RestreamServersModel.filter_all([
                        RestreamServersModel.subscription_id == subscription.id
                    ])

                    for server in servers:
                        terminate_server(server.instance_id)
                        server.delete()

            subscription.update_time = datetime.utcnow()
            subscription.save()

            result = AdminSubscriptionsSchema().dumps(subscription)
            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()


class AdminDeleteSubscriptionResource(Resource):
    @jwt_required
    @admin_required
    def delete(self, id):
        """
        Delete subscription
        ---
        tags:
          - Subscription
        description: Delete subscription by id.
        operationId: deleteSubscription
        security:
          - bearerAuth: []
        parameters:
          - in: path
            name: id
            schema:
              type: string
            required: true
            description: Subscription id
        responses:
          204:
            description: Deleted
          401:
            description: Unauthorized.
          404:
            description: Subscription not found
          500:
            description: Internal server error
        """
        try:
            if app.config['PAYPAL_MODE'] == 'sandbox':
                subscription = SubscriptionsModel.filter_first([
                    SubscriptionsModel.id == id,
                    SubscriptionsModel.sandbox == True
                ])
            else:
                subscription = SubscriptionsModel.filter_first([
                    SubscriptionsModel.id == id,
                    SubscriptionsModel.sandbox == False
                ])

            if subscription is None:
                return APIResponse.error_404("Subscription not found!")

            if subscription.status == "ACTIVE":
                return APIResponse.error_403("Active subscription can't be deleted, please suspend and try again.")

            subscription.delete()
            response = {'message': 'Subscription deleted'}
            return make_response(response, 204)

        except Exception as e:
            print(e)
            return APIResponse.error_500()
