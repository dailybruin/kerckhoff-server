from celery import shared_task
from celery.result import AsyncResult


@shared_task
def sync_gdrive():
    pass

def query_result(task_id):
    return AsyncResult(id=task_id).state
