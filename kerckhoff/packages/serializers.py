from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from .models import PackageSet, Package

from kerckhoff.users.serializers import UserSerializer


class PackageSetSerializer(serializers.ModelSerializer):
    created_by = UserSerializer(read_only=True)

    class Meta:
        model = PackageSet
        fields = ("id", "slug", "metadata", "created_by", "created_at", "updated_at")
        read_only_fields = ("id", "created_by", "created_at", "updated_at")


class PackageSerializer(serializers.ModelSerializer):
    package_set = serializers.StringRelatedField()
    created_by = UserSerializer(read_only=True)

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
        )
        read_only_fields = (
            "id",
            "package_set",
            "cached",
            "last_fetched_date",
            "created_by",
            "created_at",
            "updated_at",
        )
        validators = [
            UniqueTogetherValidator(
                queryset=Package.objects.all(), fields=("slug", "package_set")
            )
        ]
