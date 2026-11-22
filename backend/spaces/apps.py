from django.apps import AppConfig


class SpacesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'spaces'
    verbose_name = 'Przestrzenie'

    def ready(self):
        from . import signals  # noqa: F401
