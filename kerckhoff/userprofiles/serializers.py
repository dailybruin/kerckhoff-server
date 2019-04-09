from rest_framework import serializers
from .models import UserProfile


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = (
            "user",
            "title",
            "profile_img",
            "description",
            "linkedin_url",
            "github_url",
        )
        read_only_fields = ("user",)
