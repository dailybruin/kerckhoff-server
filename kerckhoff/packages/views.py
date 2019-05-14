from rest_framework import mixins, viewsets, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from rest_framework.response import Response

from kerckhoff.taskqueues.tasks import sync_gdrive_task

from .models import PackageSet, Package
from .serializers import (
    PackageSetSerializer,
    PackageSerializer,
    RetrievePackageSerializer,
)


slug_with_dots = "[-a-zA-Z0-9_.&]+"


class PackageSetViewSet(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    """
    Updates and retrieves individual Package Sets
    """

    queryset = PackageSet.objects.all()
    serializer_class = PackageSetSerializer
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
        return Response({'id': task.id})


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

    def retrieve(self, request, **kwargs):
        package = self.get_object()
        version_number = request.query_params.get("version", 1)
        serializer = RetrievePackageSerializer(
            package, context={"version_number": version_number}
        )
        return Response(serializer.data)

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
