import logging
import mimetypes
import os
import uuid

import boto3
from django.conf import settings

logger = logging.getLogger(__name__)

_global_s3_client = None


def get_s3_client():
    global _global_s3_client
    if _global_s3_client is None:
        key = settings.AWS_CONFIG["ACCESS_KEY"]
        secret = settings.AWS_CONFIG["SECRET_KEY"]
        region = settings.AWS_CONFIG["REGION"]
        session = boto3.Session(
            region_name=region, aws_access_key_id=key, aws_secret_access_key=secret
        )
        _global_s3_client = session.client("s3")
    return _global_s3_client


def upload_file(s3_client, image_path, bucket, mimetype):
    if not os.path.exists(image_path):
        raise FileNotFoundError(image_path)
    key = str(uuid.uuid4()) + mimetypes.guess_extension(mimetype)
    args = {"ContentType": mimetype}
    res = s3_client.upload_file(image_path, bucket, key, ExtraArgs=args)
    logger.debug("Uploaded {0} to {1}/{2}".format(image_path, bucket, key))
    return key, res


def get_public_link(google_drive_image_file: "GoogleDriveImageFile", duration=3600):
    s3 = get_s3_client()
    return s3.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": google_drive_image_file.s3_bucket,
            "Key": google_drive_image_file.s3_key,
        },
        ExpiresIn=duration,
    )


def get_bucket_region(s3_client, bucket):
    return s3_client.get_bucket_location(Bucket=bucket)["LocationConstraint"]
