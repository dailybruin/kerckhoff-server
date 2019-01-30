import uuid

from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.db import models

from .constants import *

class PackageSet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=32, unique=True) # ??
    drive_folder_id = models.CharField(max_length=512, blank=True)
    drive_folder_url = models.URLField()
    metadata = JSONField(blank=True, default=dict, null=True)
    # created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
class Package(models.Model):
    # slug = models.CharField(max_length=64, primary_key=True) # ??
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.CharField(max_length=64)
    package_set = models.ForeignKey(PackageSet, on_delete=models.PROTECT)
    
    class Meta:
        unique_together = ('package_set', 'slug',)

    # description = models.TextField(blank=True)
    drive_folder_id = models.CharField(max_length=512)
    drive_folder_url = models.URLField()
    metadata = JSONField(blank=True, default=dict, null=True)
    images = JSONField(blank=True, default=dict, null=True)
    data = JSONField(blank=True, default=dict, null=True)
    processing = models.BooleanField(default=False)
    cached_article_preview = models.TextField(blank=True)
    publish_date = models.DateField()
    last_fetched_date = models.DateTimeField(null=True, blank=True)
    _content_type = models.CharField(max_length=2, choices=CONTENT_TYPE_CHOICES, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Versioning
    latest_version = models.ForeignKey('PackageVersion', related_name='versions', on_delete=models.CASCADE, null=True, blank=True)


# Snapshot of a Package instance at a particular time
class PackageVersion(models.Model):
    package = models.ForeignKey(Package, on_delete=models.PROTECT)
    # creator = models.ForeignKey(User, on_delete=models.CASCADE)
    version_description = models.TextField(blank=True)
    article_data = models.TextField(blank=True)
    data = JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    #TODO 
    # Add package stateEnum for future (freeze should change state)
