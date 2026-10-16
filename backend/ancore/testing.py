"""Discover backend tests while keeping their existing Python package names."""

from django.conf import settings
from django.test.runner import DiscoverRunner


class BackendDiscoverRunner(DiscoverRunner):
    def build_suite(self, test_labels=None, **kwargs):
        # The repository root also contains frontend and deployment sources.
        # Django's default discovery would skip the non-package backend directory.
        return super().build_suite(test_labels or [str(settings.BACKEND_DIR)], **kwargs)
