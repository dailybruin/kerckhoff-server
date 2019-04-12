from rest_framework import mixins, viewsets, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.serializers import Serializer
from rest_framework.response import Response

from .models import PackageSet, Package
from .serializers import PackageSetSerializer, PackageSerializer


slug_with_dots = "[-a-zA-Z0-9_.]+"


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
        package_set = self.get_object()
        new_packages = package_set.get_new_packages_from_gdrive()
        serializer = PackageSerializer(new_packages, many=True)
        response = {"created": serializer.data, "total": len(new_packages)}
        return Response(response)


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
