from dominate.tags import *
from html import unescape
from os import getenv
from base64 import b64encode

import requests
import tempfile
import logging
import pprint

logger = logging.getLogger(__name__)
pp = pprint.PrettyPrinter(indent=2) #for debugging

class WordpressIntegration:
    """
    Helper class for handling Wordpress REST API publishing

    Params schema:
        aml_data
        {
            author: str
            content: {...} (AML content)
            coverimg: str (file name)
            excerpt: str
            headline: str
            slug: str
        },

        img_urls
        {
            <file name> : <s3 url>,
            ...
        }
    """
    def __init__(self, aml_data:dict, img_urls:dict):
        self.aml_data = aml_data
        self.img_urls = img_urls

        #Basic Auth: Auth data is stored in /.env
        self.url = getenv("WORDPRESS_API_URL")
        user = getenv("WORDPRESS_API_USER")
        pw = getenv("WORDPRESS_API_PW")
        auth_string = f"{user}:{pw}"
        auth_data = auth_string.encode("utf-8")
        self.basic_auth_header = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': "Basic " + b64encode(auth_data).decode("utf-8")
        }

    def publish(self):
        """
        Publishes article data to WordPress using REST API
            - Sends article data as a HTML string
            - Authentication using WordPress Application Passwords
        """
        #Upload imgs to Wordpress + retrieve Wordpress metadata
        self.img_data = {}
        for img in self.img_urls:
            self.img_data[img] = self.upload_img_from_s3(self.img_urls[img], img)
        coverimg = self.aml_data["coverimg"]

        #Content generation
        #TODO: No support for in-paragraph images + captions yet
        content_string = self.get_html_string()
        author_id = self.get_author_id()
        data = {
            'title': self.aml_data["headline"],
            'slug': self.aml_data["slug"],
            'status': 'publish',
            'content': content_string,
            'author': str(author_id),
            'excerpt': self.aml_data["excerpt"],
            'featured_media': str(self.img_data[coverimg]["id"])
        }

        #REST API post
        try:
            response = requests.post(f"{self.url}/wp-json/wp/v2/posts", headers=self.basic_auth_header, data=data)
        except requests.exceptions.RequestException as err:
            logger.info("Error: " + err)

    def get_html_string(self) -> str:
        """
        Converts AML data to HTML string using Dominate
        """
        content_string = ""
        for item in self.aml_data["content"]:
            if(item["type"] == "p"):
                content_string += str(p(unescape(item["value"])))
            elif(item["type"] == "aside"):
                content_string += str(aside(unescape(item["value"])))
            elif(item["type"] == "embed_instagram"):
                content_string += "\n" + item["value"] + "\n"
            elif(item["type"] == "embed_twitter"):
                content_string += "\n" + item["value"] + "\n"
        return content_string

    def get_author_id(self) -> int:
        """
        Returns author id in Wordpress based on name
            -REST API get
        """
        author = self.aml_data["author"]
        author_json = requests.get(f"{self.url}/wp-json/wp/v2/users?search={author}").json()
        author_id = author_json[0]["id"]
        return author_id

    def upload_img_from_s3(self, img_url:str, file_name:str) -> dict:
        """
        Uploads Images from S3 to Wordpress media endpoint
        Params : img_url - image url in S3
                 file_name - name of file to be created in Wordpress (up to you)
        Return format:
        {
            id: ID of image in Wordpress
            html: HTML to be embedded
            caption: ...
        }
        """
        res = requests.get(img_url, stream=True)
        ext = file_name[-3:-1] #last 3 chars of string
        if res.ok:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
                image_path = f.name
                for chunk in res.iter_content(chunk_size=1000):
                    f.write(chunk)
                headers = self.basic_auth_header
                headers["Content-Disposition"] = f"form-data; filename={file_name}"
                data = open(image_path, 'rb').read()
                wp_res = requests.post(f"{self.url}/wp-json/wp/v2/media", headers=headers, data=data)
                res_json = wp_res.json()
                if wp_res.ok:
                    logger.info(f"Uploaded image to wordpress with result {wp_res}")
                    return {
                        "id": res_json["id"],
                        "html": res_json["description"]["rendered"],
                        "caption": res_json["caption"]["rendered"]
                    }
                else:
                    logger.info("Unable to upload image to Wordpress")
                    logger.info(f"{wp_res}")
                f.flush()
        else:
            raise FileNotFoundError
