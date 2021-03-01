import os
from flasgger import Swagger

if os.environ.get("STAGE") == 'dev':
  host_name = os.environ.get("DEV_HOST")
else:
  host_name = os.environ.get("PROD_HOST")


swagger_config = {
    "openapi": "3.0.2",
    "headers": [],
    "components": {
        "securitySchemes": {
          "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
          }
        }
    },
    "servers": [
        {
          "url": host_name,
        },
    ],
    "specs": [
        {
            "endpoint": "/api/swagger",
            "route": f"/api/swagger.json",
            "rule_filter": lambda rule: True,  # all in
            "model_filter": lambda tag: True,  # all in
        }
    ],
    "title": "Greenwich.HR API Documentation",
    "version": "0.0.1",
    "termsOfService": "",
    "static_url_path": f"/api/static/swagger",
    "swagger_ui": True,
}

swagger = Swagger(
    config=swagger_config,
)
