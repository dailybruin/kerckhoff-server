import boto3
import os
import uuid
import mimetypes
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def get_s3_client():
    key = settings.AWS_CONFIG["ACCESS_KEY"]
    secret = settings.AWS_CONFIG["SECRET_KEY"]
    region = settings.AWS_CONFIG["REGION"]
    session = boto3.Session(
        region_name=region, aws_access_key_id=key, aws_secret_access_key=secret
    )
    return session.client("s3")


def upload_file(s3_client, image_path, bucket, mimetype):
    if not os.path.exists(image_path):
        raise FileNotFoundError(image_path)
    key = str(uuid.uuid4()) + mimetypes.guess_extension(mimetype)
    args = {"ContentType": mimetype}
    s3_client.upload_file(image_path, bucket, key, ExtraArgs=args)
    logger.debug("Uploaded {0} to {1}/{2}".format(image_path, bucket, key))
    return key


def get_bucket_region(s3_client, bucket):
    return s3_client.get_bucket_location(Bucket=bucket)["LocationConstraint"]
