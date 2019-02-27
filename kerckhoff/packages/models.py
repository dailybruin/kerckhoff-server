import uuid
from typing import NamedTuple, List
import re

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.validators import RegexValidator
from django.db import models
from django.contrib.auth import get_user_model

from kerckhoff.packages.exceptions import GoogleDriveNotConfiguredException
from kerckhoff.packages.operations.google_drive import GoogleDriveOperations
from kerckhoff.users.models import User as AppUser

User: AppUser = get_user_model()

slug_with_dots_re = re.compile(r'^[-a-zA-Z0-9_.]+\Z')
validate_slug_with_dots = RegexValidator(
    slug_with_dots_re,
    "Enter a valid 'slug' consisting of letters, dots, numbers, underscores or hyphens.",
    'invalid'
)

GOOGLE_DRIVE_META_KEY = "google_drive"


class GoogleDriveMeta(NamedTuple):
    folder_id: str
    folder_url: str


class PackageSet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=32, unique=True)
    metadata = JSONField(blank=True, default=dict, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.slug

    def get_or_create_gdrive_meta(self) -> GoogleDriveMeta:
        data = self.metadata.get(GOOGLE_DRIVE_META_KEY)
        if data is None:
            data = GoogleDriveMeta("", "")._asdict()
            self.metadata[GOOGLE_DRIVE_META_KEY] = data
            self.save()
        return GoogleDriveMeta(**data)

    def get_new_packages_from_gdrive(self) -> List["Package"]:
        gdrive_info = self.get_or_create_gdrive_meta()
        if not gdrive_info.folder_id:
            raise GoogleDriveNotConfiguredException(self)

        ops = GoogleDriveOperations(self.created_by)

        items, _ = ops.list_folder(gdrive_info.folder_id)
        folders = ops.filter_items(items, GoogleDriveOperations.FilterMethod.FOLDER)
        created_packages = []
        for folder in folders:
            slug = folder["title"]
            package, created = Package.objects.get_or_create(slug=slug, package_set=self, defaults={
                "created_by": self.created_by,
                "metadata": {
                    GOOGLE_DRIVE_META_KEY: GoogleDriveMeta(folder_id=folder["id"],
                                                           folder_url=folder["alternateLink"])._asdict()
                }
            })
            if created:
                created_packages.append(package)
        return created_packages


class Package(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.CharField(max_length=64, validators=[validate_slug_with_dots, ])
    package_set = models.ForeignKey(PackageSet, on_delete=models.PROTECT)
    metadata = JSONField(blank=True, default=dict, null=True)
    cached = JSONField(blank=True, default=dict, null=True)
    last_fetched_date = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Versioning
    latest_version = models.ForeignKey('PackageVersion', related_name='versions', on_delete=models.CASCADE, null=True,
                                       blank=True)
    def __str__(self):
        return self.slug

    class Meta:
        unique_together = ('package_set', 'slug',)

# Snapshot of a Package instance at a particular time
# A PackageVersion object is a specific combination of PackageItem objects

class PackageVersion(models.Model):
    """
    Snapshot of a Package instance at a particular time
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    version_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.slug    

    # Add package stateEnum for future (freeze should change state)

class PackageItem(models.Model):   
    TEXT = 'txt'
    AML = 'aml'
    IMAGE = 'img'
    MARKDOWN = 'mdn'
    SPREADSHEET = 'xls'
    
    DTYPE_CHOICES = (
        (TEXT, "TEXT"),
        (AML, "ARCHIEML"),
        (IMAGE, "IMAGE"),
        (MARKDOWN, "MARKDOWN"),
        (SPREADSHEET, "SPREADSHEET"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    package_version = models.ForeignKey(PackageVersion, on_delete=models.CASCADE)
    data_type = models.CharField(max_length=3, choices=DTYPE_CHOICES, default=TEXT)
    data = JSONField(blank=True, default=dict)
    file_name = models.CharField(max_length=64)
    mime_types = models.CharField(max_length=64)
