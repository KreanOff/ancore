from django import template

from core.avatars import preset_avatar

from accounts.avatar import avatar_color_class, avatar_color_style_from_seed


register = template.Library()


def workplace_avatar_seed(workplace):
    if workplace is not None and getattr(workplace, 'pk', None) is not None:
        try:
            return int(workplace.pk)
        except (TypeError, ValueError):
            pass

    color_basis = 'workplace'
    if workplace is not None:
        color_basis = str(getattr(workplace, 'name', '') or getattr(workplace, 'slug', '') or 'workplace')

    return sum((index + 1) * ord(char) for index, char in enumerate(color_basis))


@register.simple_tag
def workplace_avatar(workplace):
    seed = workplace_avatar_seed(workplace)
    photo_url = ''

    if workplace is not None and getattr(workplace, 'workplace_photo', None):
        try:
            photo_url = workplace.workplace_photo.url
        except ValueError:
            photo_url = ''

    return {
        **preset_avatar(getattr(workplace, 'avatar', ''), seed),
        'color_class': avatar_color_class(seed),
        'photo_url': photo_url,
        **avatar_color_style_from_seed(seed),
    }
