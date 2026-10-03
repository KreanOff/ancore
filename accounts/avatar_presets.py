"""Personal avatar illustrations, separate from Spaces and Workspace."""

# Keep automatic avatars stable as the selectable collection grows.
AUTOMATIC_AVATARS = (
    ('fox', 'Lis'), ('cat', 'Kot'), ('panda', 'Panda'),
    ('koala', 'Koala'), ('rabbit', 'Królik'), ('bear', 'Niedźwiedź'),
    ('owl', 'Sowa'), ('penguin', 'Pingwin'), ('tiger', 'Tygrys'),
    ('lion', 'Lew'), ('dog', 'Pies'), ('raccoon', 'Szop'),
    ('red-panda', 'Panda ruda'), ('hedgehog', 'Jeż'), ('otter', 'Wydra'),
    ('frog', 'Żaba'), ('deer', 'Jeleń'), ('wolf', 'Wilk'),
    ('seal', 'Foka'), ('sloth', 'Leniwiec'), ('squirrel', 'Wiewiórka'),
    ('parrot', 'Papuga'), ('chameleon', 'Kameleon'), ('capybara', 'Kapibara'),
)
AVATARS = AUTOMATIC_AVATARS + (
    ('octopus', 'Ośmiornica'), ('whale', 'Wieloryb'), ('turtle', 'Żółw'),
    ('bat', 'Nietoperz'), ('bee', 'Pszczoła'), ('dinosaur', 'Dinozaur'),
)
AVATAR_CHOICES = [('auto', 'Automatyczny')] + list(AVATARS) + [('upload', 'Własny obraz')]


def preset_avatar(key='', seed=0):
    key, label = next((entry for entry in AVATARS if entry[0] == key), AUTOMATIC_AVATARS[seed % len(AUTOMATIC_AVATARS)])
    return {'key': key, 'label': label, 'art_class': 'user-avatar-art', 'preset_class': f'user-avatar-art--{key}'}
