from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from .upload_validation import validate_attachment_upload, validate_image_upload


class UploadValidationTests(SimpleTestCase):
    def test_accepts_plain_text_attachment(self):
        uploaded_file = SimpleUploadedFile('notatka.txt', b'tresc', content_type='text/plain')

        self.assertIs(validate_attachment_upload(uploaded_file), uploaded_file)

    def test_rejects_disallowed_svg_attachment(self):
        uploaded_file = SimpleUploadedFile(
            'payload.svg',
            b'<svg><script>alert(1)</script></svg>',
            content_type='image/svg+xml',
        )

        with self.assertRaises(ValidationError):
            validate_attachment_upload(uploaded_file)

    def test_rejects_spoofed_image_upload(self):
        uploaded_file = SimpleUploadedFile(
            'avatar.png',
            b'<svg><script>alert(1)</script></svg>',
            content_type='image/png',
        )

        with self.assertRaises(ValidationError):
            validate_image_upload(uploaded_file)
