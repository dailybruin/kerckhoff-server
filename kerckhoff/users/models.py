import uuid
from django.db import models
from django.conf import settings
from django.dispatch import receiver
from django.contrib.auth.models import AbstractUser
from django.contrib.auth import get_user_model
from django.utils.encoding import python_2_unicode_compatible
from django.db.models.signals import post_save
from django.utils.crypto import get_random_string
from rest_framework.authtoken.models import Token


@python_2_unicode_compatible
class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(
        max_length=255,
        unique=True,
    )

    def __str__(self):
        return self.username


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)


def generate_username(firstname, lastname, index: int = 0) -> str:
    username = f"{firstname}{lastname}".lower() + (index if index > 0 else "")
    if get_user_model().objects.filter(username=username).exists():
        return generate_username(firstname, lastname, index + 1)
    return username


def generate_password() -> str:
    return get_random_string()
