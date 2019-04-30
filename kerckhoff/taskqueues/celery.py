import os
import configurations
from celery import Celery
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kerckhoff.config')
os.environ.setdefault('DJANGO_CONFIGURATION', 'Local')

configurations.setup()

app = Celery('kerckhoff')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
