import logging
import config
from celery import Celery
from src import create_app
from src.services.db import db

celery = Celery(
    __name__,
    backend='redis://localhost:6379/0',
    broker='redis://localhost:6379/0',
)

app = create_app(config.DevelopmentConfig)
app.app_context().push()

celery.conf.update(app.config)
logging.getLogger('googleapicliet.discovery_cache').setLevel(logging.ERROR)


@app.route("/")
def health_check():
    return {"message": "API server is live!"}


@app.teardown_request
def session_clear(exception=None):
    db.session.remove()
    if exception and db.session.is_active:
        db.session.rollback()


@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Origin, Authorization, X-Requested-With')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,OPTIONS')
    return response


@app.shell_context_processor
def make_shell_context():
    """Adds imports to default shell context for easier use"""
    from src.models.users import UserModel
    from src.models.revoked_tokens import RevokedTokenModel
    return {
        "user": UserModel,
        "revoked_token": RevokedTokenModel,
    }


from src.services.jwt import jwt


@jwt.token_in_blacklist_loader
def check_if_token_in_blacklist(decrypted_token):
    from src.models.revoked_tokens import RevokedTokenModel
    jti = decrypted_token['jti']
    return RevokedTokenModel.is_jti_blacklisted(jti)


if __name__ == '__main__':
    app.run(debug=True)
