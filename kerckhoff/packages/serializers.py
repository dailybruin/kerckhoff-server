from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .models import PackageSet, Package, PackageVersion, PackageItem

from kerckhoff.users.serializers import UserSerializer

from taggit_serializer.serializers import (TagListSerializerField,
                                            TaggitSerializer)

class PackageSetSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = PackageSet
        fields = ("id", "slug", "metadata", "created_by", "created_at", "updated_at")
        read_only_fields = ("id", "created_by", "created_at", "updated_at")


class PackageSerializer(TaggitSerializer, serializers.ModelSerializer):
    package_set = serializers.StringRelatedField()
    created_by = UserSerializer(read_only=True)
    latest_version = serializers.StringRelatedField()
    tags = TagListSerializerField()

    class Meta:
        model = Package
        fields = (
            "id",
            "slug",
            "package_set",
            "metadata",
            "cached",
            "last_fetched_date",
            "created_by",
            "created_at",
            "updated_at",
            "tags",
            "latest_version",
        )
        read_only_fields = (
            "id",
            "package_set",
            "cached",
            "last_fetched_date",
            "created_by",
            "created_at",
            "updated_at",
            "latest_version",
        )
        validators = [
            UniqueTogetherValidator(
                queryset=Package.objects.all(), fields=("slug", "package_set")
            )
        ]


class PackageVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PackageVersion
        fields = (
            "id",
            "id_num",
            "title",
            "package",
            "creator",
            "version_description",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "id_num", "package", "creator", "created_at", "updated_at")


class RetrievePackageSerializer(PackageSerializer):
    package_version = PackageVersionSerializer()

    def to_representation(self, obj):
        package = super().to_representation(obj)
        package_version = obj.get_version(self.context.get("version_number"))
        if package_version is not None:
            package["package_version"] = PackageVersionSerializer(package_version).data
        return package

class PackageItemSerializer(TaggitSerializer, serializers.ModelSerializer):
    package_versions = serializers.StringRelatedField(many=True)
    tags = TagListSerializerField()

    class Meta:
        model = PackageItem
        fields = (
            "id",
            "package_versions",
            "data_type",
            "data",
            "file_name",
            "mime_types",
            "tags",
        )
        read_only_fields = ("id", "package_versions", "data_type")