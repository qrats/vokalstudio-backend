import json
from flask import make_response, jsonify
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required
from flask import current_app as app

from src.models.restream_servers import RestreamServersModel
from src.schemas.restream_servers import AdminRestreamServersSchema

from src.utils.api_response import APIResponse
from src.utils.permissions import admin_required


class GetAdminRestreamServersResource(Resource):
    @jwt_required
    @admin_required
    def get(self):
        """
        Get all RTMP servers
        ---
        tags:
          - rtmp servers
        description: Get RTMP servers
        operationId: getRTMPServers
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
                restream_servers = RestreamServersModel.filter_all([
                    RestreamServersModel.subscription.has(sandbox=True)
                ])
            else:
                restream_servers = RestreamServersModel.filter_all([
                    RestreamServersModel.subscription.has(sandbox=False)
                ])

            result = AdminRestreamServersSchema().dumps(restream_servers, many=True)

            response = jsonify(json.loads(result))
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()
