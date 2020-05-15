from rest_framework.exceptions import APIException


class GoogleDriveNotConfiguredException(APIException):
    status_code = 400

    def __init__(self, package):
        self.detail = f"Google Drive is not yet configured for {package.slug}."

class PublishError(APIException):
    status_code = 400

    def __init__(self, message):
       self.detail = message
