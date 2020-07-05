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


class WordpressIntegrationTest(APITestCase):

	def setUp(self):
		print("setting up")
		self.user = UserFactory()
		#  self.user.userprofile.auth_data = not too sure
		self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.user.auth_token}')
		pset = PackageSet.objects.create(slug="test", created_by=self.user)	
		package = Package.objects.create(slug="wordpress.test_package", package_set=pset, created_by=self.user)	

	def testfirst(self):
		
		print("here")
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