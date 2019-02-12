from rest_framework.exceptions import APIException


class InvalidCodeException(APIException):
    status_code = 500
    default_detail = "The OAuth process failed unexpectedly."


class NoAuthTokenException(APIException):
    status_code = 500
    default_detail = "The user does not have an access token."


class NoRefreshTokenException(Exception):
    pass
