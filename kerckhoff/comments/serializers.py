from rest_framework import serializers
from .models import Comment
from kerckhoff.users.serializers import UserSerializer
from rest_framework.validators import UniqueTogetherValidator

comment_content_formats = ["plaintext"]


class CommentContentSerializer(serializers.Serializer):
    format = serializers.CharField(allow_blank=False)
    text = serializers.CharField()

    def validate_format(self, value):
        if value not in comment_content_formats:
            raise serializers.ValidationError(
                "Comment content format is not in allowed list of formats"
            )
        return value


class CommentSerializer(serializers.ModelSerializer):
    package = serializers.StringRelatedField()
    created_by = UserSerializer(read_only=True)
    comment_content = CommentContentSerializer()

    class Meta:
        model = Comment
        fields = (
            "id",
            "package",
            "created_by",
            "created_at",
            "updated_at",
            "comment_content",
        )
        read_only_fields = ("id", "package", "created_by", "created_at")
