"""Stable space avatar identifiers mapped to the illustrated sprite atlas."""
from pathlib import Path
from uuid import uuid4

from django.db import transaction
from django.core.exceptions import ValidationError

from core.avatars import AVATARS, AVATAR_CHOICES, preset_avatar
from workplaces.services import scoped_workplace_app_path


def avatar_upload_path(instance, filename):
    return f'space_avatars/{uuid4().hex}{Path(filename).suffix.lower()}'


def space_avatar(space):
    avatar = preset_avatar(space.avatar, space.pk or 0)
    if space.avatar_photo:
        avatar['photo_url'] = scoped_workplace_app_path(space.workplace, 'space', f'{space.slug}/avatar/photo/')
    return avatar


def delete_avatar_after_commit(storage, name, using='default'):
    if not name:
        return

    def cleanup():
        from .models import Space
        if not Space.objects.using(using).filter(avatar_photo=name).exists():
            storage.delete(name)

    transaction.on_commit(cleanup, using=using, robust=True)


def save_space_avatar(space, data):
    """Save a validated avatar on a locked space; return any newly written file."""
    old_photo, storage = space.avatar_photo.name, space.avatar_photo.storage
    uploaded, choice = data.get('avatar_photo'), data['avatar']
    if choice == 'upload' and not uploaded and not old_photo:
        raise ValidationError('Obraz został usunięty. Wybierz go ponownie.')
    saved_file = None
    try:
        if uploaded:
            space.avatar_photo.save(uploaded.name, uploaded, save=False)
            saved_file = (storage, space.avatar_photo.name)
        elif choice != 'upload':
            space.avatar_photo = ''
        if choice != 'upload':
            space.avatar = '' if choice == 'auto' else choice
        space.save()
        if old_photo != space.avatar_photo.name:
            delete_avatar_after_commit(storage, old_photo)
        return saved_file
    except Exception:
        if saved_file:
            storage.delete(saved_file[1])
        raise
