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

    def as_dict(self):
        return {
            "slug": self.slug,
            "gdrive_url": self.drive_folder_url,
        }

    def save(self, *args, **kwargs):
        self.drive_folder_id = self.drive_folder_url.rsplit('/', 1)[-1]
        super().save(*args, **kwargs)

    def populate(self, user):
        print("Starting populate for %s" % self.slug)
        google = get_oauth2_session(user)
        # we don't care about the aml_data dict here
        _, _, folders, _ = list_folder(google, self)
        instances = []
        for folder in folders:
            try:
                exists = Package.objects.get(slug=folder["title"])
                instances.append(exists)
            except Package.DoesNotExist:
                pkg = Package.objects.create(
                    slug=folder["title"],
                    drive_folder_id=folder["id"],
                    drive_folder_url=folder["alternateLink"],
                    publish_date=timezone.now(),
                    package_set=self
                )
                instances.append(pkg)
        for instance in instances:
            print("Processing %s" % instance.slug)
            try:
                instance.fetch_from_gdrive(user)
            except Exception as e:
                print("%s failed with error: %s" % (instance.slug, e))
                continue