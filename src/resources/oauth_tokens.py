import json
import requests
from datetime import datetime
from flask import current_app as app
from flask import make_response, jsonify
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required

from src.utils.api_response import APIResponse

from oauth2client import client
from googleapiclient.discovery import build


class OAuthTokenResource(Resource):
    @staticmethod
    def getTwitchOauthToken(code):
        url = f'https://id.twitch.tv/oauth2/token?' \
              f'client_id={app.config["TWITCH_CLIENT_ID"]}&client_secret={app.config["TWITCH_CLIENT_SECRET"]}' \
              f'&code={code}&grant_type=authorization_code&redirect_uri={app.config["TWITCH_REDIRECT_URI"]}'
        r = requests.post(url)

        if r.status_code == 200:
            token = r.json()
        else:
            return {
                'url': url,
                'message': str(r.content)
            }

        headers = {
            'Authorization': f'Bearer {token["access_token"]}',
            'Client-ID': f'{app.config["TWITCH_CLIENT_ID"]}'
        }
        r = requests.get('https://api.twitch.tv/helix/users', headers=headers)
        if r.status_code == 200:
            broadcaster = r.json()['data'][0]
        else:
            return {'message': str(r.content)}

        response = {
            'access_token': token['access_token'],
            'refresh_token': token['refresh_token'],
            'service_email': broadcaster['email'],
            'name': broadcaster['login'],
            'broadcaster_id': broadcaster['id'],
        }
        return response

    @staticmethod
    def getPodBeanOauthToken(code):
        auth = (app.config['PODBEAN_CLIENT_ID'], app.config['PODBEAN_CLIENT_SECRET'])
        url = 'https://api.podbean.com/v1/oauth/token'
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': app.config['PODBEAN_REDIRECT_URI']
        }

        r = requests.post(url, auth=auth, data=data)
        token = json.loads(r.content)

        response = {
            'access_token': token['access_token'],
            'refresh_token': token['refresh_token'],
            'service_email': 'N/A',
            'name': 'N/A',
        }
        return response

    @staticmethod
    def getFacebookOauthToken(code):
        # Get app access token
        payload = {
            'client_id': app.config['FACEBOOK_CLIENT_ID'],
            'client_secret': app.config['FACEBOOK_CLIENT_SECRET'],
            'grant_type': 'client_credentials',
        }

        url = 'https://graph.facebook.com/oauth/access_token'
        r = requests.get(url, params=payload)
        token = json.loads(r.content)
        access_token = token['access_token']

        payload = {
            'client_id': app.config['FACEBOOK_CLIENT_ID'],
            'client_secret': app.config['FACEBOOK_CLIENT_SECRET'],
            'redirect_uri': app.config['FACEBOOK_REDIRECT_URI'],
            'code': code,
        }

        url = 'https://graph.facebook.com/v10.0/oauth/access_token'
        r = requests.get(url, params=payload)
        token = json.loads(r.content)
        input_token = token['access_token']

        payload = {'access_token': access_token, 'input_token': input_token}
        url = 'https://graph.facebook.com/debug_token'
        r = requests.get(url, params=payload)
        token = json.loads(r.content)
        user_id = token['data']['user_id']

        payload = {'access_token': input_token, 'fields': 'name,email'}
        url = f'https://graph.facebook.com/v10.0/{user_id}'
        r = requests.get(url, params=payload)
        user_info = json.loads(r.content, encoding='utf-8')

        response = {
            'user_id': user_id,
            'access_token': input_token,
            'name': user_info['name'],
            'service_email': user_info['email'],
        }
        return response

    @staticmethod
    def getYoutubeOauthToken(code):
        credentials = client.credentials_from_code(
            app.config['GOOGLE_CLIENT_ID'],
            app.config['GOOGLE_CLIENT_SECRET'],
            scope='profile email https://www.googleapis.com/auth/youtube '
                  'https://www.googleapis.com/auth/youtube.force-ssl '
                  'https://www.googleapis.com/auth/youtube.readonly '
                  'https://www.googleapis.com/auth/youtubepartner-channel-audit '
                  'https://www.googleapis.com/auth/yt-analytics.readonly',
            code=code
        )
        user_info_service = build('oauth2', 'v2', credentials=credentials)
        user_info = user_info_service.userinfo().get().execute()

        response = {
            'access_token': credentials.access_token,
            'refresh_token': credentials.refresh_token,
            'service_email': user_info['email'],
            'name': user_info['name'],
        }
        return response

    @jwt_required
    def post(self):
        parser = reqparse.RequestParser()
        parser.add_argument('service', required=True, help='Service required!')
        parser.add_argument('auth_code', required=True, help='Auth code required!')
        data = parser.parse_args()

        try:
            if data['service'] == 'Youtube':
                oauth_info = self.getYoutubeOauthToken(data['auth_code'])
            elif data['service'] == 'PodBean':
                oauth_info = self.getPodBeanOauthToken(data['auth_code'])
            elif data['service'] == 'Twitch':
                oauth_info = self.getTwitchOauthToken(data['auth_code'])
            elif data['service'] == 'Facebook':
                oauth_info = self.getFacebookOauthToken(data['auth_code'])
            else:
                return APIResponse.error_400("Invalid service")

            return make_response(oauth_info, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()
