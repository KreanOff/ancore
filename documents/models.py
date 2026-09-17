from pathlib import Path
import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.validators import FileExtensionValidator
from django.db import models, transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver


def document_storage():
    # Document files and library photos use authenticated views, outside MEDIA_ROOT.
    return FileSystemStorage(location=settings.PRIVATE_DOCUMENT_ROOT)


def document_upload_path(instance, filename):
    return f'{instance.workplace_id}/{uuid.uuid4().hex}{Path(filename).suffix.lower()}'


def library_photo_upload_path(instance, filename):
    return f'library_photos/{instance.workplace_id}/{uuid.uuid4().hex}{Path(filename).suffix.lower()}'


class DocumentLibrary(models.Model):
    name = models.CharField('Nazwa biblioteki', max_length=120)
    description = models.TextField('Opis', blank=True, max_length=2000)
    photo = models.FileField(
        'Zdjęcie biblioteki', blank=True, storage=document_storage,
        upload_to=library_photo_upload_path,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
    )
    workplace = models.ForeignKey('workplaces.Workplace', on_delete=models.CASCADE, related_name='document_libraries')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='document_libraries')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name', 'pk']
        constraints = [models.UniqueConstraint(fields=['workplace', 'owner', 'name'], name='documents_unique_library_name')]

    def __str__(self):
        return self.name


@receiver(post_delete, sender=DocumentLibrary)
def delete_library_photo(sender, instance, using, **kwargs):
    if instance.photo:
        storage, name = instance.photo.storage, instance.photo.name
        transaction.on_commit(lambda: storage.delete(name), using=using, robust=True)


class Folder(models.Model):
    name = models.CharField('Nazwa folderu', max_length=120)
    library = models.ForeignKey(DocumentLibrary, on_delete=models.RESTRICT, related_name='folders')
    parent = models.ForeignKey('self', on_delete=models.RESTRICT, null=True, blank=True, related_name='children')
    workplace = models.ForeignKey('workplaces.Workplace', on_delete=models.CASCADE, related_name='document_folders')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='document_folders')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name', 'pk']
        constraints = [
            models.UniqueConstraint(fields=['library', 'parent', 'name'], condition=models.Q(parent__isnull=False), name='documents_unique_child_folder'),
            models.UniqueConstraint(fields=['library', 'name'], condition=models.Q(parent__isnull=True), name='documents_unique_root_folder'),
        ]

    def __str__(self):
        return self.name


class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField('Nazwa dokumentu', max_length=255)
    library = models.ForeignKey(DocumentLibrary, on_delete=models.RESTRICT, related_name='documents')
    description = models.TextField('Opis', blank=True, max_length=5000)
    file = models.FileField(storage=document_storage, upload_to=document_upload_path, max_length=400)
    filename = models.CharField(max_length=255)
    file_size = models.PositiveBigIntegerField(default=0)
    folder = models.ForeignKey(Folder, on_delete=models.RESTRICT, null=True, blank=True, related_name='documents')
    workplace = models.ForeignKey('workplaces.Workplace', on_delete=models.CASCADE, related_name='documents')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='documents')
    tags = models.ManyToManyField('tasks.TaskTag', blank=True, related_name='documents', verbose_name='Tagi')
    is_starred = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', 'title', 'pk']
        indexes = [models.Index(fields=['workplace', 'owner', 'deleted_at'], name='documents_workspace_status_idx')]

    @property
    def extension(self):
        return Path(self.filename).suffix.lstrip('.').upper() or 'PLIK'

    @property
    def icon(self):
        extension = self.extension.lower()
        if extension in {'jpg', 'jpeg', 'png', 'gif', 'webp'}:
            return 'file-image'
        if extension in {'xls', 'xlsx', 'csv'}:
            return 'file-spreadsheet'
        if extension in {'zip', 'rar', '7z', 'gz', 'tar'}:
            return 'file-archive'
        return 'file-text'

    def __str__(self):
        return self.title
