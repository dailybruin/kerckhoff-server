from rest_framework import serializers
from datetime import datetime
from typing import Optional
from django.utils.dateparse import parse_datetime


class GoogleDriveFile:
    drive_id: str
    title: str
    mimeType: str
    selfLink: str
    altLink: str
    last_modified_by: str
    last_modified_date: datetime
    _underlying: dict

    def to_json(self) -> dict:
        return GoogleDriveFileSerializer(self).data

    def __init__(self, underlying: dict):
        self._underlying = underlying
        self.drive_id = underlying["id"]
        self.title = underlying["title"]
        self.mimeType = underlying["mimeType"]
        self.selfLink = underlying["selfLink"]
        self.altLink = underlying["alternateLink"]
        self.last_modified_date = parse_datetime(underlying["modifiedDate"])
        self.last_modified_by = underlying["lastModifyingUser"]["emailAddress"]


class GoogleDriveImageFile(GoogleDriveFile):
    thumbnail_link: str
    src_large: Optional[str]
    src_medium: Optional[str]

    def to_json(self) -> dict:
        return GoogleDriveImageFileSerializer(self).data

    def __init__(self, underlying: dict):
        super().__init__(underlying)
        self.thumbnail_link = underlying["thumbnailLink"]


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


class GoogleDriveImageFileSerializer(GoogleDriveFileSerializer):
    thumbnail_link = serializers.URLField()
    src_large = serializers.CharField(required=False)
    src_medium = serializers.CharField(required=False)

    # def create(self, validated_data):
    #     return GoogleDriveImageFile(validated_data["_underlying"])