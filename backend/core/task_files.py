"""Delete private task files after the transaction and their final reference."""
from django.db import transaction


def delete_after_commit(instance, using):
    if not instance.file:
        return
    storage, name = instance.file.storage, instance.file.name

    def cleanup():
        from spaces.models import SpaceTaskFile
        if not SpaceTaskFile.objects.using(using).filter(file=name).exists():
            storage.delete(name)

    transaction.on_commit(cleanup, using=using, robust=True)
