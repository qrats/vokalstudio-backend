import os
import jinja2
import boto3
from botocore.exceptions import ClientError

from flask import current_app as app


def send_registration_email(user_data, verify_token):
    subject = 'Email confirmation'
    template_loader = jinja2.FileSystemLoader(searchpath=app.config['TEMPLATES_DIR'])
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template("registration.html")
    html_content = template.render(engine_host=app.config['ENGINE_HOST'], user=user_data, token=verify_token)

    client = boto3.client(
        'ses',
        region_name=app.config['AWS_REGION'],
        aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY']
    )

    # Provide the contents of the email.
    response = client.send_email(
        Destination={'ToAddresses': [user_data['email']]},
        Source=app.config['SERVICE_EMAIL'],
        Message={
            'Body': {'Html': {'Charset': "UTF-8", 'Data': html_content}},
            'Subject': {'Charset': "UTF-8", 'Data': subject},
        },
    )


def send_invitation_email(invitation_info):
    subject = 'Invited!'
    template_loader = jinja2.FileSystemLoader(searchpath=app.config['TEMPLATES_DIR'])
    template_env = jinja2.Environment(loader=template_loader)
    template = template_env.get_template("invitation.html")
    html_content = template.render(engine_host=app.config['ENGINE_HOST'], invitation_info=invitation_info)

    client = boto3.client(
        'ses',
        region_name=app.config['AWS_REGION'],
        aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY']
    )

    # Provide the contents of the email.
    response = client.send_email(
        Destination={'ToAddresses': [invitation_info['invitee_email']]},
        Source=app.config['SERVICE_EMAIL'],
        Message={
            'Body': {'Html': {'Charset': "UTF-8", 'Data': html_content}},
            'Subject': {'Charset': "UTF-8", 'Data': subject},
        },
    )
