from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .models import PackageSet, Package, PackageVersion, PackageItem

from kerckhoff.users.serializers import UserSerializer

from taggit_serializer.serializers import TagListSerializerField, TaggitSerializer


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
    version_description = serializers.CharField(required=True)

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

        read_only_fields = (
            "id",
            "id_num",
            "package",
            "creator",
            "created_at",
            "updated_at",
        )


class CreatePackageVersionSerializer(PackageVersionSerializer):
    included_items = serializers.ListField(child=serializers.CharField())

    def create(self, validated_data):
        print(validated_data)

    @staticmethod
    def validate_included_items(obj):
        print(obj)

    class Meta(PackageVersionSerializer.Meta):
        fields = PackageVersionSerializer.Meta.fields + ("included_items",)
        validators = []


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


class RetrievePackageSerializer(PackageSerializer):
    version_data = serializers.SerializerMethodField()

    def get_version_data(self, obj: Package):
        version_number = self.context["version_number"]
        package_version = obj.get_version(version_number)
        if package_version is not None:
            data = PackageVersionSerializer(package_version).data
        else:
            data = None
        return data

    class Meta(PackageSerializer.Meta):
        fields = PackageSerializer.Meta.fields + ("version_data",)
        read_only_fields = PackageSerializer.Meta.read_only_fields + ("version_data",)
