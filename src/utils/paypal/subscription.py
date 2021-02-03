import json
import requests

from .PaypalClient import PayPalClient


class Subscription(PayPalClient):
    def __init__(
        self,
        plan_id,
        start_time=None,
        quantity=1,
        shipping_amount=None,
        subscriber=None,
        application_context=None
    ):
        super().__init__()
        self.plan_id = plan_id
        self.start_time = start_time
        self.quantity = quantity
        self.shipping_amount = shipping_amount
        self.subscriber = subscriber
        if application_context is not None:
            self.application_context = application_context
        else:
            self.application_context = {
                "brand_name": "Vokal Studio",
                "locale": "en-US",
                "shipping_preference": "NO_SHIPPING",
                "user_action": "SUBSCRIBE_NOW",
                "payment_method": {
                    "payer_selected": "PAYPAL",
                    "payee_preferred": "IMMEDIATE_PAYMENT_REQUIRED"
                },
                "return_url": "https://example.com/returnUrl",
                "cancel_url": "https://example.com/cancelUrl"
            }

    def create(self):
        """
        doc: https://developer.paypal.com/docs/api/subscriptions/v1/#subscriptions_create
        """
        url = '{}/v1/billing/subscriptions'.format(self.base_url)
        data = {"plan_id": self.plan_id}

        if self.start_time is not None:
            data['start_time'] = self.start_time

        if self.quantity is not None:
            data['quantity'] = self.quantity

        if self.shipping_amount is not None:
            data['shipping_amount'] = self.shipping_amount

        if self.subscriber is not None:
            data['subscriber'] = self.subscriber

        if self.application_context is not None:
            data['application_context'] = self.application_context

        response = requests.post(url, headers=self.auth_header, data=json.dumps(data))

        if response.status_code == 201:
            created_subscription = json.loads(response.text)
        else:
            print(response.text)
            created_subscription = None

        return created_subscription

    def details(self, subscription_id):
        subscribe_details = None
        url = '{}/v1/billing/subscriptions/{}'.format(self.base_url, subscription_id)
        response = requests.get(url, headers=self.auth_header)

        if response.status_code == 200:
            subscribe_details = json.loads(response.text)

        return subscribe_details

    def unsubscribe(self, subscription_id, reason="Not satisfied with the service"):
        success = False
        url = '{}/v1/billing/subscriptions/{}/suspend'.format(self.base_url, subscription_id)
        data = {"reason": reason}

        response = requests.post(url, headers=self.auth_header, data=json.dumps(data))
        if response.status_code == 204:
            success = True

        return success

    def resubscribe(self, subscription_id, reason="Reactivating the subscription"):
        success = False
        url = '{}/v1/billing/subscriptions/{}/activate'.format(self.base_url, subscription_id)
        data = {"reason": reason}

        response = requests.post(url, headers=self.auth_header, data=json.dumps(data))
        if response.status_code == 204:
            success = True

        return success
