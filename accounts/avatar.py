from .avatar_presets import preset_avatar


AVATAR_COLOR_CLASSES = [
    'profile-avatar--blue',
    'profile-avatar--teal',
    'profile-avatar--green',
    'profile-avatar--violet',
    'profile-avatar--rose',
    'profile-avatar--amber',
]


def avatar_color_seed(user):
    if user is not None and getattr(user, 'pk', None) is not None:
        try:
            return int(user.pk)
        except (TypeError, ValueError):
            pass

    color_basis = 'system'
    if user is not None:
        color_basis = str(user.email or user.username or user.get_full_name() or 'user')

    return sum((index + 1) * ord(char) for index, char in enumerate(color_basis))


def avatar_color_style(user):
    seed = avatar_color_seed(user)
    return avatar_color_style_from_seed(seed)


def avatar_color_style_from_seed(seed):
    hue = (seed * 137) % 360
    saturation = 50 + (seed % 18)
    lightness = 36 + ((seed // 7) % 10)

    background_color = f'hsl({hue}, {saturation}%, {lightness}%)'
    foreground_color = '#ffffff'

    return {
        'background_color': background_color,
        'foreground_color': foreground_color,
        'color_style': f'--profile-avatar-bg: {background_color}; --profile-avatar-fg: {foreground_color};',
    }


def avatar_color_class(seed):
    return AVATAR_COLOR_CLASSES[seed % len(AVATAR_COLOR_CLASSES)]


def account_avatar(user, color_index=None):
    first_initial = ''
    last_initial = ''
    photo_url = ''

    if user is not None:
        first_initial = (user.first_name or '').strip()[:1]
        last_initial = (user.last_name or '').strip()[:1]

        if getattr(user, 'profile_photo', None):
            try:
                photo_url = user.profile_photo.url
            except ValueError:
                photo_url = ''

    initials = f'{first_initial}{last_initial}'.upper()
    if not initials and user is not None:
        initials = (user.email or user.username or '?').strip()[:1].upper()
    if not initials:
        initials = 'S'

    if color_index is None:
        color_index = avatar_color_seed(user)

    return {
        **(preset_avatar(getattr(user, 'avatar', ''), avatar_color_seed(user)) if user is not None else {}),
        'initials': initials,
        'color_class': avatar_color_class(color_index),
        'photo_url': photo_url,
        **avatar_color_style(user),
    }
