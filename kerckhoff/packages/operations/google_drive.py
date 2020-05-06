from django.contrib.auth import get_user_model
from requests_oauthlib import OAuth2Session
from requests.exceptions import RequestException
from requests import Response
from typing import Tuple, Optional, List
from enum import Enum
import logging

from kerckhoff.packages.operations.exceptions import OperationFailed
from kerckhoff.packages.operations.models import GoogleDriveTextFile, GoogleDriveFile
from kerckhoff.users.auth.google import GoogleOAuthStrategy

from kerckhoff.users.models import User as AppUser

logger = logging.getLogger(__name__)

User: AppUser = get_user_model()


class GoogleDriveOperations:
    oauth_session: OAuth2Session

    _GOOGLE_API_PREFIX = "https://www.googleapis.com/drive"
    _GOOGLE_DOCS_MIMETYPE = "application/vnd.google-apps.document"
    _GOOGLE_FOLDERS_MIMETYPE = "application/vnd.google-apps.folder"

    class FilterMethod(Enum):
        EXTENSION = 1
        DOCUMENT = 2
        FOLDER = 3
        IMAGES = 4

    def __init__(self, user: User):
        self.oauth_session = GoogleOAuthStrategy.create_oauth2_session(user)

    @classmethod
    def filter_items(
        cls, items: list, type: FilterMethod, extensions: Tuple[str, ...] = ("",)
    ):
        if type == cls.FilterMethod.DOCUMENT:
            return [i for i in items if i["mimeType"] == cls._GOOGLE_DOCS_MIMETYPE]
        elif type == cls.FilterMethod.EXTENSION:
            return [i for i in items if i["title"].lower().endswith(extensions)]
        elif type == cls.FilterMethod.FOLDER:
            return [i for i in items if i["mimeType"] == cls._GOOGLE_FOLDERS_MIMETYPE]
        elif type == cls.FilterMethod.IMAGES:
            return [i for i in items if i["mimeType"].startswith("image/")]

    def list_folder(
        self, gdrive_folder_id: str, all: bool = True, page_token: str = None
    ) -> Tuple[list, str]:
        """List the items in a Google Drive Folder, specified by the folder id.

        Returns the list of items, and the page token for the next page
        """

        payload = {
            "q": f"'{gdrive_folder_id}' in parents and trashed=false",
            "orderBy": "title",
            "maxResults": 100,
        }

        if page_token:
            payload["pageToken"] = page_token

        results = []
        next_url: str = None
        next_token: str = None

        while True:
            try:
                if not next_url:
                    response = self.oauth_session.get(
                        self._GOOGLE_API_PREFIX + "/v2/files", params=payload
                    )
                else:
                    response = self.oauth_session.get(next_url)
                response.raise_for_status()
                res_json = response.json()

                results += res_json["items"]
                next_token = res_json.get("nextPageToken")
                if all and next_token:
                    next_url = res_json["nextLink"]
                else:
                    break

            except RequestException:
                logger.error(
                    f"Failed to list folder for id:{gdrive_folder_id} {response.json()}"
                )
                raise OperationFailed(response.json())

        return results, next_token

    def download_item(self, gdrive_item: GoogleDriveFile) -> Response:
        """Downloads the contents of the provided Google Drive file, returns a Requests response"""
        logger.debug(f"Downloading {gdrive_item.title}")
        res = self.oauth_session.get(gdrive_item.get_download_link(), stream=True)
        return res

    def _fetch_item_metadata(self, gdrive_id: str) -> Optional[dict]:
        """Calls the API to get a single item
        """
        res = self.oauth_session.get(self._GOOGLE_API_PREFIX + f"/v2/files/{gdrive_id}")
        if res.ok:
            return res.json()
        else:
            logger.error(
                f"Failed to fetch item from GDrive. Code:{res.status_code} Response:{res.json()}"
            )
            return None
