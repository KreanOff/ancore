"""Bounded Excalidraw scenes, stored privately with optimistic revisions."""
import json
import math
from django.core.exceptions import ValidationError
from core.upload_validation import validate_image_crop

BOARD_LIMIT = 10 * 1024 * 1024
ELEMENT_TYPES = {'rectangle', 'diamond', 'ellipse', 'arrow', 'line', 'freedraw', 'text', 'image', 'frame', 'magicframe'}
EMPTY_SCENE = {'type': 'excalidraw', 'version': 2, 'source': 'Ancore', 'elements': [], 'appState': {'viewBackgroundColor': '#ffffff'}, 'files': {}}


def clean_scene(raw):
    try:
        if len(raw.encode('utf-8') if isinstance(raw, str) else raw) > BOARD_LIMIT:
            raise ValidationError('Tablica może mieć maksymalnie 10 MB.')
        data = json.loads(raw, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        if not isinstance(data, dict) or data.get('type') != 'excalidraw' or data.get('version') != 2:
            raise ValueError
        elements, files, state = data.get('elements'), data.get('files', {}), data.get('appState', {})
        if not isinstance(elements, list) or len(elements) > 10000 or not isinstance(files, dict) or not isinstance(state, dict):
            raise ValueError
        ids = set()
        for element in elements:
            if not isinstance(element, dict) or element.get('type') not in ELEMENT_TYPES:
                raise ValidationError('Tablica zawiera nieobsługiwany element osadzony.')
            key = element.get('id')
            if not isinstance(key, str) or not key or len(key) > 100 or key in ids:
                raise ValueError
            ids.add(key)
            for name in ('x', 'y', 'width', 'height', 'angle'):
                value = element.get(name, 0)
                if not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > 10000000:
                    raise ValueError
            link = element.get('link')
            if link and (not isinstance(link, str) or not link.startswith(('https://', 'http://', 'mailto:'))):
                raise ValidationError('Odnośniki tablicy muszą zaczynać się od https://, http:// lub mailto:.')
        if len(files) > 200:
            raise ValidationError('Tablica może zawierać maksymalnie 200 obrazów.')
        for key, file in files.items():
            if not isinstance(file, dict) or file.get('id') != key or not isinstance(file.get('dataURL'), str):
                raise ValueError
            # Uses the application's existing bounded byte/signature validator.
            if not validate_image_crop(file['dataURL']) or not file['dataURL'].startswith(f"data:{file.get('mimeType')};base64,"):
                raise ValueError
            if file.get('mimeType') not in {'image/png', 'image/jpeg', 'image/webp'}:
                raise ValidationError('Na tablicę wstawiaj obrazy PNG, JPG lub WebP.')
        background = state.get('viewBackgroundColor', '#ffffff')
        if not isinstance(background, str) or len(background) > 50:
            raise ValueError
        return json.dumps({**EMPTY_SCENE, 'elements': elements, 'files': files,
                           'appState': {'viewBackgroundColor': background}}, ensure_ascii=False, allow_nan=False)
    except (ValueError, TypeError, UnicodeError, RecursionError) as error:
        raise ValidationError('Nie udało się odczytać tablicy. Wybierz prawidłowy plik .excalidraw.') from error
