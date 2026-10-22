"""Build local 64px Fluent Emoji 3D atlases and Polish search data.

Usage: python build_fluent_emoji.py FLUENT_TAR PL_XML PL_DERIVED_XML CLDR_LICENSE
Build dependency: Pillow. Sources and hashes are pinned; no runtime CDN or package.
"""
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import unicodedata
import xml.etree.ElementTree as ET

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
COMMIT = '1ffb34c752ecf5d402f04cfb4b392c77f57c54bc'
HASHES = [
    '5fc28b1d47e1b60c70b0b1213bca37850a7702f157bc2492e80178de00840701',
    '34007d7477170c2f209e4707d1092591f150aeb85e1117d68d9e0bed00e902be',
    'f46fdb3c58e1ccfd4c8be0e6c07807b8dc81c3a9aa1f5e364951e401f29d3c17',
    'b4c0ae8ef04f7059f96ce5bbe0467f9fe6f6d81bbe13517701dfeb961fb4d0b6',
]
GROUPS = [
    ('Smileys & Emotion', 'smileys', 'Buźki i emocje', 'smile'),
    ('People & Body', 'people', 'Ludzie i gesty', 'users'),
    ('Animals & Nature', 'nature', 'Zwierzęta i natura', 'leaf'),
    ('Food & Drink', 'food', 'Jedzenie i napoje', 'pizza'),
    ('Travel & Places', 'travel', 'Podróże i miejsca', 'globe'),
    ('Activities', 'activities', 'Sport i zabawa', 'trophy'),
    ('Objects', 'objects', 'Przedmioty', 'lightbulb'),
    ('Symbols', 'symbols', 'Symbole', 'heart'),
    ('Flags', 'flags', 'Flagi', 'flag'),
]
TONES = {'Default': 0, 'Light': 1, 'Medium-Light': 2, 'Medium': 3, 'Medium-Dark': 4, 'Dark': 5}


def normalize(text):
    return ''.join(char for char in unicodedata.normalize('NFD', text.lower().replace('ł', 'l'))
                   if not unicodedata.combining(char))


def build(paths):
    for path, expected in zip(paths, HASHES, strict=True):
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Unexpected source archive: {path}')
    labels, keywords = {}, {}
    for path in paths[1:3]:
        for entry in ET.parse(path).iter('annotation'):
            key = entry.attrib['cp'].replace('\ufe0f', '')
            if entry.attrib.get('type') == 'tts':
                labels[key] = entry.text or ''
            else:
                keywords[key] = (entry.text or '').split(' | ')
    output = ROOT / 'static/vendor/fluent-emoji'
    output.mkdir(parents=True, exist_ok=True)
    rows, images, seen = [], [], set()
    with tarfile.open(paths[0]) as archive:
        members = archive.getmembers()
        prefix = f'fluentui-emoji-{COMMIT}/'
        metadata = {item.name[len(prefix):].removesuffix('/metadata.json'): json.load(archive.extractfile(item))
                    for item in members if item.name.endswith('/metadata.json')}
        for item in sorted(members, key=lambda item: item.name):
            path = item.name.removeprefix(prefix)
            if '/3D/' not in path or not path.endswith('.png'):
                continue
            parts = path.split('/')
            data = metadata['/'.join(parts[:2])]
            tone = TONES.get(parts[2], 0)
            code = data.get('unicodeSkintones', [data['unicode']])[tone]
            glyph = ''.join(chr(int(char, 16)) for char in code.split())
            key = glyph.replace('\ufe0f', '')
            base_key = data['glyph'].replace('\ufe0f', '')
            label = labels.get(key, labels.get(base_key, data['tts']))
            if tone and key not in labels:
                label += f' — odcień skóry {tone}'
            group = next(group[1] for group in GROUPS if group[0] == data['group'])
            words = [label, data['tts'], *keywords.get(base_key, []), *keywords.get(key, []), *data['keywords']]
            row = {'value': glyph, 'label': label, 'category': group,
                   'search': normalize(' '.join(dict.fromkeys(words)))}
            if glyph in seen:
                raise ValueError(f'Duplicate emoji: {glyph}')
            seen.add(glyph)
            rows.append(row)
            image = Image.open(io.BytesIO(archive.extractfile(item).read())).convert('RGBA')
            image.thumbnail((64, 64), Image.Resampling.LANCZOS)
            images.append(image)
        license_file = next(item for item in members if item.name == prefix + 'LICENSE')
        (output / 'LICENSE-MICROSOFT').write_bytes(archive.extractfile(license_file).read())
    # Adjacent categories share sheets so opening a category fetches only its art.
    group_order = {group[1]: index for index, group in enumerate(GROUPS)}
    pairs = sorted(zip(rows, images, strict=True), key=lambda pair: group_order[pair[0]['category']])
    rows, images = map(list, zip(*pairs, strict=True))
    for page in range((len(rows) + 255) // 256):
        sheet = Image.new('RGBA', (1024, 1024))
        for index in range(page * 256, min((page + 1) * 256, len(rows))):
            x, y = index % 16, (index % 256) // 16
            sheet.alpha_composite(images[index], (x * 64, y * 64))
            rows[index].update(sheet=page, x=x, y=y)
        sheet.save(output / f'sheet-{page:02}.webp', quality=85, method=6)
    catalog = {'version': COMMIT[:12] + '-atlas1', 'style': 'Microsoft Fluent Emoji 3D',
               'categories': [{'id': key, 'label': label, 'icon': icon} for _, key, label, icon in GROUPS],
               'items': rows}
    (output / 'catalog.json').write_text(json.dumps(catalog, ensure_ascii=False, separators=(',', ':')) + '\n')
    (output / 'LICENSE-UNICODE').write_bytes(Path(paths[3]).read_bytes())
    print(f'Built {len(rows)} emoji in {page + 1} local atlases; max value length: {max(len(row["value"]) for row in rows)}.')
    print(f'Assets: {sum(path.stat().st_size for path in output.iterdir()) / 1024 / 1024:.2f} MiB')


if __name__ == '__main__':
    build(sys.argv[1:])
