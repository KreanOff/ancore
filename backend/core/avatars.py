"""Shared illustrated presets for Spaces and Workspace."""

# Retain automatic assignments when the selectable catalogue grows.
AUTOMATIC_AVATARS = (
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
AVATARS = AUTOMATIC_AVATARS + (
    ('camera', 'Aparat'),
    ('headphones', 'Słuchawki'),
    ('mountain', 'Góry'),
    ('gem', 'Diament'),
    ('coffee', 'Kawa'),
    ('hot-air-balloon', 'Balon'),
)
AVATAR_CHOICES = [('auto', 'Automatyczny')] + list(AVATARS) + [('upload', 'Własny obraz')]


def preset_avatar(key='', seed=0):
    key, label = next((entry for entry in AVATARS if entry[0] == key), AUTOMATIC_AVATARS[seed % len(AUTOMATIC_AVATARS)])
    return {'key': key, 'label': label, 'preset_class': f'space-avatar-art--{key}'}
