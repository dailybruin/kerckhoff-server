from rest_framework.exceptions import APIException


class GoogleDriveNotConfiguredException(APIException):
    status_code = 400

    def __init__(self, package):
        self.detail = f"Google Drive is not yet configured for {package.slug}."

class PublishError(APIException):
    def __init__(self, message, status):
       self.detail = message
       self.status_code = status
