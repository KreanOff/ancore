from pathlib import Path
import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models, transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver


icon_color_validator = RegexValidator(r'^#[0-9a-fA-F]{6}\Z', 'Podaj kolor w formacie #RRGGBB.')


def document_storage():
    # Document files and library photos use authenticated views, outside MEDIA_ROOT.
    return FileSystemStorage(location=settings.PRIVATE_DOCUMENT_ROOT)


def document_upload_path(instance, filename):
    return f'{instance.workplace_id}/{uuid.uuid4().hex}{Path(filename).suffix.lower()}'


def library_photo_upload_path(instance, filename):
    return f'library_photos/{instance.workplace_id}/{uuid.uuid4().hex}{Path(filename).suffix.lower()}'


class DocumentLibrary(models.Model):
    name = models.CharField('Nazwa biblioteki', max_length=120)
    color = models.CharField('Kolor ikony', max_length=7, default='#4285d4', validators=[icon_color_validator])
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
    color = models.CharField('Kolor ikony', max_length=7, default='#ffd855', validators=[icon_color_validator])
    library = models.ForeignKey(DocumentLibrary, on_delete=models.RESTRICT, related_name='folders')
    parent = models.ForeignKey('self', on_delete=models.RESTRICT, null=True, blank=True, related_name='children')
    workplace = models.ForeignKey('workplaces.Workplace', on_delete=models.CASCADE, related_name='document_folders')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='document_folders')
    favorited_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='favorite_drive_folders', blank=True)
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
    revision = models.PositiveIntegerField(default=1)
    office_key = models.UUIDField(default=uuid.uuid4, editable=False)
    office_save_error = models.BooleanField(default=False, editable=False)
    folder = models.ForeignKey(Folder, on_delete=models.RESTRICT, null=True, blank=True, related_name='documents')
    workplace = models.ForeignKey('workplaces.Workplace', on_delete=models.CASCADE, related_name='documents')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='documents')
    # Legacy relation retained for existing data; not used by Drive or Documents.
    tags = models.ManyToManyField('tasks.TaskTag', blank=True, related_name='documents', verbose_name='Tagi')
    favorited_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='favorite_drive_documents', blank=True)
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
    def office_type(self):
        return {'DOCX': 'word', 'XLSX': 'cell', 'PPTX': 'slide', 'PDF': 'pdf'}.get(self.extension, '')

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


@receiver(post_delete, sender=Document)
def delete_drive_document_file(sender, instance, using, **kwargs):
    if instance.file:
        storage, name = instance.file.storage, instance.file.name
        transaction.on_commit(lambda: storage.delete(name), using=using, robust=True)


class WorkspaceDocumentFolder(models.Model):
    """Folders of the Dokumenty module, independent from drives."""
    name = models.CharField('Nazwa folderu', max_length=120)
    color = models.CharField('Kolor ikony', max_length=7, default='#ffd855', validators=[icon_color_validator])
    parent = models.ForeignKey('self', on_delete=models.RESTRICT, null=True, blank=True, related_name='children')
    workplace = models.ForeignKey('workplaces.Workplace', on_delete=models.CASCADE, related_name='office_folders')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='office_folders')
    is_starred = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name', 'pk']
        constraints = [
            models.UniqueConstraint(fields=['owner', 'workplace', 'parent', 'name'], condition=models.Q(parent__isnull=False), name='office_unique_child_folder'),
            models.UniqueConstraint(fields=['owner', 'workplace', 'name'], condition=models.Q(parent__isnull=True), name='office_unique_root_folder'),
        ]

    def __str__(self):
        return self.name


