from rest_framework import serializers
from .models import User
from kerckhoff.userprofiles.serializers import UserProfileSerializer
from kerckhoff.userprofiles.models import UserProfile


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
        userprofile = instance.userprofile

        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.save()

        userprofile.title = userprofile_data.get("title", userprofile.title)
        userprofile.profile_img = userprofile_data.get(
            "profile_img", userprofile.profile_img
        )
        userprofile.description = userprofile_data.get(
            "description", userprofile.description
        )
        userprofile.linkedin_url = userprofile_data.get(
            "linkedin_url", userprofile.linkedin_url
        )
        userprofile.github_url = userprofile_data.get(
            "github_url", userprofile.github_url
        )
        userprofile.save()

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
