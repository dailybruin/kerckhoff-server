from rest_framework import serializers
from datetime import datetime
from typing import Optional
from django.utils.dateparse import parse_datetime
from markdown import Markdown
import frontmatter


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
                file = frontmatter.loads(raw)
                self.html = MarkdownParser.convert(file.content)
                self.data = file.metadata
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

    def get_download_link(self) -> str:
        return self.selfLink + "?alt=media"

    def to_json(self) -> dict:
        return GoogleDriveFileSerializer(self).data

    def __init__(self, underlying: dict, from_serialized=False):
        self._from_serialized = from_serialized
        if from_serialized:
            self.drive_id = underlying["drive_id"]
            self.altLink = underlying["altLink"]
            self.last_modified_date = underlying["last_modified_date"]
            self.last_modified_by = underlying["last_modified_by"]
        else:
            self.drive_id = underlying["id"]
            self.altLink = underlying["alternateLink"]
            self.last_modified_date = parse_datetime(underlying["modifiedDate"])
            self.last_modified_by = underlying["lastModifyingUser"]["emailAddress"]

        self._underlying = underlying
        self.title = underlying["title"]
        self.mimeType = underlying["mimeType"]
        self.selfLink = underlying["selfLink"]


class GoogleDriveTextFile(GoogleDriveFile):
    format: str
    content_plain: ParsedContent
    content_rich: ParsedContent
    _is_rich: bool  # Transient state - not serialized

    def __init__(self, underlying: dict):
        super().__init__(underlying)
        self.format = infer_format(self.title)

    def get_download_link(self) -> str:
        mime_type = "text/html" if self._is_rich else "text/plain"
        return self.selfLink + f"/export?mimeType={mime_type}"

    def to_json(self) -> dict:
        return GoogleDriveTextFileSerializer(self).data

    def parse_content(self, raw: str, is_rich=False):
        content = ParsedContent(raw, self.format)
        print(content)
        if is_rich:
            self.content_rich = content
        else:
            self.content_plain = content


class GoogleDriveImageFile(GoogleDriveFile):
    thumbnail_link: str
    src_large: Optional[str]
    src_medium: Optional[str]

    def to_json(self) -> dict:
        return GoogleDriveImageFileSerializer(self).data

    def __init__(self, underlying: dict, from_serialized=False):
        super().__init__(underlying, from_serialized)
        if from_serialized:
            self.thumbnail_link = underlying["thumbnail_link"]
        else:
            self.thumbnail_link = underlying["thumbnailLink"]


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
    # #_underlying = serializers.JSONField(source="*")
    #
    # def create(self, validated_data):
    #     return GoogleDriveFile(validated_data["_underlying"])


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

    # def create(self, validated_data):
    #     return GoogleDriveImageFile(validated_data["_underlying"])

class S3ItemSerializer(serializers.Serializer):
    bucket = serializers.CharField()
    region = serializers.CharField()
    key = serializers.CharField()
    meta = serializers.JSONField()


# Utils
# TODO - convert to an ENUM type
FORMAT_AML = "AML"
FORMAT_MD = "MD"
FORMAT_PLAIN = "PLAIN"

FORMAT_TABLE = {"aml": FORMAT_AML, "md": FORMAT_MD}

MarkdownParser = Markdown()


def infer_format(file_title: str) -> str:
    extension = file_title.split(".")[-1].lower()
    return FORMAT_TABLE.get(extension, FORMAT_PLAIN)
