from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token

from .auth.google import GoogleOAuthStrategy
from .auth.strategy import OAuthStrategy
from .models import User
from .permissions import IsUserOrReadOnly
from .serializers import CreateUserSerializer, UserSerializer
from .auth.exceptions import NoRefreshTokenException

class UserViewSet(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    """
    Updates and retrieves user accounts
    """

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (IsUserOrReadOnly,)


class UserCreateViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    Creates user accounts
    """

    queryset = User.objects.all()
    serializer_class = CreateUserSerializer
    permission_classes = (AllowAny,)


class AbstractOAuthView(APIView):
    """
    Handles logins using any OAuth flow
    """

    permission_classes = (AllowAny,)
    authentication_classes = ()
    oauth_strategy: OAuthStrategy

    def get(self, request: Request):
        code = request.query_params.get("code")
        if not code:
            # Requesting the Auth URI
            redirect_url = self.oauth_strategy.get_authorization_url()
            return Response({"redirect_url": redirect_url})

        # Redirected from the provider
        try:
            user, did_register = self.oauth_strategy.login(code)
            token = Token.objects.get_or_create(user=user)[0]
            user_serializer = UserSerializer(user)
            return Response({
                "token": token.key,
                "user": user_serializer.data,
                "is_new": did_register
            })

        except NoRefreshTokenException:
            # No refresh token was found for a new user, force the authorization flow
            forced_approval_args = dict(prompt="consent", **self.oauth_strategy.additional_args)

            redirect_url = self.oauth_strategy.get_authorization_url(forced_approval_args)
            return Response({"redirect_url": redirect_url})


class GoogleOAuthView(AbstractOAuthView):
    """
    Handles logins using the Google OAuth flow
    """

    oauth_strategy = GoogleOAuthStrategy()
