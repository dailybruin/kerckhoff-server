from celery import shared_task

from .serializers import PackageSerializer
from .models import PackageSet


@shared_task
def sync_gdrive_task(package_set_slug):
    package_set = PackageSet.objects.get(slug=package_set_slug)
    packages = package_set.get_packages_from_gdrive()
    serializer = PackageSerializer(packages, many=True)
    response = {"created": serializer.data, "total": len(packages)}
    return response