class WorkspaceDocument(models.Model):
    class Kind(models.TextChoices):
        TEXT = 'text', 'Dokument Ancore'
        FILE = 'file', 'Przesłany dokument'
        BOARD = 'board', 'Tablica'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField('Nazwa dokumentu', max_length=255)
    kind = models.CharField(max_length=8, choices=Kind.choices, default=Kind.TEXT)
    content = models.TextField('Treść', blank=True)
    is_template = models.BooleanField('Używaj jako szablonu', default=False)
    is_pdf_form = models.BooleanField(default=False, editable=False)
    revision = models.PositiveIntegerField(default=1)
    office_key = models.UUIDField(default=uuid.uuid4, editable=False)
    office_save_error = models.BooleanField(default=False, editable=False)
    file = models.FileField(storage=document_storage, upload_to=document_upload_path, max_length=400, blank=True)
    filename = models.CharField(max_length=255, blank=True)
    file_size = models.PositiveBigIntegerField(default=0)
    folder = models.ForeignKey(WorkspaceDocumentFolder, on_delete=models.RESTRICT, null=True, blank=True, related_name='documents')
    workplace = models.ForeignKey('workplaces.Workplace', on_delete=models.CASCADE, related_name='office_documents')
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='office_documents')
    # Legacy relation retained for existing data; not used by Drive or Documents.
    tags = models.ManyToManyField('tasks.TaskTag', blank=True, related_name='office_documents', verbose_name='Tagi')
    favorited_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='favorite_workspace_documents', blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at', 'title', 'pk']
        indexes = [models.Index(fields=['workplace', 'owner', 'deleted_at'], name='office_workspace_status_idx')]

    @property
    def extension(self):
        if self.kind == self.Kind.TEXT:
            return 'ANCORE'
        if self.kind == self.Kind.BOARD:
            return 'BOARD'
        return Path(self.filename).suffix.lstrip('.').upper()

    @property
    def office_type(self):
        return {'DOCX': 'word', 'XLSX': 'cell', 'PPTX': 'slide', 'PDF': 'pdf'}.get(self.extension, '')

    @property
    def has_full_editor(self):
        return self.kind == self.Kind.BOARD or bool(self.office_type)

    @property
    def icon(self):
        if self.kind == self.Kind.BOARD:
            return 'layout-grid'
        if self.office_type == 'cell':
            return 'file-spreadsheet'
        if self.office_type == 'slide':
            return 'monitor'
        return 'file-text'

    def __str__(self):
        return self.title


@receiver(post_delete, sender=WorkspaceDocument)
def delete_workspace_document_file(sender, instance, using, **kwargs):
    if instance.file:
        storage, name = instance.file.storage, instance.file.name
        transaction.on_commit(lambda: storage.delete(name), using=using, robust=True)


class OfficeSaveReceipt(models.Model):
    """Deduplicate signed callbacks, including retries after closing an editor."""
    document = models.ForeignKey(WorkspaceDocument, on_delete=models.CASCADE, related_name='save_receipts')
    digest = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


class DriveOfficeSaveReceipt(models.Model):
    """Deduplicate editor callbacks for files stored on drives."""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='save_receipts')
    digest = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


class DocumentVersion(models.Model):
    """Immutable previous file; access always goes through its scoped parent."""
    document = models.ForeignKey(WorkspaceDocument, null=True, blank=True, on_delete=models.CASCADE, related_name='versions')
    drive_document = models.ForeignKey(Document, null=True, blank=True, on_delete=models.CASCADE, related_name='versions')
    revision = models.PositiveIntegerField()
    file = models.FileField(storage=document_storage, upload_to=document_upload_path, max_length=400)
    filename = models.CharField(max_length=255)
    file_size = models.PositiveBigIntegerField()
    is_pdf_form = models.BooleanField(default=False)
    saved_at = models.DateTimeField()
    archived_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-revision']
        constraints = [
            models.CheckConstraint(condition=(models.Q(document__isnull=False, drive_document__isnull=True)
                                              | models.Q(document__isnull=True, drive_document__isnull=False)), name='version_one_document'),
            models.UniqueConstraint(fields=['document', 'revision'], name='office_unique_version'),
            models.UniqueConstraint(fields=['drive_document', 'revision'], name='drive_unique_version'),
        ]


@receiver(post_delete, sender=DocumentVersion)
def delete_document_version_file(sender, instance, using, **kwargs):
    if instance.file:
        storage, name = instance.file.storage, instance.file.name
        transaction.on_commit(lambda: storage.delete(name), using=using, robust=True)
