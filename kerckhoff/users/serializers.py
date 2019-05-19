from rest_framework import serializers
from .models import User
from kerckhoff.userprofiles.serializers import UserProfileSerializer
from kerckhoff.userprofiles.models import UserProfile


class SimpleUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name")
        read_only_fields = ("id", "username", "first_name", "last_name")


class UserSerializer(serializers.ModelSerializer):
    userprofile = UserProfileSerializer()

    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "userprofile")
        read_only_fields = ("username",)

    def create(self, validated_data):
        userprofile_data = validated_data.pop("userprofile")
        user = User.objects.create(**validated_data)
        UserProfile.objects.create(user=user, **userprofile_data)
        return user

    def update(self, instance, validated_data):
        userprofile_data = validated_data.pop("userprofile")
        UserProfile.objects.filter(pk=instance.userprofile.pk).update(
            **userprofile_data
        )
        User.objects.filter(pk=instance.id).update(**validated_data)
        return instance


class CreateUserSerializer(serializers.ModelSerializer):
    def create(self, validated_data):
        # call create_user on user object. Without this
        # the password will be stored in plain text.
        user = User.objects.create_user(**validated_data)
        return user

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "password",
            "first_name",
            "last_name",
            "email",
            "auth_token",
        )
        read_only_fields = ("auth_token",)
        extra_kwargs = {"password": {"write_only": True}}
