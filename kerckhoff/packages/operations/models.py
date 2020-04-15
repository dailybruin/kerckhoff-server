from datetime import datetime
from typing import Optional

import frontmatter
from django.utils.dateparse import parse_datetime
from markdown import Markdown
from rest_framework import serializers

from kerckhoff.packages import constants
from kerckhoff.packages.operations.parser import Parser
from kerckhoff.packages.operations.s3_utils import get_public_link


class ParsedContent:
    raw: str
    html: str
    data: dict

    def __init__(self, raw, format: str):
        try:
            # is bytes
            self.raw = raw.decode("utf-8")
        except AttributeError:
            # is str
            self.raw = raw
        try:
            if format == FORMAT_MD:
                file = frontmatter.loads(self.raw)
                self.html = MarkdownParser.convert(file.content)
                self.data = file.metadata
            elif format == FORMAT_AML:
                parser = Parser()
                aml_content = parser.parse(self.raw)
                self.html = ""
                self.data = aml_content
            else:
                self.html = ""
                self.data = {"status": 0, "content": {}}

        except Exception as err:
            self.html = ""
            self.data = {"status": 1, "content": {"Error": str(err)}}


class GoogleDriveFile:
    drive_id: str
    title: str
    mimeType: str
    selfLink: str
    altLink: str
    last_modified_by: str
    last_modified_date: datetime
    _underlying: dict
    _code: str

    def __init__(self, underlying: dict, from_serialized=False):
        if from_serialized:
            self.drive_id = underlying["drive_id"]
            self.altLink = underlying["altLink"]
            self.last_modified_date = underlying["last_modified_date"]
            self.last_modified_by = underlying["last_modified_by"]
        else:
            self.drive_id = underlying["id"]
            self.altLink = underlying["alternateLink"]
            self.last_modified_date = parse_datetime(underlying["modifiedDate"])
            self.last_modified_by = underlying["lastModifyingUser"]["displayName"]

        self._underlying = underlying
        self.title = underlying["title"]
        self.mimeType = underlying["mimeType"]
        self.selfLink = underlying["selfLink"]

    def get_download_link(self) -> str:
        return self.selfLink + "?alt=media"

    def get_data_type(self) -> str:
        return constants.TEXT

    def to_json(self, **kwargs) -> dict:
        return GoogleDriveFileSerializer(self).data

    @classmethod
    def from_json(cls, serialized: dict) -> "GoogleDriveFile":
        return {
            GoogleDriveTextFile._code: GoogleDriveTextFile.from_json,
            GoogleDriveImageFile._code: GoogleDriveImageFile.from_json,
        }.get(serialized["_code"], lambda x: GoogleDriveFile(x, from_serialized=True))(
            serialized
        )

    def snapshot(self, **kwargs) -> Optional[dict]:
        """
        Performs the actions necessary for snapshotting the data
        :return: the snapshot results
        """
        return self.to_json()


class GoogleDriveTextFile(GoogleDriveFile):
    format: str
    content_plain: Optional[ParsedContent]
    content_rich: Optional[ParsedContent]
    _is_rich: bool  # Transient state - not serialized

    _code = "GDRIVE_TXT"

    def __init__(self, underlying: dict, from_serialized=False):
        super().__init__(underlying, from_serialized)
        if from_serialized:
            self.format = underlying["format"]
            self.content_plain = underlying.get("content_plain")
            self.content_rich = underlying.get("content_rich")
        else:
            self.format = infer_format(self.title)

    def get_download_link(self) -> str:
        mime_type = "text/html" if self._is_rich else "text/plain"
        return self.selfLink + f"/export?mimeType={mime_type}"

    def get_data_type(self) -> str:
        return {
            FORMAT_AML: constants.AML,
            FORMAT_MD: constants.MARKDOWN,
            FORMAT_PLAIN: constants.TEXT,
        }[self.format]

    def to_json(self, **kwargs) -> dict:
        return GoogleDriveTextFileSerializer(self).data

    @classmethod
    def from_json(cls, serialized: dict):
        return GoogleDriveTextFile(serialized, from_serialized=True)

    def parse_content(self, raw: str, is_rich=False):
        content = ParsedContent(raw, self.format)
        if is_rich:
            self.content_rich = content
        else:
            self.content_plain = content


class GoogleDriveImageFile(GoogleDriveFile):
    thumbnail_link: str
    src_large: Optional[str]
    src_medium: Optional[str]
    s3_key: Optional[str]
    s3_bucket: Optional[str]

    _code = "GDRIVE_IMG"

    def __init__(self, underlying: dict, from_serialized=False):
        super().__init__(underlying, from_serialized)
        if from_serialized:
            self.thumbnail_link = underlying["thumbnail_link"]
            self.s3_key = underlying.get("s3_key")
            self.s3_bucket = underlying.get("s3_bucket")
        else:
            self.thumbnail_link = underlying["thumbnailLink"]

    def get_data_type(self):
        return constants.IMAGE

    def to_json(self, **kwargs) -> dict:
        if kwargs.get("refresh") and self.s3_key and self.s3_bucket:
            self.src_large = get_public_link(self)
        return GoogleDriveImageFileSerializer(self).data

    @classmethod
    def from_json(cls, serialized: dict):
        return GoogleDriveImageFile(serialized, from_serialized=True)

    def snapshot(self, **kwargs) -> Optional[dict]:
        image_utils: "ImageUtils" = kwargs["image_utils"]
        res = image_utils.snapshot_image(self)
        self.s3_key = res["key"]
        self.s3_bucket = res["bucket"]
        return self.to_json(refresh=True)


class S3Item:
    def __init__(self, underlying):
        self.bucket = underlying["bucket"]
        self.region = underlying["region"]
        self.key = underlying["key"]
        self.meta = underlying.get("meta")


class GoogleDriveFileSerializer(serializers.Serializer):
    drive_id = serializers.CharField()
    title = serializers.CharField()
    mimeType = serializers.CharField()
    selfLink = serializers.URLField()
    altLink = serializers.URLField()
    last_modified_by = serializers.EmailField()
    last_modified_date = serializers.DateTimeField()
    _code = serializers.CharField()


class ParsedContentSerializer(serializers.Serializer):
    raw = serializers.CharField()
    html = serializers.CharField()
    data = serializers.JSONField()


class GoogleDriveTextFileSerializer(GoogleDriveFileSerializer):
    format = serializers.CharField()
    content_plain = ParsedContentSerializer()
    content_rich = ParsedContentSerializer(required=False)


class GoogleDriveImageFileSerializer(GoogleDriveFileSerializer):
    thumbnail_link = serializers.URLField()
    src_large = serializers.CharField(required=False)
    src_medium = serializers.CharField(required=False)
    s3_key = serializers.CharField(required=False)
    s3_bucket = serializers.CharField(required=False)


# Utils
# TODO - convert to an ENUM type
FORMAT_AML = "AML"
FORMAT_MD = "MD"
FORMAT_PLAIN = "PLAIN"

FormatTable = {"aml": FORMAT_AML, "md": FORMAT_MD}

MarkdownParser = Markdown()


def infer_format(file_title: str) -> str:
    extension = file_title.split(".")[-1].lower()
    return FormatTable.get(extension, FORMAT_PLAIN)
