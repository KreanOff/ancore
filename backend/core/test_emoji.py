from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from .emoji import emoji_catalog, emoji_payload, find_emoji, validate_emoji


class EmojiLibraryTests(SimpleTestCase):
    def test_large_library_has_local_art_and_polish_search(self):
        catalog = emoji_catalog()
        self.assertGreaterEqual(len(catalog['items']), 3000)
        self.assertEqual(len({row['value'] for row in catalog['items']}), len(catalog['items']))
        for row in catalog['items']:
            self.assertLessEqual(len(row['value']), 32)
            self.assertTrue((settings.BASE_DIR / f'static/vendor/fluent-emoji/sheet-{row["sheet"]:02}.webp').is_file())
            self.assertTrue(0 <= row['x'] < 16 and 0 <= row['y'] < 16)
        self.assertIn('rakieta', find_emoji('🚀')['search'])
        self.assertEqual(find_emoji('👩🏽\u200d💻')['category'], 'people')
        self.assertIn('karnacja', find_emoji('👩🏽\u200d💻')['label'])

    def test_legacy_and_unicode_values_share_art_and_reject_external_input(self):
        self.assertEqual(emoji_payload('layout-dashboard'), {
            'value': 'layout-dashboard', 'label': 'Pulpit', 'art': {'icon': 'layout-dashboard'},
        })
        self.assertIn('url', emoji_payload('📊')['art'])
        self.assertEqual(emoji_payload('star'), emoji_payload('⭐'))
        for value in ('arbitrary', '<img src=x>', 'https://example.test/emoji.svg'):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validate_emoji(value)
