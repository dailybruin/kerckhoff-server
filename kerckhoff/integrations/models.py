from django.db import models
from django.contrib.postgres.fields import JSONField
from django.conf import settings

from rest_framework.exceptions import APIException

from requests_oauthlib import OAuth2Session

from typing import Optional
from dataclasses import dataclass, asdict

from kerckhoff.packages.models import PackageSet, PackageVersion, PackageItem

import uuid
import logging

logger = logging.getLogger(__name__)

WORDPRESS_COM = "wpc"

SUPPORTED_INTEGRATIONS = ((WORDPRESS_COM, "Wordpress.com"),)
SUPPORTED_INTEGRATIONS_SET = {WORDPRESS_COM}


@dataclass
class AuthData:
    active: bool
    state: str
    access_token: Optional[str]
    token_type: Optional[str]

    @classmethod
    def empty(cls):
        return asdict(cls(active=False, state="", access_token=None, token_type=None))

    def get_oauth2_session(self, token=None):
        token = (
            token
            if token
            else {"access_token": self.access_token, "token_type": self.token_type}
        )
        return OAuth2Session(
            client_id=self.Meta.CLIENT_ID,
            token=token,
            redirect_uri=settings.SITE_HOST + self.Meta.REDIRECT_PATH,
        )

    def get_authorization_url(self):
        pass

    def get_token(self, code: str):
        pass

    def publish(self, **kwargs):
        pass

    class Meta:
        AUTH_ENDPOINT: str
        TOKEN_ENDPOINT: str
        CLIENT_ID: str
        CLIENT_SECRET: str
        REDIRECT_PATH = "integrations/auth/redirect"


@dataclass
class WordpressComAuthData(AuthData):

    blog_id: Optional[str] = None
    blog_url: Optional[str] = None

    def get_authorization_url(self):
        auth_url, state = self.get_oauth2_session().authorization_url(
            self.Meta.AUTH_ENDPOINT
        )
        self.state = state
        return auth_url

    def get_token(self, code: str):
        token = self.get_oauth2_session().fetch_token(
            token_url=self.Meta.TOKEN_ENDPOINT,
            code=code,
            client_secret=self.Meta.CLIENT_SECRET,
            include_client_id=True,
        )
        self.blog_id = token["blog_id"]
        self.blog_url = token["blog_url"]
        self.access_token = token["access_token"]
        self.token_type = token["token_type"]
        self.active = True
        return self

    def publish(self, **kwargs):
        # TODO - demo code, do not use
        session = self.get_oauth2_session()
        res = session.post(
            f"https://public-api.wordpress.com/wp/v2/sites/{self.blog_id}/posts", kwargs
        )
        print("Publish", kwargs, res)

    class Meta(AuthData.Meta):
        AUTH_ENDPOINT = "https://public-api.wordpress.com/oauth2/authorize"
        TOKEN_ENDPOINT = "https://public-api.wordpress.com/oauth2/token"
        CLIENT_ID = settings.INTEGRATIONS["WPC"]["CLIENT_ID"]
        CLIENT_SECRET = settings.INTEGRATIONS["WPC"]["CLIENT_SECRET"]


class Integration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128)
    package_set = models.ForeignKey(PackageSet, on_delete=models.CASCADE)
    integration_type = models.CharField(max_length=3, choices=SUPPORTED_INTEGRATIONS)
    _auth_data = JSONField(default=AuthData.empty)
    params = JSONField(default=dict, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    _auth_data_underlying: Optional[AuthData] = None

    def __str__(self):
        return f"({self.package_set.slug}): {self.integration_type}-{self.name}"

    def save(self, *args, **kwargs):
        if self._auth_data_underlying:
            self._auth_data = asdict(self._auth_data_underlying)
        super().save(*args, **kwargs)

    @property
    def auth_data(self):
        if self._auth_data_underlying is None:
            self._auth_data_underlying = {WORDPRESS_COM: WordpressComAuthData}.get(
                self.integration_type, AuthData
            )(**self._auth_data)
        return self._auth_data_underlying

    def begin_authorization(self):
        auth_url = self.auth_data.get_authorization_url()
        self.save()
        return auth_url

    def validate(self, code: str):
        try:
            self.auth_data.get_token(code)
            self.save()
        except Exception as e:
            logger.error(e)
            raise APIException(detail="Failed to exchange code for access token!")

    def publish(self, package_version: PackageVersion):
        # TODO: this is NOT the final publish code
        article_file: PackageItem = package_version.packageitem_set.filter(
            file_name="article.md"
        ).first()
        if article_file:
            data = article_file.data.get("content_plain")
            self.auth_data.publish(
                title=data["data"]["title"],
                slug=package_version.package.slug,
                content=data["html"],
                status="publish",
            )
