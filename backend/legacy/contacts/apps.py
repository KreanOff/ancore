from django.apps import AppConfig


class LegacyContactsConfig(AppConfig):
    """Retain migration dependencies and old company relations without a module UI."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'legacy.contacts'
    label = 'contacts'
    verbose_name = 'Dane historyczne'
