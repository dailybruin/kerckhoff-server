from rest_framework.exceptions import APIException

class OperationFailed(APIException):
    status_code = 500
    default_detail = "An operation has failed."

    def __init__(self, responseDict: dict):
        #if cause: # commented out cause because it seems that it is causing an error
        self.detail = f"An operation has failed, Cause: {str(responseDict)}"

class GoogleDriveFileNotFound(APIException):
    status_code = 400
    default_detail = f"Google Drive folder not found, URL may be invalid."

    def __init__(self, responseDict: dict):
        #if cause: # commented out cause because it seems that it is causing an error
        self.detail = f"Google Drive folder not found, URL may be invalid."
