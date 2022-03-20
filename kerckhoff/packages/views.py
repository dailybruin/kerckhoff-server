from multiprocessing import log_to_stderr
from typing import List
import os
import json 
from importlib_metadata import packages_distributions
from rest_framework import mixins, viewsets, filters
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from rest_framework.response import Response

from kerckhoff.integrations.serializers import IntegrationSerializer
from .tasks import sync_gdrive_task

from .models import PackageSet, Package, PackageVersion, PackageItem
from .serializers import (
    PackageSetSerializer,
    PackageSerializer,
    RetrievePackageSerializer,
    PackageVersionSerializer,
    CreatePackageVersionSerializer,
    PackageSetDetailedSerializer,
    PackageItemSerializer,
    TestSerializer
)


slug_with_dots = "[-a-zA-Z0-9_.&]+"


class PackageSetViewSet(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    """
    Updates and retrieves individual Package Sets
    """

    queryset = PackageSet.objects.all()
    serializer_class = PackageSetDetailedSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "slug"
    lookup_value_regex = slug_with_dots

    @action(methods=["post"], detail=True, serializer_class=Serializer)
    def sync_gdrive(self, request, slug):
        """
        Imports all packages from the Google Drive folder of a package set
        """
        response = sync_gdrive_task(slug)
        return Response(response)

    @action(methods=["post"], detail=True, serializer_class=Serializer)
    def async_sync_gdrive(self, request, slug):
        task = sync_gdrive_task.delay(slug)
        return Response({"id": task.id})

    @action(methods=["post"], detail=True, serializer_class=IntegrationSerializer)
    def integration(self, request, slug):
        package_set: PackageSet = self.get_object()
        new_integration = IntegrationSerializer(data=request.data)
        new_integration.is_valid(raise_exception=True)
        new_integration.save(created_by=request.user, package_set=package_set)
        return Response(new_integration.data)


class PackageSetCreateAndListViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    """
    Creates and lists new Package Sets
    """

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    queryset = PackageSet.objects.all()
    serializer_class = PackageSetSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "slug"
    lookup_value_regex = slug_with_dots
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ("slug", "last_fetched_date", "created_at", "updated_at")


class PackageViewSet(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    """
    Updates and retrieves packages
    """ 
    def get_queryset(self):
        return Package.objects.filter(package_set__slug=self.kwargs["package_set_slug"])

    serializer_class = PackageSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "slug"
    lookup_value_regex = slug_with_dots

    @action(methods=["post"], detail=True, serializer_class=Serializer)
    def preview(self, request, **kwargs):
        package = self.get_object()
        package.fetch_cache()
        serializer = PackageSerializer(package, many=False)
        return Response(serializer.data)

    @action(methods=["post"], detail=True, serializer_class=Serializer)
    def publish(self, request, **kwargs):
        package = self.get_object()
        package.publish()
        return Response(status=200)

    @action(
        methods=["post"], detail=True, serializer_class=CreatePackageVersionSerializer
    )
    def snapshot(self, request, **kwargs):
        package: Package = self.get_object()
        package_version = CreatePackageVersionSerializer(
            data=request.data, context={"package": package, "user": request.user}
        )
        package_version.is_valid(True)
        updated_pv = package_version.save()
        return Response(PackageVersionSerializer(updated_pv).data)

    @action(methods=["get"], detail=True)
    def versions(self, request, **kwargs):
        package: Package = self.get_object()
        serializer = PackageVersionSerializer(package.get_all_versions(), many=True)
        return Response({"results": serializer.data})

    def retrieve(self, request, **kwargs):
        package = self.get_object()
        version_number = request.query_params.get("version", -1)
        serializer = RetrievePackageSerializer(
            package, context={"version_number": version_number}
        )
        response = serializer.data
        return Response(response)


class PackageCreateAndListViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    """
    Creates and lists packages
    """

    def get_queryset(self):
        return Package.objects.filter(package_set__slug=self.kwargs["package_set_slug"])

    def perform_create(self, serializer):
        package_set = PackageSet.objects.get(slug=self.kwargs["package_set_slug"])
        serializer.save(created_by=self.request.user, package_set=package_set)

    serializer_class = PackageSerializer
    permission_classes = (IsAuthenticated,)
    lookup_field = "slug"
    lookup_value_regex = slug_with_dots
    filter_backends = (filters.OrderingFilter,)
    ordering_fields = ("slug", "last_fetched_date", "created_at", "updated_at")

    

# Public Package View set for External site Kerckhoff API

# mixins.ListModelMixin list out all packages in package set
# mixins.RetrieveModelMixin retrieves specific/individual package within the package set
class PublicPackageViewSet(viewsets.GenericViewSet, mixins.ListModelMixin, mixins.RetrieveModelMixin):
    """
    List and retrieve packages for external site
    """
    
    # Retrieve only the packages from the package set that has the same name/ slug as the defined package set name/slug in the url 
    def get_queryset(self):
        package = Package.objects.get(package_set__slug=self.kwargs["package_set_slug"], slug=self.kwargs["slug"])
        package_items = package.get_version(package.latest_version.id_num).packageitem_set.all() 
        # Get items from latest package
        img_urls = {}
        supported_image_types = [".jpg", ".jpeg", ".png"]
        json_data = {"content_rich":{"data":{}}}
        for file in package_items:
            file_ext = os.path.splitext(file.file_name)[-1]
            if(file.file_name == "data.aml"):
                json_data = file.data
            if(file_ext in supported_image_types):
                 # Don't worry about images for now
                img_urls[file.file_name] = file.data["src_large"]
        aml_data = json_data["content_rich"]["data"]
        print(aml_data)
        aml_data["slug"] = self.kwargs["slug"]

        # package_set = Package.objects.filter(package_set__slug=self.kwargs["package_set_slug"])
        # package_set.update(metadata=img_urls)

        # return package_set
        return Package.objects.filter(package_set__slug=self.kwargs["package_set_slug"])

    
    serializer_class = PackageSerializer
    permission_classes = (IsAuthenticatedOrReadOnly,)
    # set slug as the lookup field so that we look up for packages in the package set with the same slug
    lookup_field = "slug"
    # verifies if the url slug is a valid slug and matches our valid slug format defined at the top of this file
    lookup_value_regex = slug_with_dots

    @action(methods=["get"], detail=True)
    def versions(self, request, **kwargs):
        package: Package = self.get_object()
        serializer = PackageVersionSerializer(package.get_all_versions(), many=True)
        return Response({"results": serializer.data})

    @action(methods=["get"], detail=True, serializer_class=Serializer)
    def preview(self, request, **kwargs):
        package = self.get_object()
        package.fetch_cache()
        serializer = PackageSerializer(package, many=False)
        return Response(serializer.data)

    

    @action(methods=["get"], detail=True, serializer_class=Serializer)
    def details(self, request, **kwargs):
        package = self.get_object()
        package.fetch_cache()
        versionSerializer = PackageVersionSerializer(package.get_version(package.latest_version.id_num))
        version_description = versionSerializer.data["version_description"]
        folder_id = package.metadata["google_drive"]["folder_id"]
        folder_url = package.metadata["google_drive"]["folder_url"]
        
        package_items = package.get_version(package.latest_version.id_num).packageitem_set.all() 

        img_urls = {}
        supported_image_types = [".jpg", ".jpeg", ".png"]
        for file in package_items:
            file_ext = os.path.splitext(file.file_name)[-1]
            if(file.file_name == "article.aml"):
                aml_data = file.data["content_rich"]["data"]
            if(file_ext in supported_image_types):
                 # Don't worry about images for now
                img_urls[file.file_name] = file.data["src_large"]
        
        cached = package.cached
        for item in cached:
            if(item["title"] == "article.aml"):
                cached_article_preview = file.data["content_plain"]["raw"]
        
        return Response({"slug": package.slug, 
        "description": version_description, 
        "folder_id": folder_id,
        "folder_url": folder_url,
        "metadata": {},
        "data": {"article": aml_data},
        "processing": False if package.state == "pub" else True,
        "cached_article_preview": cached_article_preview,
        "last_fetched_date": package.last_fetched_date,
        "package_set": str(package.package_set),
        "latest_version": str(package.latest_version)
        })





