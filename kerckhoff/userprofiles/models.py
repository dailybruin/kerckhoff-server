from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.conf import settings

from kerckhoff.users.auth.exceptions import NoRefreshTokenException

from .roles import Contributor, all_roles


class UserProfile(models.Model):
    """The additional profile information for a user
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True
    )
    title = models.CharField(max_length=100, blank=True, default="Contributor")
    profile_img = models.ImageField(upload_to="profile/imgs/", blank=True, null=True)
    description = models.CharField(max_length=500, blank=True, default="")
    linkedin_url = models.URLField(blank=True, default="")
    github_url = models.URLField(blank=True, default="")

    auth_data = JSONField(encoder=DjangoJSONEncoder, default=dict)
    role = models.CharField(
        max_length=2, choices=[(r.ABBRV, r.__name__) for r in all_roles]
    )

    def get_auth_information(self, provider: str) -> dict:
        """Retrieve the OAuth information for the user
        
        Arguments:
            provider {str} -- The Oauth provider, e.g. "google"
        
        Returns:
            dict -- returns a dictionary of the OAuth information
        """
        return self.auth_data.get(provider)

    def update_auth_information(self, provider: str, auth_info: dict):
        """Updates the OAuth information for the user
        
        Arguments:
            provider {str} -- The Oauth provider, e.g. "google"
            auth_info {dict} -- A dictionary of the OAuth information
        
        Raises:
            NoRefreshTokenException -- A refresh token is not provided
        """

        current_auth_info = self.auth_data.get(provider)
        if current_auth_info is None:
            if "refresh_token" not in auth_info:
                raise NoRefreshTokenException()
            self.auth_data = dict()
            self.auth_data[provider] = auth_info
        else:
            assert isinstance(current_auth_info, dict)
            current_auth_info.update(auth_info)
        self.save()


@receiver(post_save, sender=get_user_model())
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance, role=Contributor.ABBRV)
