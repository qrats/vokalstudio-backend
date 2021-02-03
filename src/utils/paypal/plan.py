import json
import requests

from .PaypalClient import PayPalClient


class Plan(PayPalClient):
    def __init__(
            self,
            product_id,
            name,
            description,
            frequency='MONTH',
            total_cycles='0',
            price='9.99',
            currency='USD',
            setup_fee="0",
            setup_currency="USD",
            tax_percentage="0"
    ):
        super().__init__()
        self.product_id = product_id
        self.name = name
        self.description = description
        self.frequency = frequency
        self.total_cycles = total_cycles
        self.price = price
        self.currency = currency
        self.setup_fee = setup_fee
        self.setup_currency = setup_currency
        self.tax_percentage = tax_percentage

        self.billing_cycles = [
            {
                "frequency": {
                    "interval_unit": self.frequency,
                    "interval_count": 1
                },
                "tenure_type": "REGULAR",
                "sequence": 1,
                "total_cycles": self.total_cycles,
                "pricing_scheme": {
                    "fixed_price": {
                        "value": self.price,
                        "currency_code": self.currency
                    }
                }
            }
        ]

        self.payment_preferences = {
            "auto_bill_outstanding": "true",
            "setup_fee": {
                "value": self.setup_fee,
                "currency_code": self.setup_currency
            },
            "setup_fee_failure_action": "CONTINUE",
            "payment_failure_threshold": 3
        }

        self.taxes = {
            "percentage": self.tax_percentage,
            "inclusive": "false"
        }

        self.url = '{}/v1/billing/plans'.format(self.base_url)

    def details(self, plan_id):
        url = f"{self.url}/{plan_id}"
        response = requests.get(url, headers=self.auth_header)

        if response.status_code == 200:
            plan = json.loads(response.text)
            print(plan)
        else:
            plan = None

        return plan

    def create(self):
        data = {
            "product_id": self.product_id,
            "name": self.name,
            "description": self.description,
            "status": "ACTIVE",
            "billing_cycles": self.billing_cycles,
            "payment_preferences": self.payment_preferences,
            "taxes": self.taxes
        }

        response = requests.post(self.url, headers=self.auth_header, data=json.dumps(data))

        if response.status_code == 201:
            created_plan = json.loads(response.text)
            print(created_plan)
        else:
            print(response.text)
            created_plan = None

        return created_plan

    def list(self):
        plans = []
        response = requests.get(self.url, headers=self.auth_header)

        if response.status_code == 200:
            plans = json.loads(response.text)['plans']

        return plans
