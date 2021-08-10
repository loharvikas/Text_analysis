from django.apps import AppConfig
from .main.load_data import preload_data


class AnalysisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analysis'

    def ready(self):
        preload_data()
