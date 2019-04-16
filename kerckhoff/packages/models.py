import re
import uuid
from typing import List, NamedTuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.postgres.fields import JSONField
from django.core.validators import RegexValidator
from django.utils.timezone import now

from django.db import models
from kerckhoff.packages.exceptions import GoogleDriveNotConfiguredException
from kerckhoff.packages.operations.google_drive import GoogleDriveOperations
from kerckhoff.packages.operations.models import (
    GoogleDriveFile,
    GoogleDriveFileSerializer,
    GoogleDriveImageFile,
    GoogleDriveImageFileSerializer,
    GoogleDriveTextFile,
    FORMAT_MD,
)
from kerckhoff.packages.operations.utils import GoogleDocHTMLCleaner
from kerckhoff.users.models import User as AppUser


User: AppUser = get_user_model()

slug_with_dots_re = re.compile(r"^[-a-zA-Z0-9_.]+\Z")
validate_slug_with_dots = RegexValidator(
    slug_with_dots_re,
    "Enter a valid 'slug' consisting of letters, dots, numbers, underscores or hyphens.",
    "invalid",
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
            package, created = Package.objects.get_or_create(
                slug=slug,
                package_set=self,
                defaults={
                    "created_by": self.created_by,
                    "metadata": {
                        GOOGLE_DRIVE_META_KEY: GoogleDriveMeta(
                            folder_id=folder["id"], folder_url=folder["alternateLink"]
                        )._asdict()
                    },
                },
            )
            if created:
                created_packages.append(package)
        return created_packages


class Package(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.CharField(max_length=64, validators=[validate_slug_with_dots])
    package_set = models.ForeignKey(PackageSet, on_delete=models.PROTECT)
    metadata = JSONField(blank=True, default=dict, null=True)
    cached = JSONField(blank=True, default=dict, null=True)
    last_fetched_date = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Versioning
    latest_version = models.ForeignKey(
        "PackageVersion",
        related_name="versions",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    def __str__(self):
        return self.package_set.slug + "/" + self.slug

    class Meta:
        unique_together = ("package_set", "slug")

    def get_or_create_gdrive_meta(self) -> GoogleDriveMeta:
        data = self.metadata.get(GOOGLE_DRIVE_META_KEY)
        if data is None:
            data = GoogleDriveMeta("", "")._asdict()
            self.metadata[GOOGLE_DRIVE_META_KEY] = data
            self.save()
        return GoogleDriveMeta(**data)

    def fetch_cache(self):
        ops = GoogleDriveOperations(self.created_by)
        items, _ = ops.list_folder(self.get_or_create_gdrive_meta().folder_id)

        # Images / Media
        images_raw = ops.filter_items(items, GoogleDriveOperations.FilterMethod.IMAGES)
        images = [GoogleDriveImageFile(image) for image in images_raw]

        # Content / Data Files
        content_files_raw = ops.filter_items(
            items, GoogleDriveOperations.FilterMethod.EXTENSION, ("aml", "md", "txt")
        )
        content_files: List[GoogleDriveTextFile] = [
            GoogleDriveTextFile(content_file) for content_file in content_files_raw
        ]

        # Export content files as HTML and plaintext
        for file in content_files:
            if file.format != FORMAT_MD:
                # Markdown does not support HTML format
                file._is_rich = True
                file.parse_content(
                    GoogleDocHTMLCleaner.clean(ops.download_item(file).text),
                    is_rich=True,
                )

            file._is_rich = False
            file.parse_content(
                ops.download_item(file).content.decode("utf-8-sig").encode("utf-8"),
                is_rich=False,
            )

        to_update: List[GoogleDriveFile] = images + content_files

        as_json = [i.to_json() for i in to_update]

        # TODO: further process
        self.last_fetched_date = now()
        self.cached = as_json
        self.save()

    def create_version(self, user, change_summary, package_items_set):
        """Creates new PackageVersion object
        
        Arguments:
            user {User} -- User object, required argument
            package_items_set {set} -- set of PackageItem ForeignKeys, TODO views to handle this?
        """
        id_num = 0
        if self.packageversion_set.count() > 1:
            id_num = self.packageversion_set.count() - 1
        # Add package items
        new_pv = self.packageversion_set.create(
            package=self,
            creator=user,
            version_description=change_summary,
            id_num=id_num,
        )
        for package_item in package_items_set:
            new_pv.packageitem_set.add(package_item)
        new_pv.save()
        self.latest_version = new_pv
        # return 'Successfully created PackageVersion object!'


# Snapshot of a Package instance, defined as a collection of PackageItem objects
class PackageVersion(models.Model):
    """
    Snapshot of a Package instance at a particular time
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    id_num = models.IntegerField(
        default=0
    )  # Integer wrapper for uuid for UI referencing, set during PackageVersion creation. Zero-indexed.
    title = models.CharField(max_length=64)
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    version_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.package.slug + "/" + str(self.id_num)

    # Add package stateEnum for future (freeze should change state)


class PackageItem(models.Model):
    TEXT = "txt"
    AML = "aml"
    IMAGE = "img"
    MARKDOWN = "mdn"
    SPREADSHEET = "xls"

    DTYPE_CHOICES = (
        (TEXT, "TEXT"),
        (AML, "ARCHIEML"),
        (IMAGE, "IMAGE"),
        (MARKDOWN, "MARKDOWN"),
        (SPREADSHEET, "SPREADSHEET"),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    package_versions = models.ManyToManyField(PackageVersion)
    data_type = models.CharField(max_length=3, choices=DTYPE_CHOICES, default=TEXT)
    data = JSONField(blank=True, default=dict)
    file_name = models.CharField(max_length=64)
    mime_types = models.CharField(max_length=64)
