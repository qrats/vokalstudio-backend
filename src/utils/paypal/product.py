import json
import requests

from .PaypalClient import PayPalClient


class Product(PayPalClient):
    def __init__(
            self,
            name,
            description,
            type='DIGITAL',
            category='SOFTWARE',
            image_url=None,
            home_url=None
    ):
        super().__init__()
        self.id = None
        self.name = name
        self.description = description
        self.type = type
        self.category = category
        self.image_url = image_url
        self.home_url = home_url
        self.created_time = None

        self.url = '{}/v1/catalogs/products'.format(self.base_url)

    def details(self, product_id):
        url = f"{self.url}/{product_id}"
        response = requests.get(url, headers=self.auth_header)

        if response.status_code == 200:
            product = json.loads(response.text)
            print(product)
        else:
            product = None

        return product

    def create(self):
        data = {
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "category": self.category,
        }

        if self.image_url is not None:
            data['image_url'] = self.image_url

        if self.home_url is not None:
            data['home_url'] = self.home_url

        response = requests.post(self.url, headers=self.auth_header, data=json.dumps(data))

        if response.status_code == 201:
            created_product = json.loads(response.text)
            print(created_product)
        else:
            created_product = None

        return created_product

    def list(self, page_size, page_number):
        params = {
            'page_size': page_size,
            'page': page_number,
            'total_required': True
        }
        response = requests.get(self.url, headers=self.auth_header, params=params)

        if response.status_code == 200:
            products = json.loads(response.text)
            print(products)
        else:
            products = []

        return products
