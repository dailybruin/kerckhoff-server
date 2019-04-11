import uuid
from django.db import models
from django.conf import settings
from kerckhoff.packages.models import Package, validate_slug_with_dots


class CommentContent:
    def __init__(self, format, text):
        self.format = format
        self.text = text

    def get_content(self):
        if self.format == "plaintext":
            return self.text
        else:
            return "lel"  # TODO: implement this


class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.CharField(max_length=64, validators=[validate_slug_with_dots])
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    comment_content = CommentContent

    class Meta:
        unique_together = ("slug", "package")
