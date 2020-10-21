import tempfile
import pprint
from os import getenv
from base64 import b64encode
from html import unescape

import requests
import logging
import bleach
from dominate.tags import *
from bs4 import BeautifulSoup

from django.utils.html import escape
from django.core.exceptions import (
    MultipleObjectsReturned,
    ObjectDoesNotExist,
)
from kerckhoff.packages.exceptions import (
    PublishError
)
import kerckhoff.packages.models as models

logger = logging.getLogger(__name__)
pp = pprint.PrettyPrinter(indent=2) #for debugging


"""
Helper class for handling Wordpress REST API publishing

Constructor Params schema:
    aml_data
    {
        (REQUIRED FIELDS)
        author: str
        content: [...] (AML content)
        coverimg: str (file name)
        excerpt: str
        headline: str
        slug: str
    },

    img_urls
    {
        <file name> : <s3 url>,
    }

"""
class WordpressIntegration:
    def __init__(self, aml_data:dict, img_urls:dict):
        if aml_data == None:
            raise PublishError("No AML file specified")
        self.aml_data = aml_data
        self.img_urls = img_urls

        #Basic Auth: Auth data is stored in /.env
        user = getenv("WORDPRESS_API_USER")
        pw = getenv("WORDPRESS_API_PW")
        auth_string = f"{user}:{pw}"
        auth_data = auth_string.encode("utf-8")
        self.url = getenv("WORDPRESS_API_URL")
        self.basic_auth_header = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': "Basic " + b64encode(auth_data).decode("utf-8")
        }


    def publish(self) -> dict:
        """
        Publishes article data to WordPress using REST API
            - Sends article data as a HTML string
            - Authentication using WordPress Application Passwords

        Return format:
        {
            id: id of post
            img_data : {...self.img_data}
        }
        The return data is currently only being used to delete
        the post in tests
        """

        print("Parsing top level data...")
        #AML metadata (top level tags)
        try:
            author = self.aml_data["author"]
            headline = self.aml_data["headline"]
            slug = self.aml_data["slug"]
            excerpt = self.aml_data["excerpt"]
            content = self.aml_data["content"]
            categories = self.aml_data["categories"].split(",")
        except KeyError as err:
            raise PublishError(f"Missing top-level AML field: {err}")

        print("Retrieving IDs...")
        #Convert metadata to Wordpress UUIDs
        author_id = self.get_author_id(author)
        category_id_string = ""
        for i, category in enumerate(categories):
            category = category.strip()
            category_id_string += str(self.get_category_id(category))
            if i < len(categories) - 1:
                category_id_string += ","

        print("Uploading images...")
        #Upload imgs to Wordpress + retrieve Wordpress metadata
        self.img_data = {}
        for img in self.img_urls:
            self.img_data[img] = self.upload_img_from_s3(self.img_urls[img], img)

        # Set coverimg if in article
        if "coverimg" in self.aml_data and self.aml_data["coverimg"] != "":
            try:
                coverimg_id = str(self.img_data[self.aml_data["coverimg"]]["id"])
                covercaption = self.aml_data["covercaption"]
            except KeyError as err:
                raise PublishError(f"Missing cover image file: {err}")
        else:
            coverimg_id = ""

        #Content generation
        content_string = self.get_html_string(content)

        data = {
            "title": headline,
            "slug": slug,
            "status": 'publish',
            "content": content_string,
            "author": str(author_id),
            "excerpt": excerpt,
            "featured_media": coverimg_id if coverimg_id != "" else None,
            "categories": category_id_string,
        }

        print("Publishing...")
        #REST API post
        #TODO: Improve this error handling (feedback to frontend)
        if coverimg_id != "":
            # Wordpress caption uploading:
            requests.post(
                f"{self.url}/wp-json/wp/v2/media/{coverimg_id}",
                headers=self.basic_auth_header,
                data={"caption": covercaption}
            )

        response = requests.post(  #Main article uploading
            f"{self.url}/wp-json/wp/v2/posts",
            headers=self.basic_auth_header,
            data=data
        )
        if not response.ok:
            print(response)
            raise PublishError("Failed to send data to WordPress")
        logger.info("Publish Response: ", response)

        return {
            "id": response.json()["id"],
            "img_data": self.img_data
        }


    def get_html_string(self, content:list) -> str:
        """
        Converts AML data to HTML string using Dominate
        """
        #TODO: No support for related articles yet
        #TODO: Author information at the bottom
        html_content = []
        for item in content:
            try:
                if item["type"] == "text":
                    html_content.append(str(p(unescape(item["value"]))))
                elif item["type"] == "aside":
                    html_content.append(str(aside(unescape(item["value"]))))
                elif item["type"] == "embed_instagram" or item["type"] == "embed_twitter":
                    #Strip all tags and escape to get the embed link
                    text = bleach.clean(item["value"], strip=True, tags=[])
                    html_content.append("\n" + escape(text) + "\n")
                elif item["type"] == "image":
                    file_name = item["value"]["src"]
                    caption = item["value"]["caption"]
                    html = self.img_data[file_name]["html"]
                    html_content.append(f"[caption align=\"aligncenter\" width=\"207\"]{html}{caption}[/caption]")
                    try:
                        requests.post(  #Wordpress caption uploading
                                f"{self.url}/wp-json/wp/v2/media/{self.img_data[file_name]['id']}",
                            headers=self.basic_auth_header,
                            data={"caption": caption}
                        )
                    except KeyError as err:
                        raise PublishError(f"Missing image file: {err}")
                elif item["type"] == "related_link":
                    #Get headline from url
                    url = bleach.clean(item["value"], strip=True, tags=[])
                    res = requests.get(url)
                    soup = BeautifulSoup(res.content, "html.parser")
                    headline = soup.find("h1").get_text()
                    #Generate html
                    link = a(href=url)
                    link.add(b(headline))
                    paragraph = p()
                    for item in [b("[Related link:"), link, b("]")]:
                        paragraph.add(item)
                    unescaped = str(unescape(paragraph)).replace("\n", "")  #Newlines mess up the html
                    html_content.append(unescaped)
                else:
                    raise PublishError(f"Invalid content item type {item['type']}")
            except KeyError as err:
                raise PublishError(f"Invalid AML item {item}")
        return "".join(html_content)


    def get_author_id(self, author_name) -> int:
        return self.get_id("author", author_name)

    def get_category_id(self, cat_name) -> int:
        return self.get_id("category", cat_name)


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
                if wp_res.ok:
                    res_json = wp_res.json()
                    logger.info(f"Uploaded image to wordpress with result {wp_res}")
                    print(f"{file_name} uploaded")
                    return {
                        "id": res_json["id"],
                        "html": res_json["description"]["rendered"],
                        "caption": res_json["caption"]["raw"]
                    }
                else:
                    err_message = f"Unable to upload image {file_name} to WordPress"
                    logger.info(err_message)
                    logger.info(f"{wp_res}")
                    raise PublishError(err_message)
                f.flush()
        else:
            raise PublishError(f"Unable to retrieve image {file_name} from S3")


    def get_id(self, model:str, object_name:str) -> int:
        """
        "Template function" - runs with multiple model types

        Retrieves id of the specifed model stored in database.
        If not in database, retrieve from API and store.
        """
        #Type specification
        if model == "author":
            WpModel = models.WordpressAuthor
            api_end = f"{self.url}/wp-json/wp/v2/users?search={object_name}"
        elif model == "category":
            WpModel = models.WordpressCategory
            api_end = f"{self.url}/wp-json/wp/v2/categories?slug={object_name}"

        if object_name == "":
            raise PublishError(f"No {model} name specified")

        try:
            entry = WpModel.objects.get(name__iexact=object_name)
        except MultipleObjectsReturned as err:
            raise PublishError(f"Multiple {model}s with {object_name}")
        except ObjectDoesNotExist:
            #Retrieve from API
            req_json = requests.get(f"{api_end}").json()
            try:
                obj = req_json[0]
            except IndexError:
                raise PublishError(f"No {model} named {object_name}")

            try:
                #Try one more time to see if object exists in database
                existing_obj = WpModel.objects.get(wp_id=obj["id"])
                entry = existing_obj
            except ObjectDoesNotExist:
                if model == "author":
                    entry = WpModel(wp_id=obj["id"], name=obj["name"])
                elif model == "category":
                    entry = WpModel(wp_id=obj["id"], name=obj["slug"])
                entry.save()

        return entry.wp_id
