"""Stable space avatar identifiers mapped to the illustrated sprite atlas."""
from pathlib import Path
from uuid import uuid4

from django.db import transaction

from workplaces.services import scoped_workplace_app_path


AVATARS = (
    ('rocket', 'Rakieta'),
    ('compass', 'Kompas'),
    ('lightbulb', 'Pomysł'),
    ('leaf', 'Liść'),
    ('palette', 'Paleta'),
    ('globe', 'Globus'),
    ('flask-conical', 'Laboratorium'),
    ('target', 'Cel'),
    ('laptop', 'Komputer'),
    ('flag', 'Flaga'),
    ('puzzle', 'Puzzle'),
    ('cloud', 'Chmura'),
    ('plane', 'Samolot'),
    ('book-open', 'Książka'),
    ('heart', 'Serce'),
    ('zap', 'Błyskawica'),
    ('shield-check', 'Tarcza'),
    ('layers', 'Warstwy'),
    ('megaphone', 'Megafon'),
    ('trophy', 'Puchar'),
    ('wrench', 'Narzędzia'),
    ('star', 'Gwiazda'),
    ('ship', 'Statek'),
    ('smile', 'Uśmiech'),
)
AVATAR_CHOICES = [('auto', 'Automatyczny')] + list(AVATARS) + [('upload', 'Własny obraz')]


def avatar_upload_path(instance, filename):
    return f'space_avatars/{uuid4().hex}{Path(filename).suffix.lower()}'


def preset_avatar(key='', seed=0):
    key, label = next((entry for entry in AVATARS if entry[0] == key), AVATARS[seed % len(AVATARS)])
    return {'key': key, 'label': label, 'preset_class': f'space-avatar-art--{key}'}


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
