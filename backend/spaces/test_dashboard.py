"""Personal dashboard persistence preserves Space and Workspace boundaries."""
from copy import deepcopy
import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from .dashboard import default_widgets
from .models import SpaceDashboardLayout, SpaceMembership
from .testing import make_space
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class SpaceDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='layout-owner', email='layout-owner@example.test')
        cls.member = users.objects.create_user(username='layout-member', email='layout-member@example.test')
        cls.outsider = users.objects.create_user(username='layout-outsider', email='layout-outsider@example.test')
        cls.guest = users.objects.create_user(username='layout-guest', email='layout-guest@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Pulpity Przestrzeni')
        cls.other_workspace = create_workplace_for_user(cls.owner, 'Inny Workspace')
        for user, role in ((cls.member, 'member'), (cls.outsider, 'member'), (cls.guest, 'guest')):
            WorkplaceMembership.objects.create(workplace=cls.workspace, user=user, role=role)
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Prywatna',
                               visibility='private', private_owner=cls.owner, kind='software', template='scrum')
        cls.second_space = make_space(user=cls.owner, workplace=cls.workspace, name='Publiczna')
        cls.foreign_space = make_space(user=cls.owner, workplace=cls.other_workspace, name='Obca')
        SpaceMembership.objects.create(space=cls.space, user=cls.member, role='observer')
        SpaceMembership.objects.create(space=cls.space, user=cls.guest, role='observer')

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def target(self, space=None, scoped=True, numeric=False, suffix=''):
        space = space or self.space
        app, key = ('spaces', str(space.pk)) if numeric else ('space', space.slug)
        if scoped:
            return scoped_workplace_app_path(self.workspace, app, key + '/' + suffix)
        return f'/{app}/{key}/{suffix}'

    def api(self, scoped=True):
        return scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') if scoped else '/api/v1/page/'

    def page(self, space=None, scoped=True, numeric=False):
        response = self.client.get(self.api(scoped), {'url': self.target(space, scoped, numeric)})
        if response.status_code == 200 and response.json().get('redirect'):
            response = self.client.get(self.api(scoped), {'url': response.json()['redirect']})
        return response

    def save(self, widgets=None, revision=0, space=None, scoped=True, numeric=False, direct=False, **extra):
        target = self.target(space, scoped, numeric, 'dashboard/layout/')
        url = target if direct else self.api(scoped) + '?url=' + target
        payload = {'revision': revision, 'widgets': default_widgets(space or self.space) if widgets is None else widgets, **extra}
        return self.client.post(url, json.dumps(payload), content_type='application/json')

    def test_first_read_exposes_defaults_without_creating_or_resetting_preferences(self):
        for scoped in (False, True):
            for numeric in (False, True):
                with self.subTest(scoped=scoped, numeric=numeric):
                    response = self.page(scoped=scoped, numeric=numeric)
                    self.assertEqual(response.status_code, 200)
                    dashboard = response.json()['data']['summary']['dashboard']
                    self.assertEqual(dashboard['widgets'], default_widgets(self.space))
                    self.assertEqual(dashboard['revision'], 0)
                    self.assertEqual(dashboard['columns'], 12)
                    self.assertEqual(len(dashboard['catalog']), 10)
                    self.assertIn(f'/space/{self.space.slug}/dashboard/layout/', dashboard['save_url'])
        self.assertFalse(SpaceDashboardLayout.objects.exists())
        self.assertEqual(self.save(widgets=[]).status_code, 200)
        for _ in range(2):
            dashboard = self.page().json()['data']['summary']['dashboard']
            self.assertEqual(dashboard['widgets'], [])
            self.assertEqual(dashboard['revision'], 1)

    def test_observer_can_add_move_resize_and_remove_personal_widgets(self):
        widgets = [{'id': 'statuses', 'x': 0, 'y': 0, 'w': 8, 'h': 7},
                   {'id': 'completed', 'x': 8, 'y': 2, 'w': 4, 'h': 3}]
        saved = self.save(widgets)
        self.assertEqual(saved.status_code, 200)
        self.assertTrue(saved.json()['saved'])
        self.assertEqual(saved.json()['revision'], 1)
        self.assertEqual(saved.json()['dashboard']['widgets'], widgets)
        self.assertEqual(self.page().json()['data']['summary']['dashboard']['widgets'], widgets)
        changed = [{'id': 'activity', 'x': 4, 'y': 7, 'w': 8, 'h': 10}]
        self.assertEqual(self.save(changed, revision=1).status_code, 200)
        layout = SpaceDashboardLayout.objects.get(space=self.space, user=self.member)
        self.assertEqual((layout.widgets, layout.revision), (changed, 2))

    def test_first_html_render_uses_saved_widget_selection_geometry_and_empty_state(self):
        widgets = [{'id': 'completed', 'x': 8, 'y': 3, 'w': 4, 'h': 2},
                   {'id': 'statuses', 'x': 0, 'y': 5, 'w': 8, 'h': 7}]
        self.assertEqual(self.save(widgets).status_code, 200)
        response = self.client.get(self.target())
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-summary-widget="completed"')
        self.assertContains(response, 'data-summary-widget="statuses"')
        self.assertContains(response, 'grid-column: 9 / span 4; grid-row: 4 / span 2')
        self.assertContains(response, 'grid-column: 1 / span 8; grid-row: 6 / span 7')
        self.assertNotContains(response, 'data-summary-widget="activity"')
        self.assertNotContains(response, '<h2>Ostatnia aktywność</h2>')
        self.assertNotContains(response, '<h2>Podział priorytetów</h2>')
        self.assertEqual(self.save([], revision=1).status_code, 200)
        empty = self.client.get(self.target())
        self.assertContains(empty, 'Ten pulpit jest pusty.')
        self.assertNotContains(empty, 'data-summary-widget=')
        self.assertNotContains(empty, '<h2>Przegląd statusów</h2>')

    def test_layouts_are_independent_per_person_and_space(self):
        self.assertEqual(self.save(widgets=[]).status_code, 200)
        self.assertEqual(self.save(widgets=[], space=self.second_space).status_code, 200)
        self.client.force_login(self.owner)
        self.assertEqual(self.page().json()['data']['summary']['dashboard']['revision'], 0)
        self.assertEqual(self.save(user=self.member.pk, space_id=self.second_space.pk).status_code, 200)
        self.assertEqual(SpaceDashboardLayout.objects.get(space=self.space, user=self.member).widgets, [])
        self.assertEqual(SpaceDashboardLayout.objects.get(space=self.space, user=self.owner).widgets, default_widgets(self.space))
        self.assertEqual(SpaceDashboardLayout.objects.filter(user=self.member).count(), 2)

    def test_stale_revision_cannot_overwrite_the_latest_saved_layout(self):
        self.assertEqual(self.save().status_code, 200)
        conflict = self.save(widgets=[], revision=0)
        self.assertEqual(conflict.status_code, 409)
        self.assertIn('innym oknie', conflict.json()['error'])
        layout = SpaceDashboardLayout.objects.get(space=self.space, user=self.member)
        self.assertEqual((layout.revision, layout.widgets), (1, default_widgets(self.space)))
        # A client cannot invent a first revision to initialize another Space.
        self.assertEqual(self.save(widgets=[], revision=1, space=self.second_space).status_code, 409)
        self.assertFalse(SpaceDashboardLayout.objects.filter(space=self.second_space).exists())

    def test_invalid_geometry_and_ids_do_not_change_existing_layout(self):
        self.assertEqual(self.save().status_code, 200)
        valid = [{'id': 'statuses', 'x': 0, 'y': 0, 'w': 6, 'h': 6}]
        malformed = [None, {}, 'widgets', [None], [{}], valid * 2, valid + [{'id': 'activity', 'x': 3, 'y': 3, 'w': 6, 'h': 6}]]
        for key, value in [('id', 'unknown'), ('id', ['statuses']), ('x', -1), ('x', 7), ('x', True),
                           ('y', 200), ('y', -1), ('w', 3), ('w', 13), ('h', 4), ('h', 17), ('h', 5.5)]:
            row = deepcopy(valid[0])
            row[key] = value
            malformed.append([row])
        malformed.append([{**valid[0], 'extra': 'unexpected'}])
        malformed.append([{**valid[0], 'y': 199}])
        for widgets in malformed:
            with self.subTest(widgets=widgets):
                response = self.client.post(self.api() + '?url=' + self.target(suffix='dashboard/layout/'),
                                            json.dumps({'revision': 1, 'widgets': widgets}), content_type='application/json')
                self.assertEqual(response.status_code, 400)
        for revision in (-1, True, '1', None):
            self.assertEqual(self.save(widgets=[], revision=revision).status_code, 400)
        layout = SpaceDashboardLayout.objects.get(space=self.space, user=self.member)
        self.assertEqual((layout.revision, layout.widgets), (1, default_widgets(self.space)))

    def test_invalid_json_and_wrong_method_do_not_create_layout(self):
        target = self.target(suffix='dashboard/layout/')
        for body in ('{', '[]', 'null', '{"revision":0}', '\ud800'):
            with self.subTest(body=repr(body)):
                response = self.client.post(self.api() + '?url=' + target, body.encode('utf-8', errors='surrogatepass'), content_type='application/json')
                self.assertEqual(response.status_code, 400)
        self.assertEqual(self.client.post(target, {'revision': 0, 'widgets': []}).status_code, 400)
        self.assertEqual(self.client.get(target).status_code, 405)
        self.assertFalse(SpaceDashboardLayout.objects.exists())

    def test_plain_scoped_and_numeric_writes_use_the_same_personal_record(self):
        revision = 0
        for scoped in (False, True):
            for numeric in (False, True):
                for direct in (False, True):
                    with self.subTest(scoped=scoped, numeric=numeric, direct=direct):
                        saved = self.save(widgets=[], revision=revision, scoped=scoped, numeric=numeric, direct=direct)
                        self.assertEqual(saved.status_code, 200)
                        revision += 1
                        self.assertEqual(saved.json()['revision'], revision)
        self.assertEqual(SpaceDashboardLayout.objects.count(), 1)

    def test_epics_are_available_only_for_software_spaces(self):
        dashboard = self.page(self.second_space).json()['data']['summary']['dashboard']
        self.assertNotIn('epics', {row['id'] for row in dashboard['catalog']})
        self.assertEqual(next(row['w'] for row in dashboard['widgets'] if row['id'] == 'workload'), 12)
        epics = [{'id': 'epics', 'x': 0, 'y': 0, 'w': 6, 'h': 6}]
        self.assertEqual(self.save(widgets=epics, space=self.second_space).status_code, 400)
        self.assertEqual(self.save(widgets=epics).status_code, 200)
        self.space.kind = 'business'
        self.space.save(update_fields=['kind'])
        dashboard = self.page().json()['data']['summary']['dashboard']
        self.assertEqual(dashboard['widgets'], [])
        self.assertEqual(dashboard['revision'], 1)

    def test_private_other_workspace_and_revoked_access_cannot_read_or_write(self):
        self.assertEqual(self.save(widgets=[]).status_code, 200)
        self.assertEqual(self.save(space=self.foreign_space).status_code, 404)
        self.assertEqual(self.page(self.foreign_space).status_code, 404)
        self.client.force_login(self.outsider)
        self.assertEqual(self.page().status_code, 404)
        self.assertEqual(self.save().status_code, 404)
        self.client.force_login(self.member)
        SpaceMembership.objects.filter(space=self.space, user=self.member).delete()
        self.assertEqual(self.page().status_code, 404)
        self.assertEqual(self.save(revision=1).status_code, 404)
        self.assertEqual(SpaceDashboardLayout.objects.get(space=self.space, user=self.member).revision, 1)

    def test_guest_disabled_module_and_unauthenticated_sessions_cannot_write(self):
        self.client.force_login(self.guest)
        dashboard = self.page().json()['data']['summary']['dashboard']
        self.assertEqual(dashboard['save_url'], '')
        for direct in (False, True):
            self.assertEqual(self.save(direct=direct).status_code, 403)
        self.client.force_login(self.member)
        self.workspace.disabled_modules = ['spaces']
        self.workspace.save(update_fields=['disabled_modules'])
        self.assertEqual(self.page().status_code, 404)
        self.assertEqual(self.save().status_code, 404)
        self.workspace.disabled_modules = []
        self.workspace.save(update_fields=['disabled_modules'])
        self.client.logout()
        self.assertEqual(self.save().status_code, 401)
        self.assertFalse(SpaceDashboardLayout.objects.exists())

    def test_csrf_is_required_for_the_delegated_and_direct_save(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.member)
        for url in (self.target(suffix='dashboard/layout/'), self.api() + '?url=' + self.target(suffix='dashboard/layout/')):
            self.assertEqual(client.post(url, json.dumps({'revision': 0, 'widgets': []}), content_type='application/json').status_code, 403)
        self.assertFalse(SpaceDashboardLayout.objects.exists())
