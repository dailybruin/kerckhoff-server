import boto3
import os
from kerckhoff.config.common import Common
import uuid
import mimetypes


def get_s3():
    key = Common.AWS_CONFIG["ACCESS_KEY"]
    secret = Common.AWS_CONFIG["SECRET_KEY"]
    region = Common.AWS_CONFIG["REGION"]
    session = boto3.Session(region_name=region, aws_access_key_id=key, aws_secret_access_key=secret)
    return session.client('s3')


def upload_file(s3, image_path, bucket, mimetype):
    if not os.path.exists(image_path):
        raise FileNotFoundError(image_path)
    key = str(uuid.uuid4()) + mimetypes.guess_extension(mimetype)
    args = {'ContentType': mimetype}
    s3.upload_file(image_path, bucket, key, ExtraArgs=args)
    return key
