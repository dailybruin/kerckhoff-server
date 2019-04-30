import uuid
from django.db import models
from django.contrib.postgres.fields import JSONField
from django.conf import settings
from kerckhoff.packages.models import Package


class CommentContent:
    def __init__(self, format, text):
        self.format = format
        self.text = text

    def get_content(self):
        if self.format == "plaintext":
            return self.text
        else:
            return self.text


class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    comment_content = JSONField(default=dict)
