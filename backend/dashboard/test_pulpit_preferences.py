from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import TestCase

from spaces.models import SpaceTask
from spaces.testing import make_space
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import Dashboard, DashboardGadget, SavedTaskFilter


class DashboardPreferencesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='preferences-owner', email='owner@example.test')
        cls.viewer = users.objects.create_user(username='preferences-viewer', email='viewer@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Pulpity z parametrami')
        cls.other = create_workplace_for_user(cls.owner, 'Obcy Workspace')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.viewer)
        cls.first = make_space(user=cls.owner, workplace=cls.workspace, name='Produkt', key='PRO')
        cls.second = make_space(user=cls.owner, workplace=cls.workspace, name='Marketing', key='MAR')
        cls.private = make_space(user=cls.owner, workplace=cls.workspace, name='Poufna Przestrzeń', key='SEC',
                                 visibility='private', private_owner=cls.owner)
        cls.foreign = make_space(user=cls.owner, workplace=cls.other, name='Obca', key='OTH')
        SpaceTask.objects.create(space=cls.first, title='Otwarte', created_by=cls.owner)
        SpaceTask.objects.create(space=cls.first, title='Zamknięte', status='closed', created_by=cls.owner)
        SpaceTask.objects.create(space=cls.second, title='Marketing', created_by=cls.owner)
        SpaceTask.objects.create(space=cls.private, title='Poufne', created_by=cls.owner)
        cls.source = SavedTaskFilter.objects.create(owner=cls.owner, workplace=cls.workspace, created_by=cls.owner,
                                                   name='Zamknięte z filtra', query='status = closed', visibility='workspace')
        cls.foreign_filter = SavedTaskFilter.objects.create(owner=cls.owner, workplace=cls.other, created_by=cls.owner,
                                                           name='Obcy filtr', query='')
        cls.dashboard = Dashboard.objects.create(owner=cls.owner, workplace=cls.workspace, created_by=cls.owner,
                                                name='Plan', visibility='workspace')
        cls.gadget = DashboardGadget.objects.create(dashboard=cls.dashboard, kind='progress')

    def setUp(self):
        self.login(self.owner)

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def path(self, suffix=''):
        return scoped_workplace_app_path(self.workspace, 'dashboards', self.dashboard.slug + '/' + suffix)

    def endpoint(self, path):
        return scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') + '?' + urlencode({'url': path})

    def get(self, suffix=''):
        return self.client.get(self.endpoint(self.path(suffix))).json()['data']

    def save(self, **changes):
        data = {'name': 'Plan', 'description': '', 'icon': 'users', 'data_scope': 'workspace', 'refresh_interval': 60}
        return self.client.post(self.endpoint(self.path('edit/')), {**data, **changes})

    def card(self):
        return self.get()['columns'][0][0]

    def test_settings_save_and_serialization_preserve_layout_and_access(self):
        response = self.save(data_scope='spaces', scope_spaces=[self.first.pk], refresh_interval=300)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['form']['bound'])
        self.assertFalse(any(field['errors'] for field in response.json()['form']['fields']))
        self.assertEqual(next(field['value'] for field in response.json()['form']['fields'] if field['name'] == 'scope_spaces'), [str(self.first.pk)])
        item = Dashboard.objects.get(pk=self.dashboard.pk)
        self.assertEqual((item.icon, item.data_scope, item.refresh_interval, item.revision), ('users', 'spaces', 300, 1))
        self.assertEqual((item.layout, item.visibility, item.created_by_id), ('equal', 'workspace', self.owner.pk))
        self.assertEqual(list(item.scope_spaces.all()), [self.first])
        self.assertEqual(self.get()['dashboard']['refresh_interval'], 300)
        self.assertEqual(self.get()['dashboard']['icon'], 'users')
        self.assertEqual(self.get()['dashboard']['emoji'], '👥')
        fields = {field['name']: field for field in self.get('edit/')['form']['fields']}
        self.assertEqual(fields['icon']['type'], 'emoji')
        self.assertNotIn('choices', fields['icon'])
        self.assertEqual(fields['icon']['emoji_picker']['selected']['value'], '👥')
        self.assertIn('/static/vendor/fluent-emoji/', fields['icon']['emoji_picker']['catalog_url'])
        self.assertEqual(fields['icon']['emoji_picker']['selected']['art'], self.get()['dashboard']['emoji_art'])

    def test_new_emoji_variants_save_in_existing_field_and_keep_legacy_choices(self):
        for value in ('🚀', '👩🏽\u200d💻', 'star', 'layout-dashboard'):
            with self.subTest(value=value):
                self.assertEqual(self.save(icon=value).status_code, 200)
                self.dashboard.refresh_from_db()
                self.assertEqual(self.dashboard.icon, value)
                field = next(field for field in self.get('edit/')['form']['fields'] if field['name'] == 'icon')
                self.assertEqual(field['value'], value)
                art = self.get()['dashboard']['emoji_art']
                if value == 'layout-dashboard':
                    self.assertEqual(art, {'icon': 'layout-dashboard'})
                    self.assertEqual(field['emoji_picker']['selected'], field['emoji_picker']['default'])
                else:
                    self.assertIn('/static/vendor/fluent-emoji/sheet-', art['url'])

    def test_sources_and_choices_are_validated_in_plain_and_scoped_routes(self):
        for path in (self.path('edit/'), f'/dashboards/{self.dashboard.slug}/edit/'):
            for values in ({'icon': 'nonexistent'}, {'icon': 'https://example.test/a.svg'}, {'icon': '<script>x</script>'},
                           {'refresh_interval': 1}, {'data_scope': 'invalid'},
                           {'data_scope': 'spaces'}, {'data_scope': 'filter'},
                           {'data_scope': 'spaces', 'scope_spaces': [self.foreign.pk]},
                           {'data_scope': 'filter', 'scope_filter': self.foreign_filter.pk}):
                with self.subTest(path=path, values=values):
                    payload = {'name': 'Plan', 'data_scope': 'workspace', 'refresh_interval': 0, **values}
                    self.assertEqual(self.client.post(self.endpoint(path), payload).status_code, 400)
        self.dashboard.refresh_from_db()
        self.assertEqual(self.dashboard.revision, 0)

    def test_settings_choices_exclude_inaccessible_sources(self):
        self.dashboard.created_by = self.viewer
        self.dashboard.save()
        self.source.visibility = 'private'
        self.source.save()
        self.login(self.viewer)
        fields = {field['name']: field for field in self.get('edit/')['form']['fields']}
        self.assertEqual({row['value'] for row in fields['scope_spaces']['choices']}, {str(self.first.pk), str(self.second.pk)})
        self.assertEqual([row['value'] for row in fields['scope_filter']['choices']], [''])

    def test_space_defaults_and_explicit_gadget_override(self):
        self.save(data_scope='spaces', scope_spaces=[self.first.pk])
        self.assertEqual((self.card()['count'], self.card()['closed_count']), (2, 1))
        self.gadget.space = self.second
        self.gadget.save()
        self.assertEqual(self.card()['count'], 1)
        self.assertIn(self.second.name, self.card()['caption'])

    def test_saved_filter_uses_existing_query_compiler_and_gadget_assignment(self):
        self.assertEqual(self.save(data_scope='filter', scope_filter=self.source.pk).status_code, 200)
        self.assertEqual((self.card()['count'], self.card()['percent']), (1, 100))
        self.gadget.assignee = 'me'
        self.gadget.save()
        self.assertEqual(self.card()['count'], 0)

    def test_shared_scope_rechecks_viewer_access_and_never_exposes_private_names(self):
        self.save(data_scope='spaces', scope_spaces=[self.first.pk, self.private.pk])
        self.assertEqual(self.card()['count'], 3)
        self.login(self.viewer)
        self.assertEqual(self.card()['count'], 2)
        self.dashboard.scope_spaces.set([self.private])
        card = self.card()
        self.assertTrue(card['unavailable'])
        self.assertNotIn('caption', card)
        self.assertNotIn('count', card)
        self.assertNotIn(self.private.name, str(self.get()))

    def test_revoked_deleted_and_invalid_filters_do_not_fall_back_to_workspace(self):
        self.save(data_scope='filter', scope_filter=self.source.pk)
        self.source.visibility = 'private'
        self.source.save()
        self.login(self.viewer)
        self.assertTrue(self.card()['unavailable'])
        self.assertNotIn(self.source.name, str(self.get()))
        self.login(self.owner)
        self.source.query = 'invalid query !!!'
        self.source.save()
        self.assertTrue(self.card()['unavailable'])
        self.source.delete()
        self.assertTrue(self.card()['unavailable'])
        self.dashboard.refresh_from_db()
        self.assertIsNone(self.dashboard.scope_filter)
        self.assertEqual(self.dashboard.data_scope, 'filter')

    def test_deleted_space_selection_does_not_widen_scope(self):
        self.save(data_scope='spaces', scope_spaces=[self.second.pk])
        self.second.delete()
        self.assertTrue(self.card()['unavailable'])

    def test_switching_modes_clears_unused_relations_and_legacy_post_preserves_preferences(self):
        self.save(data_scope='spaces', scope_spaces=[self.first.pk])
        result = self.client.post(self.endpoint(self.path('edit/')), {'name': 'Nowa nazwa', 'description': 'Opis'})
        self.assertEqual(result.status_code, 200)
        self.dashboard.refresh_from_db()
        self.assertEqual((self.dashboard.icon, self.dashboard.refresh_interval, self.dashboard.data_scope), ('users', 60, 'spaces'))
        self.assertEqual(list(self.dashboard.scope_spaces.all()), [self.first])
        self.save(data_scope='filter', scope_filter=self.source.pk)
        self.assertFalse(self.dashboard.scope_spaces.exists())
        self.save()
        self.dashboard.refresh_from_db()
        self.assertIsNone(self.dashboard.scope_filter)

    def test_quick_add_uses_the_same_scope_and_non_creators_cannot_edit_preferences(self):
        self.save(data_scope='filter', scope_filter=self.source.pk)
        self.dashboard.refresh_from_db()
        result = self.client.post(self.endpoint(self.path('gadgets/quick-add/')),
                                  {'kind': 'progress', 'revision': self.dashboard.revision}, content_type='application/json')
        self.assertEqual(result.status_code, 200)
        self.assertEqual((result.json()['gadget']['count'], result.json()['gadget']['percent']), (1, 100))
        self.login(self.viewer)
        self.assertEqual(self.save().status_code, 403)
