import boto3

from flask import current_app as app


def ec2_client():
    return boto3.client(
        "ec2",
        region_name=app.config['AWS_REGION'],
        aws_access_key_id=app.config['AWS_ACCESS_KEY_ID'],
        aws_secret_access_key=app.config['AWS_SECRET_ACCESS_KEY']
    )


def create_server(server_name):
    instances = ec2_client().run_instances(
        ImageId="ami-00a75f9c9e4e317c2",
        MinCount=1,
        MaxCount=1,
        InstanceType="t3a.nano",
        KeyName="vokal-restreamer",
        SubnetId="subnet-6753fc3b",
        SecurityGroupIds=['sg-002298719807b3a1b'],
        TagSpecifications=[
            {
                'ResourceType': 'instance',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': server_name
                    },
                ]
            },
        ],
    )

    return instances["Instances"][0]


def get_server_info(server_id):
    ec2_client().describe_instances(InstanceIds=[server_id])


def terminate_server(server_id):
    ec2_client().terminate_instances(InstanceIds=[server_id])
