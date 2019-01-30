import re
import logging

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from requests_oauthlib import OAuth2Session

# from .utils import transfer_to_s3, rewrite_image_url
from .google_drive_actions import get_file, get_oauth2_session, list_folder, create_package, add_to_repo_folder
from .constants import *

logger = logging.getLogger(settings.APP_NAME)

class PackageSet(models.Model):
    slug = models.SlugField(max_length=32, primary_key=True)
    drive_folder_id = models.CharField(max_length=512, blank=True)
    drive_folder_url = models.URLField()
    default_content_type = models.CharField(max_length=2, choices=CONTENT_TYPE_CHOICES, default=PLAIN_TEXT)

class Package(models.Model):
    slug = models.CharField(max_length=64, primary_key=True)
    description = models.TextField(blank=True)
    drive_folder_id = models.CharField(max_length=512)
    drive_folder_url = models.URLField()
    metadata = JSONField(blank=True, default=dict, null=True)
    images = JSONField(blank=True, default=dict, null=True)
    data = JSONField(blank=True, default=dict, null=True)
    processing = models.BooleanField(default=False)
    cached_article_preview = models.TextField(blank=True)
    publish_date = models.DateField()
    last_fetched_date = models.DateTimeField(null=True, blank=True)
    package_set = models.ForeignKey(PackageSet, on_delete=models.PROTECT)
    _content_type = models.CharField(max_length=2, choices=CONTENT_TYPE_CHOICES, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Versioning
    latest_version = models.ForeignKey('PackageVersion', related_name='versions', on_delete=models.CASCADE, null=True, blank=True)


# Snapshot of a Package instance at a particular time
class PackageVersion(models.Model):
    package = models.ForeignKey(Package, on_delete=models.PROTECT)
    creator = models.ForeignKey(User, on_delete=models.CASCADE)
    version_description = models.TextField(blank=True)
    article_data = models.TextField(blank=True)
    data = JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    #TODO 
    # Add package stateEnum for future (freeze should change state)