from bleach.sanitizer import Cleaner
from html5lib.filters.base import Filter
from urllib.parse import parse_qs, urlparse
from PIL import Image
import tempfile
import re

from kerckhoff.packages.operations.s3_utils import get_s3, upload_file
from kerckhoff.packages.operations.models import GoogleDriveImageFile, S3Item, S3ItemSerializer
from kerckhoff.packages.operations.google_drive import GoogleDriveOperations
from kerckhoff.packages.models import PackageItem
from kerckhoff.users.models import User as AppUser

User: AppUser = get_user_model()

TAGS = ["a", "p", "span", "em", "strong"]
ATTRS = {"span": ["style"], "a": ["href"]}
STYLES = ["font-weight", "font-style", "text-decoration"]


class KeepOnlyInterestingSpans(Filter):
    drop_next_close = False

    def _style_is_boring(self, prop, value):
        boring_styles = {
            "font-weight": ["400", "normal"],
            "text-decoration": ["none"],
            "font-style": ["normal"],
        }

        return value in boring_styles.get(prop, [])

    def _reduce_to_interesting_styles(self, token):
        styles = token["data"].get((None, "style"))
        if styles is not None:
            final_styles = ""
            for prop, value in re.findall(r"([-\w]+)\s*:\s*([^:;]*)", styles):
                if not self._style_is_boring(prop, value):
                    final_styles += "%s:%s;" % (prop, value)
            token["data"][(None, "style")] = final_styles
            return final_styles
        return ""

    def __iter__(self):
        for token in Filter.__iter__(self):
            if token["type"] == "StartTag" and token["name"] == "span":
                if not token["data"]:
                    drop_next_close = True
                    continue

                reduced_styles = self._reduce_to_interesting_styles(token)
                # print("final:", token)
                if reduced_styles == "":
                    drop_next_close = True
                    continue
            elif (
                token["type"] == "EndTag"
                and token["name"] == "span"
                and drop_next_close
            ):
                drop_next_close = False
                continue
            yield (token)


class ConvertPTagsToNewlines(Filter):
    NEWLINE_TOKEN = {"type": "Characters", "data": "\n"}

    def __iter__(self):
        for token in Filter.__iter__(self):
            if token["type"] == "StartTag" and token["name"] == "p":
                continue
            elif token["type"] == "EndTag" and token["name"] == "p":
                yield (self.NEWLINE_TOKEN)
                continue
            yield (token)


class RemoveGoogleTrackingFromHrefs(Filter):
    def __iter__(self):
        for token in Filter.__iter__(self):
            if token["type"] == "StartTag" and token["name"] == "a" and token["data"]:
                url = token["data"].get((None, "href"))
                if url is not None:
                    actual_url = parse_qs(urlparse(url).query).get("q")
                    if actual_url is not None and len(actual_url) > 0:
                        token["data"][(None, "href")] = actual_url[0]
            yield (token)


GoogleDocHTMLCleaner: Cleaner = Cleaner(
    tags=TAGS,
    attributes=ATTRS,
    styles=STYLES,
    strip=True,
    filters=[
        KeepOnlyInterestingSpans,
        ConvertPTagsToNewlines,
        RemoveGoogleTrackingFromHrefs,
    ],
)

# Image utils
class ImageUtils:

    def __init__(self, user: User):
        self.__user = user

    def snapshot_images(self, package, bucket, package_versions, quality=95):
        """Download images from package, compresses them and uploads them into s3

        Keyword arguments:
        package -- package to download images from
        bucket -- s3 bucket to upload images
        package_versions -- versions in which the images are used
        quality -- quality to compress image to (default:05)
        """
        s3 = get_s3()
        image_metas = [package.cached[i] for i in range(len(package.cached))
                       if package.cached[i]['mimeType'] == 'image/jpeg']
        op = GoogleDriveOperations(self.__user)
        for meta in image_metas:
            gdrive_img = GoogleDriveImageFile(meta, from_serialized=True)
            res = op.download_item(gdrive_img)
            if res.ok:
                # ToDo: Handle non-jpeg
                with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
                    image_path = f.name
                    for chunk in res:
                        f.write(chunk)
                    f.flush()
                    # Wrap in try except
                    self.__compress_image(image_path, quality=quality, mimetype=meta['mimeType'])
                    key = upload_file(s3, image_path, bucket, meta['mimeType'])
                    self.__save_item(package_versions, key, bucket, s3.region, meta['mimeType'])

    def __compress_image(self, image_path, quality=95, mimetype='image/jpeg'):
        """Compresses image and replaces original image

        Keyword arguments:
        image_path -- local path of image
        quality -- 0 to 100 (default: 95)
        mimetype -- string (default: image/jpeg)
        """
        img = Image.open(image_path)
        img.save(image_path, quality=quality, optimize=True)

    def __save_item(self, package_versions, key, bucket, region, mimetype, meta=None):
        data = S3Item({
            "key": key,
            "bucket": bucket,
            "region": region,
            "meta": meta
        })

        item = PackageItem(package_versions=package_versions,
                           data_type=PackageItem.IMAGE,
                           data=S3ItemSerializer(data),
                           file_name=key,
                           mime_types=mimetype)
        item.save()
