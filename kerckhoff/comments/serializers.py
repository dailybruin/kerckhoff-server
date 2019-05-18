from rest_framework import serializers
from .models import Comment, CommentContent
from kerckhoff.users.serializers import UserSerializer
from rest_framework.validators import UniqueTogetherValidator

comment_content_formats = ["plaintext"]


class CommentContentSerializer(serializers.Serializer):
    format = serializers.CharField(allow_blank=False)
    text = serializers.CharField()

    def create(self, validated_data):
        return CommentContent(**validated_data)

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

    def create(self, validated_data):
        comment_content_data = validated_data.pop("comment_content")
        comment_content = CommentContentSerializer(data=comment_content_data)
        comment_content.is_valid()
        comment = Comment.objects.create(**validated_data)
        comment.comment_content = comment_content.validated_data
        comment.save()
        return comment

    def update(self, instance, validated_data):
        comment_content_data = validated_data.pop("comment_content")
        comment_content = CommentContentSerializer(data=comment_content_data)
        comment_content.is_valid()
        Comment.objects.filter(pk=instance.id).update(
            comment_content=comment_content.validated_data, **validated_data
        )
        return instance
