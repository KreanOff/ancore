from pathlib import Path

from django.http import Http404
from django.views.static import serve


def public_media(request, path, document_root):
    """Only public profile images/logos may bypass authenticated download views."""
    directory, _, filename = path.partition('/')
    if (
        directory not in {'profile_photos', 'profile_banners', 'workplace_photos'}
        or not filename or '/' in filename or '\\' in filename
        or Path(filename).suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}
    ):
        raise Http404
    return serve(request, filename, document_root=Path(document_root) / directory)
