# Generated by Django 2.1.5 on 2019-05-19 01:35

from django.conf import settings
import django.contrib.postgres.fields.jsonb
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import re
import taggit.managers
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("taggit", "0003_taggeditem_add_unique_index"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Package",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "slug",
                    models.CharField(
                        max_length=64,
                        validators=[
                            django.core.validators.RegexValidator(
                                re.compile("^[-a-zA-Z0-9_.]+\\Z"),
                                "Enter a valid 'slug' consisting of letters, dots, numbers, underscores or hyphens.",
                                "invalid",
                            )
                        ],
                    ),
                ),
                (
                    "metadata",
                    django.contrib.postgres.fields.jsonb.JSONField(
                        blank=True, default=dict, null=True
                    ),
                ),
                (
                    "cached",
                    django.contrib.postgres.fields.jsonb.JSONField(
                        blank=True, default=list, null=True
                    ),
                ),
                ("last_fetched_date", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PackageItem",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "data_type",
                    models.CharField(
                        choices=[
                            ("txt", "TEXT"),
                            ("aml", "ARCHIEML"),
                            ("img", "IMAGE"),
                            ("mdn", "MARKDOWN"),
                            ("xls", "SPREADSHEET"),
                        ],
                        default="txt",
                        max_length=3,
                    ),
                ),
                (
                    "data",
                    django.contrib.postgres.fields.jsonb.JSONField(
                        blank=True, default=dict
                    ),
                ),
                ("file_name", models.CharField(max_length=64)),
                ("mime_types", models.CharField(max_length=64)),
            ],
        ),
        migrations.CreateModel(
            name="PackageSet",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("slug", models.SlugField(max_length=32, unique=True)),
                (
                    "metadata",
                    django.contrib.postgres.fields.jsonb.JSONField(
                        blank=True, default=dict, null=True
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="PackageVersion",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("id_num", models.IntegerField(default=0)),
                ("title", models.CharField(max_length=64)),
                ("version_description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "package",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="packages.Package",
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="packageitem",
            name="package_versions",
            field=models.ManyToManyField(to="packages.PackageVersion"),
        ),
        migrations.AddField(
            model_name="packageitem",
            name="tags",
            field=taggit.managers.TaggableManager(
                help_text="A comma-separated list of tags.",
                through="taggit.TaggedItem",
                to="taggit.Tag",
                verbose_name="Tags",
            ),
        ),
        migrations.AddField(
            model_name="package",
            name="latest_version",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="versions",
                to="packages.PackageVersion",
            ),
        ),
        migrations.AddField(
            model_name="package",
            name="package_set",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT, to="packages.PackageSet"
            ),
        ),
        migrations.AddField(
            model_name="package",
            name="tags",
            field=taggit.managers.TaggableManager(
                help_text="A comma-separated list of tags.",
                through="taggit.TaggedItem",
                to="taggit.Tag",
                verbose_name="Tags",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="package", unique_together={("package_set", "slug")}
        ),
    ]
