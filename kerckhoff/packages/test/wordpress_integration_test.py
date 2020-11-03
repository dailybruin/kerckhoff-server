from os import getenv
from threading import Thread
import re

from django.test import TestCase
from bs4 import BeautifulSoup
import requests

from ..operations.wordpress_utils import WordpressIntegration
from ..exceptions import PublishError
from ..models import *
from .wordpress_test_data import (
    authors,
    categories,
    test_article_aml,
    test_article_images
)

# pp = pprint.PrettyPrinter(indent=2) #for debugging

class BasicFunctionalityTest(TestCase):

    #TODO: test uncategorized

    def setUp(self):
        # Wordpress Basic Auth: Auth data is stored in /.env
        user = getenv("WORDPRESS_API_USER")
        pw = getenv("WORDPRESS_API_PW")
        auth_string = f"{user}:{pw}"
        auth_data = auth_string.encode("utf-8")
        self.url = getenv("WORDPRESS_API_URL")
        self.basic_auth_header = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': "Basic " + b64encode(auth_data).decode("utf-8")
        }

    def test_missing_AML_fields(self):
        """
        Test that missing AML field throws appropriate PublishError
        """
        data = {
            "author": "john d",
            "content": [
                {
                    "value": "hi",
                    "type": "text"
                }
            ],
            "excerpt": "this is a test AML",
            "headline": "Test AML",
            "slug": "slug1",
            "categories": "cat1,cat2,cat3"
        }
        for field in data.keys():
            data_copy = data.copy()
            data_copy.pop(field)
            with self.assertRaises(PublishError) as context:
                integration = WordpressIntegration(data_copy, [])
                integration.publish()
                self.assertEqual(context.exception.detail, f"Missing top-level AML field: \'{field}\'")

    def test_wp_author_ids(self):
        """
        Test that WordpressIntegration retrieves author id from API + database correctly

        Multithreading is used to speed up the process, as a request and database query
        is done for every author
        """
        def compare_author_ids(author:dict):
            integration = WordpressIntegration({}, [])
            wp_id = integration.get_author_id(author["name"])
            if "extra_ids" in author.keys():
                #Author has more than 1 id
                if wp_id != author["id"]:
                    if wp_id not in author["extra_ids"]:
                        print(f'Wrong id for author {author["name"]}')
                    self.assertTrue(wp_id in author["extra_ids"])
            else:
                if wp_id != author["id"]:
                    print(f'Wrong id for author {author["name"]}')
                self.assertEqual(wp_id, author["id"])

        for i in range(2):
            # Run twice: once for retrieval from API, once for retrieval from db
            threads = []
            for author in authors:
                t = ErrThread(target=compare_author_ids, args=(author,))
                t.start()
                threads.append(t)

            for t in threads:
                t.join()
                if t.err:
                    # Raise stored exception in ErrThread
                    raise t.err

    def test_wp_category_ids(self):
        """
        Same as test_wp_author_ids, but for categories instead
        """
        def compare_category_ids(category:dict):
            integration = WordpressIntegration({}, [])
            wp_id = integration.get_category_id(category["slug"])
            if wp_id != category["id"]:
                print(f'Wrong id for category {category["name"]}')
            self.assertEqual(wp_id, category["id"])

        for i in range(2):
            # Run twice: once for retrieval from API, once for retrieval from db
            threads = []
            for category in categories:
                t = ErrThread(target=compare_category_ids, args=(category,))
                t.start()
                threads.append(t)

            for t in threads:
                t.join()
                if t.err:
                    # Raise stored exception in ErrThread
                    raise t.err

    def test_image_uploading(self):
        """
        Test uploading of image from S3 to Wordpress using Wordpress REST API

        For testing purposes, we don't necessarily need to use S3 links
        """

        def upload_and_delete_image(image_url):
            integration = WordpressIntegration({}, [])
            image_data = integration.upload_img_from_s3(image_url, "test.jpg")
            # Delete immediately
            api_url = getenv("WORDPRESS_API_URL")
            res = requests.delete(f'{api_url}/wp-json/wp/v2/media/{image_data["id"]}?force=true',
                                  headers=self.basic_auth_header)

        # Change these image urls if any of them go down
        image_urls = [
            "https://images.unsplash.com/photo-1596273249616-2b7ff039de07?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=633&q=80",
            "https://images.unsplash.com/photo-1596178836784-268ac447e3e2?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=1302&q=80",
            "https://images.unsplash.com/photo-1596162954151-cdcb4c0f70a8?ixlib=rb-1.2.1&ixid=eyJhcHBfaWQiOjEyMDd9&auto=format&fit=crop&w=634&q=80"
        ]

        threads = []
        for url in image_urls:
            t = ErrThread(target=upload_and_delete_image, args=(url,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()
            # t.err will be a PublishError
            if t.err:
                self.fail(t.err)

    def test_article_posting(self):
        """
        Test posting of article to Wordpress
        """

        #TODO: additional checks for article format after upload using BS4

        integration = WordpressIntegration(test_article_aml, test_article_images)

        try:
            # Publish Test Article
            result = integration.publish()
            url = result["response"]["link"]

            # Uncategorized category id test (important)
            self.assertTrue(1 in result["response"]["categories"]) # 1 is the uncategorized id

            # Check published article in correct format
            self.check_article_html(url, test_article_aml)
        except PublishError as e:
            self.fail(e.detail)
        finally:
            # Delete post
            api_url = getenv("WORDPRESS_API_URL")
            res = requests.delete(f'{api_url}/wp-json/wp/v2/posts/{result["id"]}?force=true',
                                      headers=self.basic_auth_header)
            # Delete images
            img_data = result["img_data"]
            for img in img_data:
                res = requests.delete(f'{api_url}/wp-json/wp/v2/media/{img_data[img]["id"]}?force=true',
                                      headers=self.basic_auth_header)

    def check_article_html(self, url, article_aml):
        """
        Helper function to check HTML of published article against its AML
        """
        soup = BeautifulSoup(requests.get(url).content, "html.parser")
        paragraphs = map(lambda el: el.get_text(strip=True), soup.find_all("p"))
        content = article_aml["content"]
        for item in content:
            if item["type"] == "text":
                self.assertTrue(item["value"].strip() in paragraphs)


class ErrThread(Thread):
    """
    Special thread that allows assertions to be used in a multithreading context

    Instead of allowing AssertionErrors to be raised while in individual threads,
    it saves them so that they can be raised later in the main thread. Without this,
    the test case will always pass, as the testing module will never see the AssertionErrors.
    """
    def run(self):
        try:
            Thread.run(self)
        except Exception as e:
            self.err = e
            pass
        else:
            self.err = None


class HTMLCorrectnessTest(TestCase):

    def setUp(self):
        self.integration = WordpressIntegration({}, [])

    def test_invalid_content_type(self):
        content = [
            {
                "type": "random_type_name",
                "value": "first paragraph"
            }
        ]
        with self.assertRaises(PublishError) as context:
            html = self.integration.get_html_string(content)
        self.assertTrue(f"Invalid content item type {content[0]['type']}" == str(context.exception))

    def test_item_missing_attributes(self):
        content = [
            {
                "typ": "random_type_name",
                "value": "first paragraph"
            }
        ]
        with self.assertRaises(PublishError) as context:
            html = self.integration.get_html_string(content)
        self.assertTrue(f"Invalid AML item {content[0]}" == str(context.exception))

    def test_paragraph(self):
        content = [
            {
                "type": "text",
                "value": "first paragraph"
            },
            {
                "type": "text",
                "value": "second paragraph"
            },
            {
                "type": "text",
                "value": "third paragraph"
            }
        ]
        original_content = list(map(lambda element : element["value"], content))

        html = self.integration.get_html_string(content)
        soup = BeautifulSoup(html, "html.parser")
        parsed_content = list(map(lambda paragraph : paragraph.string, soup.find_all("p")))

        self.assertEqual(original_content, parsed_content)

    def test_aside(self):
        aside_text = "this is an aside"
        content = [
            {
                "type": "text",
                "value": "first paragraph"
            },
            {
                "type": "aside",
                "value": aside_text
            },
            {
                "type": "text",
                "value": "second paragraph"
            }
        ]
        html = self.integration.get_html_string(content)
        soup = BeautifulSoup(html, "html.parser")
        aside = soup.find("aside")
        self.assertEqual(aside_text, aside.string)

    def test_embed_link(self):
        instagram_link = "https://www.instagram.com/p/CDCSn7Qs-Hn/?utm_source=ig_web_copy_link"
        twitter_link = "https://twitter.com/Twitter/status/1283504558753415168"
        paragraph_text = "first_paragraph"
        content = [
            {
                "type": "text",
                "value": paragraph_text
            },
            {
                "type": "embed_instagram",
                "value": instagram_link
            },
            {
                "type": "embed_twitter",
                "value": twitter_link
            }
        ]
        html = self.integration.get_html_string(content)
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(soup.find("p").string, paragraph_text)

        # Embed links are not in html elements because Wordpress
        # will automatically embed them
        self.assertTrue(f"\n{instagram_link}\n\n{twitter_link}\n" in html)

    def test_image(self):
        img_file = "test.jpg"
        img_caption = "this is the image caption"
        img_html = f'<img src="{img_file}">'
        self.integration.img_data = {
            "test.jpg": {
                "html": img_html,
                "id": -1 # This has to be an invalid ID so it doesn't actually upload to wordpress
            }
        }
        content = [
            {
                "type": "text",
                "value": "Image test"
            },
            {
                "type": "image",
                "value": {
                    "src": img_file,
                    "caption": img_caption
                }
            }
        ]
        html = self.integration.get_html_string(content)
        soup = BeautifulSoup(html, "html.parser")
        paragraph = soup.find("p")
        self.assertEqual(paragraph.string, "Image test")

        # For wordpress templating, image with caption should be in the format
        # [caption (attributes...) ]<img src="...">caption_text[/caption]
        html_without_p = html.replace(str(paragraph), "")
        pattern = re.compile(f"\[caption.*\]{img_html}{img_caption}\[\/caption\]")
        match = pattern.search(html)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(0), html_without_p)

    def test_related_link(self):
        #Change the link if the article gets taken down
        headline = "UC patient care and service workers ratify wage increases, more in new contract"
        url = "https://dailybruin.com/2020/02/09/uc-patient-care-and-service-workers-ratify-wage-increases-more-in-new-contract"
        content = [
            {
                "type": "text",
                "value": "paragraph 1"
            },
            {
                "type": "related_link",
                "value": url
            },
            {
                "type": "text",
                "value": "paragraph 2"
            }
        ]
        html = self.integration.get_html_string(content)
        soup = BeautifulSoup(html, "html.parser")
        paragraphs = soup.find_all("p")
        related_link = paragraphs[1]
        bolded_text = related_link.find_all("b")

        # Wrapping text
        self.assertEqual(bolded_text[0].string, "[Related link:")
        self.assertEqual(bolded_text[2].string, "]")

        # <a> element
        anchor = related_link.find("a")
        self.assertEqual(anchor["href"], url) #Link
        self.assertEqual(anchor.find("b").string, headline) #Headline

