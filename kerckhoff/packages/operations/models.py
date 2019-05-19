from datetime import datetime
from typing import Optional

import frontmatter
from django.utils.dateparse import parse_datetime
from markdown import Markdown
from rest_framework import serializers

from kerckhoff.packages import constants
import archieml


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
                aml_content = archieml.loads(self.raw)

                # HACK: Fixes a bad bug in the archieml parser
                for key, value in aml_content.items():
                    if isinstance(value, list):
                        for index, item in enumerate(value):
                            if isinstance(item, dict):
                                if (
                                    item.get("type") is None
                                    and item.get("value")
                                    and isinstance(value[index - 1], dict)
                                    and value[index - 1].get("type")
                                ):
                                    aml_content[key][index - 1]["value"] = item["value"]
                                    aml_content[key][index] = None
                        aml_content[key] = [
                            i for i in aml_content[key] if i is not None
                        ]

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
            self.last_modified_by = underlying["lastModifyingUser"]["emailAddress"]

        self._underlying = underlying
        self.title = underlying["title"]
        self.mimeType = underlying["mimeType"]
        self.selfLink = underlying["selfLink"]

    def get_download_link(self) -> str:
        return self.selfLink + "?alt=media"

    def get_data_type(self) -> str:
        return constants.TEXT

    def get_underlying(self) -> dict:
        # TODO - override this method to customize the data representation
        return self._underlying

    def to_json(self) -> dict:
        return GoogleDriveFileSerializer(self).data

    @classmethod
    def from_json(cls, serialized: dict):
        return {
            GoogleDriveTextFile._code: GoogleDriveTextFile.from_json,
            GoogleDriveImageFile._code: GoogleDriveImageFile.from_json,
        }.get(serialized["_code"], lambda x: GoogleDriveFile(x, from_serialized=True))(
            serialized
        )


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

    def to_json(self) -> dict:
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

    _code = "GDRIVE_IMG"

    def __init__(self, underlying: dict, from_serialized=False):
        super().__init__(underlying, from_serialized)
        if from_serialized:
            self.thumbnail_link = underlying["thumbnail_link"]
        else:
            self.thumbnail_link = underlying["thumbnailLink"]

    def get_data_type(self):
        return constants.IMAGE

    def to_json(self) -> dict:
        return GoogleDriveImageFileSerializer(self).data

    @classmethod
    def from_json(cls, serialized: dict):
        return GoogleDriveImageFile(serialized, from_serialized=True)


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

FormatTable = {"aml": FORMAT_AML, "md": FORMAT_MD}

MarkdownParser = Markdown()


def infer_format(file_title: str) -> str:
    extension = file_title.split(".")[-1].lower()
    return FormatTable.get(extension, FORMAT_PLAIN)
