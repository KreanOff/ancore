"""Delete shared legacy/canonical task files only after their final reference."""
from django.apps import apps
from django.db import transaction


def delete_after_commit(instance, using, *, comment=False):
    if not instance.file:
        return
    storage, name = instance.file.storage, instance.file.name
    models = [('tasks', 'TaskCommentImage'), ('kanban', 'KanbanCommentImage')] if comment else [('tasks', 'TaskAttachment'), ('kanban', 'KanbanAttachment')]

    models.append(('spaces', 'SpaceTaskFile'))

    def cleanup():
        if not any(apps.get_model(app, model).objects.using(using).filter(file=name).exists() for app, model in models):
            storage.delete(name)

    transaction.on_commit(cleanup, using=using, robust=True)
