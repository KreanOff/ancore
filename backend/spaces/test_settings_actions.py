"""Settings directory actions reuse Space ACL and delete only confirmed spaces."""
import tempfile
from datetime import date
from unittest.mock import patch
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.test import Client, TestCase
from django.urls import reverse

from dashboard.models import Dashboard, DashboardGadget
from tasks.models import TaskTag
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .forms import SpaceDeleteForm
from .models import Space, SpaceConfiguration, SpaceMembership, SpaceTask, SpaceTaskFile, Sprint, Team, WorkItem
from .testing import make_space, make_task


class SpaceSettingsActionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='space-action-owner', email='space-action-owner@example.test')
        cls.member = users.objects.create_user(username='space-action-member', email='space-action-member@example.test')
        cls.guest = users.objects.create_user(username='space-action-guest', email='space-action-guest@example.test')
        cls.other = users.objects.create_user(username='space-action-other', email='space-action-other@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Workspace działań')
        cls.foreign = create_workplace_for_user(cls.other, 'Obcy Workspace działań')
        cls.member_access = WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.guest, role='guest')
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Przestrzeń do usunięcia', visibility='public')
        cls.managed = make_space(user=cls.owner, workplace=cls.workspace, name='Przestrzeń członka', responsible_user=cls.member)
        cls.private = make_space(user=cls.owner, workplace=cls.workspace, name='Prywatna przestrzeń', visibility='private', private_owner=cls.owner)
        SpaceMembership.objects.create(space=cls.private, user=cls.member, role='admin')
        SpaceMembership.objects.create(space=cls.private, user=cls.guest, role='admin')
        cls.hidden = make_space(user=cls.owner, workplace=cls.workspace, name='Ukryta przestrzeń', visibility='private', private_owner=cls.owner)
        cls.foreign_space = make_space(user=cls.other, workplace=cls.foreign, name='Obca przestrzeń')

    def setUp(self):
        self.client.force_login(self.owner)
        self.activate(self.client)

    def activate(self, client):
        session = client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def path(self, space=None, scoped=True):
        suffix = (space or self.space).slug + '/delete/'
        return scoped_workplace_app_path(self.workspace, 'space', suffix) if scoped else '/space/' + suffix

    def api(self, target, values=None, scoped=True, client=None):
        endpoint = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') if scoped else '/api/v1/page/'
        url = endpoint + '?' + urlencode({'url': target})
        client = client or self.client
        return client.get(url) if values is None else client.post(url, values)

    def test_delete_get_is_compact_confirmation_and_never_mutates(self):
        for scoped in (False, True):
            response = self.api(self.path(scoped=scoped), scoped=scoped)
            self.assertEqual(response.status_code, 200)
            data = response.json()['data']
            self.assertEqual(response.json()['type'], 'form')
            self.assertEqual(data['title'], 'Usuń przestrzeń')
            self.assertEqual(data['return_url'], reverse('settings') + '?section=spaces')
            self.assertTrue(data['form']['compact'])
            self.assertEqual(data['form']['submit_label'], 'Usuń przestrzeń')
            field = data['form']['fields'][0]
            self.assertEqual(field['name'], 'name')
            self.assertIn(self.space.name, field['help_text'])
            self.assertIn('zadania', data['form']['confirmation_message'])
            self.assertIn(self.space.name, data['form']['confirmation_message'])
            self.assertIn('nie można cofnąć', data['form']['confirmation_message'])
            self.assertTrue(Space.objects.filter(pk=self.space.pk).exists())

    def test_delete_requires_exact_current_name_and_rejects_a_stale_name(self):
        response = self.api(self.path(), {'name': 'Nieprawidłowa nazwa'})
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.json()['data']['form']['fields'][0]['errors'])
        old_name = self.space.name
        self.space.name = 'Nowa nazwa'
        self.space.save(update_fields=['name'])
        self.assertEqual(self.api(self.path(), {'name': old_name}).status_code, 400)
        self.assertTrue(Space.objects.filter(pk=self.space.pk).exists())
        self.assertEqual(self.api(self.path(), {'name': self.space.name}).json()['redirect'], reverse('settings') + '?section=spaces')
        self.assertFalse(Space.objects.filter(pk=self.space.pk).exists())

    def test_native_and_api_deletion_work_for_plain_and_scoped_urls(self):
        for scoped in (False, True):
            space = make_space(user=self.owner, workplace=self.workspace, name=f'Usuwana {scoped}')
            target = self.path(space, scoped=scoped)
            if scoped:
                response = self.api(target, {'name': space.name}, scoped=scoped)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['redirect'], reverse('settings') + '?section=spaces')
            else:
                response = self.client.post(target, {'name': space.name})
                self.assertRedirects(response, reverse('settings') + '?section=spaces')
            self.assertFalse(Space.objects.filter(pk=space.pk).exists())
        self.assertEqual(self.client.session['active_workplace_id'], self.workspace.pk)

    def test_delete_cascades_content_but_preserves_other_spaces_configuration_teams_and_dashboards(self):
        configuration = self.space.configuration
        configuration.shared = True
        configuration.save(update_fields=['shared'])
        sibling = make_space(user=self.owner, workplace=self.workspace, name='Wspólna konfiguracja', configuration=configuration)
        task = make_task(user=self.owner, workplace=self.workspace, space=self.space, title='Zadanie')
        child = make_task(user=self.owner, workplace=self.workspace, space=self.space, title='Podzadanie', parent=task)
        preserved_task = make_task(user=self.owner, workplace=self.workspace, space=sibling, title='Pozostawione')
        sprint = Sprint.objects.create(space=self.space, name='Sprint', start_on=date(2026, 11, 1), end_on=date(2026, 11, 14))
        tag = TaskTag.objects.create(space=self.space, user=self.owner, workplace=self.workspace, name='Tag')
        grant = SpaceMembership.objects.create(space=self.space, user=self.member)
        team = Team.objects.create(owner=self.owner, workplace=self.workspace, created_by=self.owner, name='Zespół')
        team.spaces.add(self.space, sibling)
        dashboard = Dashboard.objects.create(owner=self.owner, workplace=self.workspace, created_by=self.owner, name='Pulpit')
        dashboard.scope_spaces.add(self.space, sibling)
        gadget = DashboardGadget.objects.create(dashboard=dashboard, space=self.space)
        response = self.api(self.path(), {'name': self.space.name})
        self.assertEqual(response.status_code, 200)
        for model, pk in ((Space, self.space.pk), (SpaceTask, task.pk), (SpaceTask, child.pk), (Sprint, sprint.pk), (TaskTag, tag.pk), (SpaceMembership, grant.pk), (DashboardGadget, gadget.pk)):
            self.assertFalse(model.objects.filter(pk=pk).exists())
        self.assertFalse(WorkItem.objects.filter(space_id=self.space.pk).exists())
        self.assertTrue(SpaceConfiguration.objects.filter(pk=configuration.pk).exists())
        self.assertTrue(SpaceTask.objects.filter(pk=preserved_task.pk).exists())
        self.assertEqual(list(team.spaces.values_list('pk', flat=True)), [sibling.pk])
        self.assertEqual(list(dashboard.scope_spaces.values_list('pk', flat=True)), [sibling.pk])
        self.assertTrue(WorkplaceMembership.objects.filter(pk=self.member_access.pk).exists())

    def test_delete_uses_existing_file_cleanup_only_after_commit(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        storage = FileSystemStorage(directory.name)
        for model, field_name in ((Space, 'avatar_photo'), (SpaceTaskFile, 'file')):
            field = model._meta.get_field(field_name)
            self.addCleanup(setattr, field, 'storage', field.storage)
            field.storage = storage
        self.space.avatar_photo.save('avatar.png', ContentFile(b'avatar'))
        task = make_task(user=self.owner, workplace=self.workspace, space=self.space, title='Z plikiem')
        attachment = SpaceTaskFile(task=task, filename='attachment.txt')
        attachment.file.save('attachment.txt', ContentFile(b'attachment'))
        names = [self.space.avatar_photo.name, attachment.file.name]
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.api(self.path(), {'name': self.space.name}).status_code, 200)
            self.assertTrue(all(storage.exists(name) for name in names))
        self.assertFalse(any(storage.exists(name) for name in names))

    def test_member_can_manage_own_public_space_or_private_admin_space_only(self):
        self.client.force_login(self.member)
        self.activate(self.client)
        for space in (self.managed, self.private):
            self.assertEqual(self.api(self.path(space)).status_code, 200)
        for space, status in ((self.space, 403), (self.hidden, 404), (self.foreign_space, 404)):
            self.assertEqual(self.api(self.path(space)).status_code, status)
            self.assertEqual(self.api(self.path(space), {'name': space.name}).status_code, status)
            self.assertTrue(Space.objects.filter(pk=space.pk).exists())
        self.assertEqual(self.api(self.path(self.private), {'name': self.private.name}).status_code, 200)
        self.assertFalse(Space.objects.filter(pk=self.private.pk).exists())

    def test_guest_private_admin_cannot_open_or_submit_delete(self):
        self.client.force_login(self.guest)
        self.activate(self.client)
        for scoped in (False, True):
            target = self.path(self.private, scoped=scoped)
            self.assertEqual(self.client.get(target).status_code, 403)
            self.assertEqual(self.api(target, scoped=scoped).status_code, 403)
            self.assertEqual(self.api(target, {'name': self.private.name}, scoped=scoped).status_code, 403)
        self.assertTrue(Space.objects.filter(pk=self.private.pk).exists())

    def test_disabled_module_revoked_membership_and_csrf_deny_delete(self):
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.owner)
        self.activate(csrf)
        self.assertEqual(csrf.post(self.path(), {'name': self.space.name}).status_code, 403)
        self.assertEqual(self.api(self.path(), {'name': self.space.name}, client=csrf).status_code, 403)
        self.workspace.disabled_modules = ['spaces']
        self.workspace.save(update_fields=['disabled_modules'])
        self.assertEqual(self.client.get(self.path()).status_code, 404)
        self.assertEqual(self.api(self.path(), {'name': self.space.name}).status_code, 404)
        self.workspace.disabled_modules = []
        self.workspace.save(update_fields=['disabled_modules'])
        self.client.force_login(self.member)
        self.activate(self.client)
        self.member_access.delete()
        self.assertEqual(self.api(self.path(self.managed), {'name': self.managed.name}).status_code, 403)
        self.assertTrue(Space.objects.filter(pk=self.managed.pk).exists())

    def test_name_and_management_permission_are_rechecked_after_form_validation(self):
        real_validation = SpaceDeleteForm.is_valid

        def rename_after_validation(form):
            valid = real_validation(form)
            Space.objects.filter(pk=self.space.pk).update(name='Nazwa zmieniona w międzyczasie')
            return valid

        with patch.object(SpaceDeleteForm, 'is_valid', rename_after_validation):
            self.assertEqual(self.api(self.path(), {'name': self.space.name}).status_code, 400)
        self.assertTrue(Space.objects.filter(pk=self.space.pk).exists())
        self.client.force_login(self.member)
        self.activate(self.client)

        def revoke_after_validation(form):
            valid = real_validation(form)
            Space.objects.filter(pk=self.managed.pk).update(responsible_user=self.owner)
            return valid

        with patch.object(SpaceDeleteForm, 'is_valid', revoke_after_validation):
            self.assertEqual(self.api(self.path(self.managed), {'name': self.managed.name}).status_code, 403)
        self.assertTrue(Space.objects.filter(pk=self.managed.pk).exists())

    def test_create_from_settings_reuses_templates_and_returns_to_new_settings(self):
        self.client.force_login(self.member)
        self.activate(self.client)
        for scoped in (False, True):
            target = (scoped_workplace_app_path(self.workspace, 'spaces', 'create/') if scoped else '/spaces/create/') + '?return_to=settings'
            response = self.api(target, scoped=scoped)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['data']['return_url'], reverse('settings') + '?section=spaces')
            self.assertTrue(response.json()['data']['form']['templates'])
            payload = {'name': f'Nowa z ustawień {scoped}', 'key': 'NOWA' + str(int(scoped)), 'description': 'Opis', 'kind': 'business', 'template': 'tasks', 'management': 'team', 'visibility': 'private'}
            invalid = self.api(target, {**payload, 'name': ''}, scoped=scoped)
            self.assertEqual(invalid.status_code, 400)
            response = self.api(target, payload, scoped=scoped)
            self.assertEqual(response.status_code, 200)
            space = Space.objects.get(key=payload['key'], workplace=self.workspace)
            self.assertEqual(space.private_owner, self.member)
            self.assertEqual(space.responsible_user, self.member)
            self.assertEqual(response.json()['redirect'], scoped_workplace_app_path(self.workspace, 'space', space.slug + '/?view=settings'))

    def test_actions_payload_hides_unavailable_operations_and_ssr_keeps_toolbar_order(self):
        target = reverse('settings') + '?section=spaces'
        self.client.force_login(self.member)
        self.activate(self.client)
        data = self.api(target).json()['data']
        self.assertTrue(data['create_url'].endswith('/spaces/create/?return_to=settings'))
        rows = {row['id']: row for row in data['spaces']}
        self.assertTrue(rows[self.managed.pk]['can_manage'])
        self.assertEqual(rows[self.managed.pk]['edit_url'], rows[self.managed.pk]['url'])
        self.assertEqual(rows[self.managed.pk]['delete_url'], self.path(self.managed))
        self.assertFalse(rows[self.space.pk]['can_manage'])
        self.assertEqual(rows[self.space.pk]['edit_url'], '')
        self.assertEqual(rows[self.space.pk]['delete_url'], '')
        response = self.client.get(target)
        html = response.content.decode()
        positions = [html.index(hook) for hook in ('data-settings-spaces-create', 'data-settings-spaces-search', 'data-settings-spaces-edit', 'data-settings-spaces-delete')]
        self.assertEqual(positions, sorted(positions))
        self.client.force_login(self.guest)
        self.activate(self.client)
        data = self.api(target).json()['data']
        self.assertEqual(data['create_url'], '')
        self.assertTrue(all(not row['can_manage'] and not row['edit_url'] and not row['delete_url'] for row in data['spaces']))
        self.assertContains(self.client.get(target), 'disabled data-settings-spaces-create')

    def test_native_confirmation_message_is_visible_before_the_name_field(self):
        response = self.client.get(self.path())
        self.assertEqual(response.status_code, 200)
        message = SpaceDeleteForm(space=self.space).confirmation_message
        self.assertContains(response, '<p class="resources-form-wide app-form-wide">' + message + '</p>', html=True)
