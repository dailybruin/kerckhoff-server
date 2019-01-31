from abc import ABC

from requests_oauthlib import OAuth2Session

from ..models import User


class OAuthStrategy(ABC):
    """
    An abstract base strategy for all authentication methods
    """

    BASE_URL: str
    TOKEN_URL: str
    REDIRECT_PATH: str

    oauth_session: OAuth2Session
    additional_args: dict

    def login(self, code: str, **kwargs) -> [User, bool]:
        raise NotImplementedError()

    def register(self, profile: dict, **kwargs):
        raise NotImplementedError()

    def get_authorization_url(self, args: dict = None) -> str:
        """Get the user authorization URL for the OAuth flow

        Returns:
            str: The authorization url
        """

        authorization_url, _ = self.oauth_session.authorization_url(
            self.BASE_URL, **(self.additional_args if not args else args)
        )
        return authorization_url

    def get_access_token(self, code: str, client_secret: str) -> dict:
        """Exchanges the Authorization code for an access token
        """
        return self.oauth_session.fetch_token(
            self.TOKEN_URL, client_secret=client_secret, code=code
        )
