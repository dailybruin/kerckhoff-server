from celery.result import AsyncResult


def query_result(task_id):
    return AsyncResult(id=task_id).state
