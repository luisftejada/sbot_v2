import os

import boto3
from dotenv import load_dotenv

env_file = os.environ.get("ENV_FILE_PATH", ".env")

load_dotenv(env_file, override=True)

DYNAMODB_env = os.environ.get("DYNAMODB_ENV", "local")
DYNAMODB_ENDPOINT_URL = os.environ.get("DYNAMODB_ENDPOINT_URL", "http://localhost:8000")
DYNAMODB_REGION = os.environ.get("DYNAMODB_REGION", "us-west-2")

AWS_SECRET_KEY = os.environ.get("AWS_SECRET_KEY", "")
AWS_ACCESS_KEY = os.environ.get("AWS_ACCESS_KEY", "")

if DYNAMODB_env == "local":
    dynamodb = boto3.resource(
        "dynamodb",
        endpoint_url=DYNAMODB_ENDPOINT_URL,
        region_name=DYNAMODB_REGION,
        aws_access_key_id="anything",
        aws_secret_access_key="anything",
    )
else:
    dynamodb = boto3.resource("dynamodb", region_name=DYNAMODB_REGION)


def get_dynamodb():
    global dynamodb
    return dynamodb
