from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from kerckhoff.users.models import User

from .roles import Contributor, all_roles


class UserProfile(models.Model):
    """The additional profile information for a user
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    title = models.CharField(max_length=100, blank=True, default="Contributor")
    profile_img = models.ImageField(upload_to="profile/imgs/", null=True)
    description = models.CharField(max_length=500, blank=True, default="")
    linkedin_url = models.URLField(blank=True, default="")
    github_url = models.URLField(blank=True, default="")

    auth_data = JSONField(encoder=DjangoJSONEncoder, default=dict)
    role = models.CharField(
        max_length=2, choices=[(r.ABBRV, r.__name__) for r in all_roles]
    )


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance, role=Contributor.ABBRV)
