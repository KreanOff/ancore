from django import forms
from django.test import SimpleTestCase

from .frontend import form_payload


class PayloadForm(forms.Form):
    title = forms.CharField(label='Tytuł', max_length=8)
    description = forms.CharField(label='Opis', required=False, widget=forms.Textarea)
    visibility = forms.ChoiceField(choices=[('private', 'Prywatne'), ('public', 'Publiczne')])
    revision = forms.IntegerField(widget=forms.HiddenInput)


class FormPayloadFieldIdentityTests(SimpleTestCase):
    def test_unbound_prefixed_schema_separates_logical_names_from_submission_names(self):
        for prefix in ('subtask', 'worklog', 'items-0'):
            with self.subTest(prefix=prefix):
                form = PayloadForm(prefix=prefix, auto_id='editor-%s', initial={
                    'title': 'Początek', 'description': 'Opis początkowy',
                    'visibility': 'private', 'revision': 7,
                })
                payload = form_payload(form)
                fields = {field['field_name']: field for field in payload['fields']}

                self.assertFalse(payload['bound'])
                self.assertEqual(list(fields), list(form.fields))
                for name, field in fields.items():
                    self.assertEqual(field['name'], f'{prefix}-{name}')
                    self.assertEqual(field['id'], f'editor-{prefix}-{name}')
                    self.assertEqual(field['errors'], [])
                self.assertEqual(fields['title']['value'], 'Początek')
                self.assertEqual(fields['description']['value'], 'Opis początkowy')
                self.assertEqual(fields['visibility']['value'], ['private'])
                self.assertEqual(fields['revision']['value'], '7')
                self.assertTrue(fields['revision']['hidden'])

    def test_bound_invalid_schema_keeps_prefixed_names_ids_and_draft(self):
        form = PayloadForm({
            'subtask-title': 'Za długi tytuł',
            'subtask-description': 'Niezapisany opis',
            'subtask-visibility': 'public',
            'subtask-revision': '9',
        }, prefix='subtask')
        self.assertFalse(form.is_valid())

        payload = form_payload(form)
        fields = {field['field_name']: field for field in payload['fields']}

        self.assertTrue(payload['bound'])
        for name, field in fields.items():
            self.assertEqual(field['name'], f'subtask-{name}')
            self.assertEqual(field['id'], f'id_subtask-{name}')
        self.assertEqual(fields['title']['value'], 'Za długi tytuł')
        self.assertEqual(fields['title']['errors'], list(form['title'].errors))
        self.assertTrue(fields['title']['errors'])
        self.assertEqual(fields['description']['value'], 'Niezapisany opis')
        self.assertEqual(fields['description']['errors'], [])
        self.assertEqual(fields['visibility']['value'], ['public'])
        self.assertEqual(fields['revision']['value'], '9')
        self.assertTrue(fields['revision']['hidden'])
