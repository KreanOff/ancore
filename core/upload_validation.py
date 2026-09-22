import base64
import binascii
import mimetypes
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import FileResponse


MB = 1024 * 1024
DEFAULT_IMAGE_MAX_SIZE = 5 * MB
DEFAULT_ATTACHMENT_MAX_SIZE = 10 * MB

IMAGE_CONTENT_TYPES = {
    'image/jpeg': 'jpg',
    'image/jpg': 'jpg',
    'image/png': 'png',
    'image/webp': 'webp',
}
IMAGE_EXTENSIONS = {
    '.jpg': 'jpg',
    '.jpeg': 'jpg',
    '.png': 'png',
    '.webp': 'webp',
}
ATTACHMENT_ALLOWED_EXTENSIONS = {
    '.csv',
    '.doc',
    '.docx',
    '.gif',
    '.gz',
    '.jpg',
    '.jpeg',
    '.pdf',
    '.ppt',
    '.pptx',
    '.png',
    '.rar',
    '.rtf',
    '.tar',
    '.txt',
    '.webp',
    '.xls',
    '.xlsx',
    '.zip',
    '.7z',
}


def _read_start(uploaded_file, length=4096):
    position = None
    try:
        position = uploaded_file.tell()
    except (AttributeError, OSError):
        pass

    try:
        uploaded_file.seek(0)
    except (AttributeError, OSError):
        pass

    data = uploaded_file.read(length)

    if position is not None:
        try:
            uploaded_file.seek(position)
        except (AttributeError, OSError):
            pass
    else:
        try:
            uploaded_file.seek(0)
        except (AttributeError, OSError):
            pass

    return data or b''


def _extension(filename):
    return os.path.splitext(filename or '')[1].lower()


def _detect_image_extension(data):
    if data.startswith(b'\xff\xd8\xff'):
        return 'jpg'
    if data.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if data.startswith((b'GIF87a', b'GIF89a')):
        return 'gif'
    if len(data) >= 12 and data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'webp'
    return ''


def _looks_like_text(data):
    if b'\x00' in data:
        return False
    if not data:
        return True
    for encoding in ('utf-8', 'utf-16'):
        try:
            data.decode(encoding)
            return True
        except UnicodeDecodeError:
            continue
    return False


def _looks_like_tar(data):
    return len(data) > 262 and data[257:262] == b'ustar'


def _validate_attachment_signature(extension, data):
    if extension in {'.jpg', '.jpeg'}:
        return _detect_image_extension(data) == 'jpg'
    if extension == '.png':
        return _detect_image_extension(data) == 'png'
    if extension == '.gif':
        return _detect_image_extension(data) == 'gif'
    if extension == '.webp':
        return _detect_image_extension(data) == 'webp'
    if extension == '.pdf':
        return data.startswith(b'%PDF-')
    if extension in {'.txt', '.csv'}:
        return _looks_like_text(data)
    if extension == '.rtf':
        return data.startswith(b'{\\rtf')
    if extension in {'.doc', '.xls', '.ppt'}:
        return data.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1')
    if extension in {'.docx', '.xlsx', '.pptx', '.zip'}:
        return data.startswith((b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08'))
    if extension == '.rar':
        return data.startswith(b'Rar!\x1a\x07')
    if extension == '.7z':
        return data.startswith(b"7z\xbc\xaf'\x1c")
    if extension == '.gz':
        return data.startswith(b'\x1f\x8b')
    if extension == '.tar':
        return _looks_like_tar(data)
    return False


def validate_image_bytes(content, content_type, max_size=DEFAULT_IMAGE_MAX_SIZE):
    if len(content) > max_size:
        raise ValidationError('Zdjęcie może mieć maksymalnie 5 MB.')

    declared_extension = IMAGE_CONTENT_TYPES.get((content_type or '').lower())
    if declared_extension is None:
        raise ValidationError('Wybierz plik obrazu.')

    detected_extension = _detect_image_extension(content[:32])
    if detected_extension != declared_extension:
        raise ValidationError('Plik obrazu ma nieprawidłową zawartość.')

    return detected_extension


def validate_image_crop(crop_data, max_size=DEFAULT_IMAGE_MAX_SIZE, error_message='Nie udało się odczytać przyciętego zdjęcia.'):
    crop_data = (crop_data or '').strip()
    if not crop_data:
        return None
    header, separator, encoded = crop_data.partition(',')
    if not separator or not header.startswith('data:') or not header.endswith(';base64'):
        raise ValidationError(error_message)
    # Bound the encoded input before allocating the decoded image.
    if len(encoded) > ((max_size + 2) // 3) * 4:
        raise ValidationError('Zdjęcie może mieć maksymalnie 5 MB.')
    try:
        content = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError):
        raise ValidationError(error_message)
    extension = validate_image_bytes(content, header[5:-7].lower(), max_size)
    return {'content': content, 'extension': extension}


def validate_image_upload(uploaded_file, max_size=DEFAULT_IMAGE_MAX_SIZE):
    if not uploaded_file:
        return uploaded_file

    if uploaded_file.size > max_size:
        raise ValidationError('Zdjęcie może mieć maksymalnie 5 MB.')

    expected_extension = IMAGE_EXTENSIONS.get(_extension(uploaded_file.name))
    if expected_extension is None:
        raise ValidationError('Wybierz plik obrazu.')

    detected_extension = _detect_image_extension(_read_start(uploaded_file, 32))
    if detected_extension != expected_extension:
        raise ValidationError('Plik obrazu ma nieprawidłową zawartość.')

    return uploaded_file


def validate_attachment_upload(uploaded_file):
    max_size = getattr(settings, 'MAX_ATTACHMENT_SIZE', DEFAULT_ATTACHMENT_MAX_SIZE)
    extension = _extension(getattr(uploaded_file, 'name', ''))

    if extension not in ATTACHMENT_ALLOWED_EXTENSIONS:
        raise ValidationError('Ten typ załącznika nie jest dozwolony.')

    if uploaded_file.size <= 0:
        raise ValidationError('Załącznik nie może być pusty.')
    if uploaded_file.size > max_size:
        raise ValidationError('Załącznik może mieć maksymalnie 10 MB.')

    sample = _read_start(uploaded_file, 4096)
    if not _validate_attachment_signature(extension, sample):
        raise ValidationError('Załącznik ma nieprawidłową zawartość.')

    return uploaded_file


def attachment_download_response(attachment):
    content_type, _encoding = mimetypes.guess_type(attachment.filename)
    response = FileResponse(
        attachment.file.open('rb'),
        as_attachment=True,
        filename=attachment.filename,
        content_type=content_type or 'application/octet-stream',
    )
    response['X-Content-Type-Options'] = 'nosniff'
    response['Cache-Control'] = 'private, no-store'
    return response
