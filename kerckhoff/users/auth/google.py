import logging
from typing import Tuple

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from oauthlib.oauth2.rfc6749.errors import OAuth2Error
from requests import HTTPError
from requests_oauthlib import OAuth2Session
from rest_framework.exceptions import APIException

from kerckhoff.userprofiles.models import UserProfile
from kerckhoff.users.models import generate_username, generate_password, User as AppUser
from .exceptions import InvalidCodeException, NoAuthTokenException
from .strategy import OAuthStrategy

logger = logging.getLogger(__name__)

User: AppUser = get_user_model()


class GoogleOAuthStrategy(OAuthStrategy):
    """The strategy to handle OAuth for Google
    """

    BASE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://www.googleapis.com/oauth2/v4/token"
    PROFILE_ENDPOINT = "https://www.googleapis.com/oauth2/v1/userinfo"
    REDIRECT_PATH = "api-oauth/google/auth"

    PROVIDER_KEY = "google"

    oauth_session = OAuth2Session(
        settings.GOOGLE_OAUTH["CLIENT_ID"],
        redirect_uri=settings.SITE_HOST + REDIRECT_PATH,
        scope=settings.GOOGLE_OAUTH["SCOPES"],
    )

    additional_args = {
        "access_type": "offline",
        "hd": settings.GOOGLE_OAUTH["USER_DOMAIN"],
    }

    def login(self, code: str, **kwargs) -> Tuple[User, bool]:
        """Logs a user in using the OAuth code

        Args:
            code (str): The authorization code returned by the OAuth flow.

        Raises:
            InvalidCodeException: The authorization code is invalid
            NoRefreshTokenException: No refresh token was found for a new user

        Returns:
            Tuple[User, bool]: the user object and a flag to indicate if the user is newly registered
        """
        access_token = None
        register = False

        try:
            access_token = self.get_access_token(
                code, settings.GOOGLE_OAUTH["CLIENT_SECRET"]
            )
        except OAuth2Error as err:
            raise InvalidCodeException(err)

        profile = self._get_profile()
        current_user = User.objects.filter(email=profile["email"]).first()

        if current_user is None:
            current_user = self.register(profile)
            register = True

        current_user.userprofile.update_auth_information(self.PROVIDER_KEY, access_token)
        return current_user, register

    def register(self, profile: dict, **kwargs) -> AppUser:
        new_user: AppUser = User.objects.create_user(
            username=generate_username(profile["given_name"], profile["family_name"]),
            password=generate_password(),
            email=profile["email"])

        new_user.first_name = profile["given_name"]
        new_user.last_name = profile["family_name"]
        new_user.save()
        return new_user

    @classmethod
    def create_oauth2_session(cls, user: User) -> OAuth2Session:
        """ Create OAuth2 session which automatically updates the access token if it has expired """
        profile = UserProfile.objects.get(user=user)
        auth_info: dict = profile.get_auth_information(cls.PROVIDER_KEY)
        if auth_info is None or auth_info.get("refresh_token") is None:
            raise NoAuthTokenException()

        def token_updater(token: dict):
            token['expires_at'] = timezone.now()
            profile.update_auth_information(cls.PROVIDER_KEY, token)

        client_id = settings.GOOGLE_OAUTH["CLIENT_ID"]
        client_secret = settings.GOOGLE_OAUTH["CLIENT_SECRET"]

        extra = {
            'client_id': client_id,
            'client_secret': client_secret
        }

        expires_in = auth_info["expires_at"] - timezone.now().timestamp()
        token = {
            'access_token': auth_info["access_token"],
            'refresh_token': auth_info["refresh_token"],
            'token_type': 'Bearer',
            'expires_in': expires_in
        }

        return OAuth2Session(client_id, token=token, auto_refresh_kwargs=extra,
                             auto_refresh_url=cls.TOKEN_URL, token_updater=token_updater)

    def _get_profile(self) -> dict:
        try:
            response = self.oauth_session.get(self.PROFILE_ENDPOINT)
        except HTTPError:
            raise APIException()
        return response.json()
