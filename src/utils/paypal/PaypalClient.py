import os
import json
import base64
import requests


class PayPalClient:
    def __init__(self):
        self.mode = os.environ['PAYPAL_MODE']
        if self.mode == 'sandbox':
            self.base_url = "https://api-m.sandbox.paypal.com"
        else:
            self.base_url = "https://api.paypal.com"
        
        self.access_token = None
    
    def _get_token(self):
        credential = base64.b64encode(
            f"{os.environ['PAYPAL_CLIENT_ID']}:{os.environ['PAYPAL_CLIENT_SECRET']}".encode('utf-8')).decode(
            'utf-8').replace("\n", "")
        
        headers = {
            "Authorization": ("Basic %s" % credential),
            'Accept': 'application/json',
            'Accept-Language': 'en_US',
        }
        param = {'grant_type': 'client_credentials'}

        url = '{}/v1/oauth2/token'.format(self.base_url)
        r = requests.post(url, headers=headers, data=param)
        response = json.loads(r.text)

        return response['access_token']

    @property
    def auth_header(self):
        if self.access_token is None:
            self.access_token = self._get_token()

        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + self.access_token
        }

        return headers
