from django.test import TestCase
from django.test import Client
from django.urls import reverse
from django.forms.models import model_to_dict
from django.contrib.auth.hashers import check_password
from nose.tools import ok_, eq_
from rest_framework.test import APITestCase
from rest_framework import status
from faker import Faker
from .factories import UserFactory
from ..models import *

from threading import Thread
import re

from bs4 import BeautifulSoup

from kerckhoff.packages.operations.wordpress_utils import WordpressIntegration
from kerckhoff.packages.exceptions import PublishError
from kerckhoff.packages.test.wordpress_test_data import (
    authors,
    categories
)


class BasicFunctionalityTest(APITestCase):

    def setUp(self):
        print("setting up")
        self.user = UserFactory()
        #  self.user.userprofile.auth_data = not too sure
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.user.auth_token}')
        pset = PackageSet.objects.create(slug="test", created_by=self.user)
        package = Package.objects.create(slug="wordpress.test_package", package_set=pset, created_by=self.user)

    def testfirst(self):
        response = self.client.post("/api/v1/package-sets/test/packages/wordpress.test_package/preview/")
        print(response.json())
        response = self.client.post("/api/v1/package-sets/test/packages/wordpress.test_package/snapshot/",{
            "title":"test",
            "version_description":"a",
            "included_items":[
                "igor-stepanov-o32SNDk8cMA-unsplash.jpg",
                "photo-1503023345310-bd7c1de61c7d.jpeg",
                "the-honest-company--kCEUoJFH7I-unsplash.jpg",
                "data.aml"
            ]
        })
        print(response)
        eq_(True, False);

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
            "coverimg": "test.jpg",
            "excerpt": "this is a test AML",
            "headline": "Test AML",
            "slug": "slug1",
            "covercaption": "this is the caption",
            "categories": "cat1,cat2,cat3"
        }
        for field in data.keys():
            data_copy = data.copy()
            data_copy.pop(field)
            try:
                integration = WordpressIntegration(data_copy, [])
                integration.publish()
            except PublishError as e:
                self.assertEqual(e.detail, f"Missing top-level AML field: \'{field}\'")


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
        Test that WordpressIntegration retrieves category id from API + database correctly

        Multithreading is used to speed up the process, as a request and database query
        is done for every category
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
        return

    def test_article_posting(self):
        return


class HTMLCorrectnessTest(APITestCase):
    integration = WordpressIntegration({}, [])

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
