import uuid

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models

from .constants import *


class PackageSet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=32, unique=True) # ??
    metadata = JSONField(blank=True, default=dict, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
class Package(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.CharField(max_length=64)
    package_set = models.ForeignKey(PackageSet, on_delete=models.PROTECT)
    metadata = JSONField(blank=True, default=dict, null=True)
    cached = JSONField(blank=True, default=dict, null=True)
    last_fetched_date = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Versioning
    latest_version = models.ForeignKey('PackageVersion', related_name='versions', on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        unique_together = ('package_set', 'slug',)

# Snapshot of a Package instance at a particular time
class PackageVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    package = models.ForeignKey(Package, on_delete=models.PROTECT)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    version_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    #TODO 
    # Add package stateEnum for future (freeze should change state)
