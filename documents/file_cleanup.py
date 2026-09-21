"""Cleanup for replaced private files, after their database write commits."""
from django.db import transaction


def delete_replaced_file(document, name):
    if not name or name == document.file.name:
        return
    storage = document.file.storage
    using = document._state.db

    def cleanup():
        # Retired history records still own their archived files.
        if not document.versions.using(using).filter(file=name).exists():
            storage.delete(name)

    transaction.on_commit(cleanup, using=using, robust=True)
