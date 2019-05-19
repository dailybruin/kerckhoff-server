import tempfile
import os
from PIL import Image
from django.contrib.auth import get_user_model
from kerckhoff.users.models import User as AppUser
from kerckhoff.packages.operations.s3_utils import (
    get_s3_client,
    upload_file,
    get_bucket_region,
)
from kerckhoff.packages.operations.google_drive import GoogleDriveOperations
from kerckhoff.packages.models import PackageItem

User: AppUser = get_user_model()


class ImageUtils:
    def __init__(self, user: User):
        self._user = user

    def snapshot_images(
        self, google_drive_image_files, bucket, package_versions, quality=95
    ):
        """Download images from package, compresses them and uploads them into s3

        Keyword arguments:
        google_drive_image_files {list(GoogleDriveImageFile)} -- drive images
        bucket {str} - bucket name for image upload
        package_versions {list(PackageVersion)} -- versions in which the images are used
        quality {int} -- quality to compress image to (1-100, default:95)
        """
        s3 = get_s3_client()
        op = GoogleDriveOperations(self._user)
        for drive_image_file in google_drive_image_files:
            res = op.download_item(drive_image_file)
            if res.ok:
                # ToDo: Handle non-jpeg
                with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
                    image_path = f.name
                    for chunk in res:
                        f.write(chunk)
                    f.flush()
                    self._compress_image(
                        image_path, quality=quality, mimetype=drive_image_file.mimeType
                    )
                    key = upload_file(s3, image_path, bucket, drive_image_file.mimeType)
                    self._save_item(
                        package_versions,
                        key,
                        bucket,
                        get_bucket_region(s3, bucket),
                        drive_image_file.mimeType,
                    )
            else:
                raise FileNotFoundError

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

    def _save_item(self, package_versions, key, bucket, region, mimetype, meta=None):
        data = {"key": key, "bucket": bucket, "region": region, "meta": meta}

        item = PackageItem(
            data_type=PackageItem.IMAGE, data=data, file_name=key, mime_types=mimetype
        )
        item.save()
        item.package_versions.set(package_versions)
        item.save()
