"""Development server with an automatically refreshed application frontend."""
from django.conf import settings
from django.contrib.staticfiles.management.commands.runserver import Command as StaticRunserver

from core.dev_frontend import FrontendBuilder, FrontendBuildError, FrontendBuildHandler


class Command(StaticRunserver):
    frontend_builder = None

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--no-frontend-build', action='store_true',
            help='Wyłącz automatyczny build, np. przy osobnym pnpm dev.',
        )

    def inner_run(self, *args, **options):
        self.frontend_builder = None
        if settings.DEBUG and not options.get('no_frontend_build'):
            self.frontend_builder = FrontendBuilder(settings.BASE_DIR, self.stdout)
            try:
                self.frontend_builder.ensure_current()
            except FrontendBuildError as error:
                # Keep the server available to retry after the source is fixed.
                self.stderr.write(str(error))
        return super().inner_run(*args, **options)

    def get_handler(self, *args, **options):
        handler = super().get_handler(*args, **options)
        if self.frontend_builder is not None:
            return FrontendBuildHandler(handler, self.frontend_builder, settings.STATIC_URL)
        return handler
