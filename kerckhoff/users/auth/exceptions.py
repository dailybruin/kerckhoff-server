from rest_framework.exceptions import APIException


class InvalidCodeException(APIException):
    status_code = 500
    default_detail = "The OAuth process failed unexpectedly."


class NoRefreshTokenException(Exception):
    pass
