# Generated by Django 2.2 on 2019-05-26 20:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [("packages", "0001_initial")]

    operations = [
        migrations.RenameField(
            model_name="packageitem", old_name="mime_types", new_name="mime_type"
        )
    ]