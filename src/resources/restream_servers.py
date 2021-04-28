import json
from flask import make_response, jsonify
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required
from flask import current_app as app

from src.models.restream_servers import RestreamServersModel

from src.schemas.restream_servers import RestreamServersSchema
from src.utils.api_response import APIResponse


class GetRestreamServerResource(Resource):
    @jwt_required
    def get(self, subscription_id):
        try:
            restresm_server = RestreamServersModel.filter_first([
                RestreamServersModel.subscription_id == subscription_id
            ])

            result = RestreamServersSchema().dumps(restresm_server)
            response = json.loads(result)
            return make_response(response, 200)
        except Exception as e:
            print(e)
            return APIResponse.error_500()
