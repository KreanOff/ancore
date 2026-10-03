"""Stable space avatar identifiers mapped to the illustrated sprite atlas."""
from pathlib import Path
from uuid import uuid4

from django.db import transaction

from core.avatars import AVATARS, AVATAR_CHOICES, preset_avatar
from workplaces.services import scoped_workplace_app_path


def avatar_upload_path(instance, filename):
    return f'space_avatars/{uuid4().hex}{Path(filename).suffix.lower()}'


def space_avatar(space):
    avatar = preset_avatar(space.avatar, space.pk or 0)
    if space.avatar_photo:
        avatar['photo_url'] = scoped_workplace_app_path(space.workplace, 'spaces', f'{space.pk}/avatar/photo/')
    return avatar


def delete_avatar_after_commit(storage, name, using='default'):
    if not name:
        return

    def cleanup():
        from .models import Space
        if not Space.objects.using(using).filter(avatar_photo=name).exists():
            storage.delete(name)

    transaction.on_commit(cleanup, using=using, robust=True)
