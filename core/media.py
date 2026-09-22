from pathlib import Path

from django.http import Http404
from django.views.static import serve


def public_media(request, path, document_root):
    """Only public avatars/logos may bypass authenticated download views."""
    directory, _, filename = path.partition('/')
    if (
        directory not in {'profile_photos', 'company_photos', 'workplace_photos'}
        or not filename or '/' in filename or '\\' in filename
        or Path(filename).suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}
    ):
        raise Http404
    return serve(request, filename, document_root=Path(document_root) / directory)
