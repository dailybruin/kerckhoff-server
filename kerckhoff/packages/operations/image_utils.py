import logging
import os
import tempfile

from PIL import Image
from django.conf import settings
from django.contrib.auth import get_user_model

from kerckhoff.packages.operations.google_drive import GoogleDriveOperations
from kerckhoff.packages.operations.s3_utils import (
    get_s3_client,
    upload_file,
    get_bucket_region,
)
from kerckhoff.users.models import User as AppUser

logger = logging.getLogger(__name__)

User: AppUser = get_user_model()


class ImageUtils:
    def __init__(self, user: User):
        self._user = user

    def snapshot_image(
        self,
        google_drive_image_file: "GoogleDriveImageFile",
        bucket=settings.AWS_CONFIG["MEDIA_BUCKET_NAME"],
        quality=95,
    ):
        """Download images from package, compresses them and uploads them into s3

        Keyword arguments:
        google_drive_image_file {GoogleDriveImageFile} -- drive image
        bucket {str} - bucket to upload the image to
        quality {int} -- quality to compress image to (1-100, default:95)
        """
        s3 = get_s3_client()
        op = GoogleDriveOperations(self._user)
        res = op.download_item(google_drive_image_file)
        if res.ok:
            # ToDo: Handle non-jpeg
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                image_path = f.name
                for chunk in res:
                    f.write(chunk)
                f.flush()
                self._compress_image(
                    image_path,
                    quality=quality,
                    mimetype=google_drive_image_file.mimeType,
                )
                key, s3_res = upload_file(
                    s3, image_path, bucket, google_drive_image_file.mimeType
                )
                logger.info(f"Uploaded to S3 with result {s3_res}")
                return {
                    "key": key,
                    "bucket": bucket,
                    "region": get_bucket_region(s3, bucket),
                    "meta": s3_res,
                }
        else:
            raise FileNotFoundError

    def get_public_link(
        self, google_drive_image_file: "GoogleDriveImageFile", duration=3600
    ):
        s3 = get_s3_client()
        return s3.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": google_drive_image_file.s3_bucket,
                "Key": google_drive_image_file.s3_key,
            },
            ExpiresIn=duration,
        )

    def _compress_image(self, image_path, quality=95, mimetype="image/jpeg"):
        """Compresses image and replaces original image

        Keyword arguments:
        image_path -- local path of image
        quality -- 0 to 100 (default: 95)
        mimetype -- string (default: image/jpeg)
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError
        img = Image.open(image_path)
        img.save(image_path, quality=quality, optimize=True)
