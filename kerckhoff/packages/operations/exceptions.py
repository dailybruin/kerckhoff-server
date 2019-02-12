from rest_framework.exceptions import APIException

class OperationFailed(APIException):
    status_code = 500
    default_detail = "An operation has failed."

    def __init__(self, responseDict: dict):
        if cause:
            self.detail = f"An operation has failed, Cause: {str(responseDict)}"
