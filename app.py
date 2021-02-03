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
    response.headers.add('Access-Control-Allow-Headers', '*')
    response.headers.add('Access-Control-Allow-Methods', '*')
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


@app.cli.command('create_products')
def cmd_create_product():
    from datetime import datetime
    from src.models.products import ProductsModel
    from src.utils.paypal.product import Product
    product = Product(
        name="PRO",
        description="Include all features across Producer, Syndication and Virtual Studio.",
    )
    prod = product.create()

    p = product.details(prod['id'])

    new_product = ProductsModel(
        sandbox=False,
        id=p['id'],
        name=p['name'],
        description=p['description'],
        type=p['type'],
        category=p['category'],
        links=p['links'],
        create_time=datetime.strptime(p['create_time'], '%Y-%m-%dT%H:%M:%SZ'),
        update_time=datetime.strptime(p['update_time'], '%Y-%m-%dT%H:%M:%SZ')
    )

    if 'image_url' in p:
        new_product.image_url = p['image_url']

    if 'home_url' in p:
        new_product.home_url = p['home_url']

    new_product.save()


@app.cli.command('create_plans')
def cmd_create_plans():
    from datetime import datetime
    from src.models.plans import PlansModel
    from src.utils.paypal.plan import Plan

    plan = Plan(
        product_id='PROD-9LB36648893007432',
        name="PRO",
        description="Include all features across Producer, Syndication and Virtual Studio.",
        price=99.00
    )
    pln = plan.create()

    p = plan.details(pln['id'])

    new_plan = PlansModel(
        sandbox=False,
        id=p['id'],
        name=p['name'],
        description=p['description'],
        product_id=p['product_id'],
        status=p['status'],
        billing_cycles=plan.billing_cycles,
        payment_preferences=plan.payment_preferences,
        taxes=plan.taxes,
        links=p['links'],
        quantity_supported=False,
        create_time=datetime.strptime(p['create_time'], '%Y-%m-%dT%H:%M:%SZ'),
        update_time=datetime.strptime(p['update_time'], '%Y-%m-%dT%H:%M:%SZ')
    )
    new_plan.save()


@app.cli.command('create_subscription')
def cmd_create_subscription():
    from datetime import datetime
    from src.utils.paypal.subscription import Subscription

    sub = Subscription(
        plan_id='P-47S70783128454237MALV32I'
    )

    # s = sub.create()

    p = sub.details('I-YK3SWC2YXKYA')
    print(p)
