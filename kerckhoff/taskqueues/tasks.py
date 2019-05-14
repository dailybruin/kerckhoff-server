from celery import shared_task
from celery.result import AsyncResult
from kerckhoff.packages.serializers import PackageSerializer
from kerckhoff.packages.models import PackageSet


@shared_task
def sync_gdrive_task(package_set_slug):
    package_set = PackageSet.objects.get(slug=package_set_slug)
    new_packages = package_set.get_new_packages_from_gdrive()
    serializer = PackageSerializer(new_packages, many=True)
    response = {"created": serializer.data, "total": len(new_packages)}
    return response

def query_result(task_id):
    return AsyncResult(id=task_id).state
