"""File snapshots retained in the same private storage as their parent."""
from .models import DocumentVersion


def version_parent(document):
    return {'drive_document': document} if document._meta.label_lower == 'documents.document' else {'document': document}


def archive_current(document):
    """Call under the parent's row lock, before replacing its file.

    Retain the old storage object instead of copying it. The transaction owns
    the reference transfer; a rollback leaves the current file untouched.
    """
    return DocumentVersion.objects.get_or_create(
        **version_parent(document), revision=document.revision,
        defaults={'file': document.file.name, 'filename': document.filename,
                  'file_size': document.file_size, 'saved_at': document.updated_at,
                  'is_pdf_form': getattr(document, 'is_pdf_form', False)},
    )[0]
