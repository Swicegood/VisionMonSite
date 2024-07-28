from django.apps import AppConfig
from django.conf import settings
import os

class MonitorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'monitor'
    path = os.path.join(settings.BASE_DIR, 'monitor')