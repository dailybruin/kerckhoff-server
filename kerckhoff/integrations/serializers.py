from rest_framework import serializers

from kerckhoff.integrations.models import Integration
from kerckhoff.users.serializers import SimpleUserSerializer


class IntegrationSerializer(serializers.ModelSerializer):
    created_by = SimpleUserSerializer(read_only=True)
    active = serializers.SerializerMethodField()

    def get_active(self, obj: Integration):
        return obj.auth_data.active

    class Meta:
        model = Integration
        fields = (
            "id",
            "name",
            "integration_type",
            "created_by",
            "created_at",
            "active",
        )
        read_only = ("id", "created_by", "created_at", "active")
