"""Private storage and presentation shared by Space task attachments."""
from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage

from core.upload_validation import COMMENT_IMAGE_EXTENSIONS


def comment_image_storage():
    return FileSystemStorage(location=settings.PRIVATE_DOCUMENT_ROOT)


class AttachmentPresentation:
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
