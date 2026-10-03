"""Private comment attachments; image model names and URLs stay compatible."""
import logging
from pathlib import Path
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import models, transaction
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse

from core.upload_validation import COMMENT_IMAGE_EXTENSIONS, attachment_download_response, validate_comment_attachments
from workplaces.services import scoped_workplace_app_path, workspace_owner


logger = logging.getLogger(__name__)


def comment_image_storage():
    return FileSystemStorage(location=settings.PRIVATE_DOCUMENT_ROOT)


def comment_image_path(instance, filename):
    return f'comment_images/{instance._meta.app_label}/{uuid.uuid4().hex}{Path(filename).suffix.lower()}'


class CommentImage(models.Model):
    file = models.FileField(storage=comment_image_storage, upload_to=comment_image_path)
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(default=0)

    class Meta:
        abstract = True
        ordering = ['pk']

    def get_url(self):
        task = self.activity.task
        app = self._meta.app_label
        if task.workplace_id:
            return scoped_workplace_app_path(task.workplace, app, f'comment-images/{self.pk}/')
        return reverse(f'{app}:comment_image', args=[self.pk])

    def is_image(self):
        return Path(self.filename).suffix.lower() in COMMENT_IMAGE_EXTENSIONS

    def get_type_class(self):
        extension = Path(self.filename).suffix.lower()
        if self.is_image():
            return 'image'
        if extension == '.pdf':
            return 'pdf'
        if extension in {'.zip', '.rar', '.7z', '.tar', '.gz'}:
            return 'archive'
        if extension in {'.doc', '.docx', '.xls', '.xlsx', '.txt', '.csv', '.rtf'}:
            return 'document'
        return 'default'

    def get_formatted_size(self):
        size = float(self.file_size)
        if not size:
            return '0 B'
        for unit in ('B', 'KB', 'MB', 'GB'):
            if size < 1024 or unit == 'GB':
                return f'{size:.1f} {unit}'
            size /= 1024


def delete_comment_image_file(sender, instance, using, **kwargs):
    from core.task_files import delete_after_commit
    delete_after_commit(instance, using, comment=True)


def save_comment(request, task, image_model, record_activity):
    from dashboard.collaboration import comment_mention_metadata

    raw_comment = request.POST.get('activity_comment') or ''
    comment = raw_comment.replace('\r\n', '\n').strip()
    # Older open tabs still submit the original image field.
    files = request.FILES.getlist('comment_attachments') + request.FILES.getlist('comment_images')
    validate_comment_attachments(files)
    if not comment and not files:
        raise ValidationError('Wpisz treść komentarza lub dodaj plik.')

    saved_files = []
    try:
        with transaction.atomic():
            activity = record_activity(
                task, request.user, 'commented', comment, kind='comment',
                metadata=comment_mention_metadata(task, raw_comment, request.POST.get('activity_mentions')),
            )
            for uploaded in files:
                image = image_model(activity=activity, filename=uploaded.name, file_size=uploaded.size)
                image.file.save(uploaded.name, uploaded, save=False)
                saved_files.append((image.file.storage, image.file.name))
                image.save()
    except Exception:
        # Database rollback does not roll back storage writes.
        for storage, name in saved_files:
            try:
                storage.delete(name)
            except OSError:
                logger.exception('Failed to clean up a comment attachment after rollback')
        raise
    return activity


def comment_image_response(request, image_model, image_id):
    from tasks.access import visible_to

    image = get_object_or_404(
        visible_to(image_model.objects.all(), request.user).select_related('activity__task').filter(
            activity__kind='comment', activity__task__user=workspace_owner(request),
            activity__task__workplace=request.workplace,
        ), pk=image_id,
    )
    try:
        return attachment_download_response(image, inline=image.is_image())
    except FileNotFoundError:
        raise Http404
