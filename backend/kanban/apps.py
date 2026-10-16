from django.apps import AppConfig


class KanbanConfig(AppConfig):
    name = 'kanban'

    def ready(self):
        from . import sharing_signals  # noqa: F401
