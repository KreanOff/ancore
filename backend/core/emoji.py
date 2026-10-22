"""Local Fluent Emoji 3D atlases, shared presentation and server-side allowlist."""
from functools import lru_cache
import json

from django.conf import settings
from django.core.exceptions import ValidationError
from django.templatetags.static import static

LEGACY_VALUES = {
    'layout-dashboard': '📊', 'chart-no-axes-combined': '📈', 'users': '👥', 'layers': '🗂️',
    'calendar-days': '📅', 'folder': '📁', 'star': '⭐', 'file-text': '📄',
}


@lru_cache(maxsize=1)
def emoji_catalog():
    return json.loads((settings.BASE_DIR / 'static/vendor/fluent-emoji/catalog.json').read_text())


@lru_cache(maxsize=1)
def emoji_index():
    return {item['value'].replace('\ufe0f', ''): item for item in emoji_catalog()['items']}


def find_emoji(value):
    return emoji_index().get(LEGACY_VALUES.get(value, value).replace('\ufe0f', ''))


def validate_emoji(value):
    if not find_emoji(value):
        raise ValidationError('Wybierz emoji z biblioteki.', code='invalid_emoji')


def emoji_art(item):
    return {'url': static(f'vendor/fluent-emoji/sheet-{item["sheet"]:02}.webp') + '?v=' + emoji_catalog()['version'],
            'position': f'{item["x"] * 100 / 15:.6f}% {item["y"] * 100 / 15:.6f}%'}


def emoji_payload(value):
    item = find_emoji(value)
    if value == 'layout-dashboard' or item is None:
        return {'value': 'layout-dashboard', 'label': 'Pulpit', 'art': {'icon': 'layout-dashboard'}}
    return {'value': item['value'], 'label': item['label'], 'art': emoji_art(item)}


def emoji_picker_config(value):
    return {'selected': emoji_payload(value),
            'default': emoji_payload('layout-dashboard'),
            'catalog_url': static('vendor/fluent-emoji/catalog.json') + '?v=' + emoji_catalog()['version'],
            'asset_url': static('vendor/fluent-emoji/')}
