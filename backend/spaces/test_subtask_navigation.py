"""Subtasks are edited from their root task without exposing a full detail page."""
import json
from urllib.parse import parse_qs, urlencode, urlsplit

from django.test import TestCase

from workplaces.models import create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from . import test_independent_tasks as fixtures
from .models import SpaceTask, SpaceTaskMembership


class SubtaskNavigationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.IndependentTaskTests.setUpTestData.__func__(cls)
        cls.child = SpaceTask.objects.create(space=cls.space, parent=cls.task, title='Podzadanie', created_by=cls.owner)
        cls.nested = SpaceTask.objects.create(space=cls.space, parent=cls.child, title='Zagnieżdżone podzadanie', created_by=cls.owner)

    login = fixtures.IndependentTaskTests.login
    url = fixtures.IndependentTaskTests.url
    task_url = fixtures.IndependentTaskTests.task_url

    def setUp(self):
        self.login(self.owner)

    def child_url(self, task=None, suffix='', scoped=True):
        task = task or self.child
        path = f'tasks/{task.work_item.key}/{suffix}'
        return self.url(path) if scoped else f'/space/{self.space.slug}/{path}'

    def api(self, scoped=True):
        return scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') if scoped else '/api/v1/page/'

    def assert_parent_url(self, url, view='list'):
        target = urlsplit(url)
        self.assertEqual(target.path, self.task_url())
        self.assertEqual(parse_qs(target.query), {'view': [view], 'q': ['kontekst'], 'tab': ['subtasks']})

    def test_direct_and_nested_urls_redirect_in_html_and_api_with_context(self):
        for task in [self.child, self.nested]:
            for scoped in [False, True]:
                with self.subTest(task=task.pk, scoped=scoped):
                    url = self.child_url(task, '?view=backlog&tab=history&q=kontekst', scoped)
                    response = self.client.get(url, follow=True)
                    self.assertEqual(response.status_code, 200)
                    self.assert_parent_url(response.redirect_chain[-1][0], 'backlog')
                    self.assertEqual(response.context['task'].pk, self.task.pk)
                    response = self.client.get(self.api(scoped), {'url': url}, follow=True)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(set(response.json()), {'redirect'})
                    self.assert_parent_url(response.json()['redirect'], 'backlog')
        response = self.client.get(self.task_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['task'].pk, self.task.pk)

    def test_access_checked_before_redirect_and_deleted_links_stay_missing(self):
        self.child.visibility, self.child.private_owner = 'private', self.owner
        self.child.save()
        self.login(self.member)
        # A public grandchild cannot bypass its private parent.
        for task in [self.child, self.nested]:
            for scoped in [False, True]:
                target = self.child_url(task, scoped=scoped)
                response = self.client.get(target, follow=True)
                self.assertEqual(response.status_code, 404)
                self.assertNotIn('Location', response)
                self.assertEqual(self.client.get(self.api(scoped), {'url': target}, follow=True).status_code, 404)
        SpaceTaskMembership.objects.create(task=self.child, user=self.member, role='observer')
        self.assertEqual(self.client.get(self.child_url(self.nested)).status_code, 302)
        self.assertEqual(self.client.get(self.child_url(suffix='edit/')).status_code, 403)
        self.login(self.owner)
        other = create_workplace_for_user(self.owner, 'Inny Workspace')
        self.assertEqual(self.client.get(self.child_url().replace(self.workspace.slug, other.slug)).status_code, 404)
        stale_url = self.child_url()
        self.child.delete()
        self.assertEqual(self.client.get(stale_url).status_code, 404)

    def test_root_lists_visible_descendants_and_keeps_operation_urls_on_children(self):
        hidden = SpaceTask.objects.create(space=self.space, parent=self.task, title='Prywatne', created_by=self.owner,
                                          visibility='private', private_owner=self.owner)
        SpaceTask.objects.create(space=self.space, parent=hidden, title='Ukryty potomek', created_by=self.owner)
        self.login(self.member)
        response = self.client.get(self.task_url('?tab=subtasks'))
        self.assertEqual(response.context['subtask_count'], 2)
        self.assertContains(response, self.nested.title)
        self.assertNotContains(response, 'Ukryty potomek')
        page = self.client.get(self.api(), {'url': self.task_url('?tab=subtasks')}).json()['data']
        self.assertEqual({item['task_id'] for item in page['children']}, {self.child.pk, self.nested.pk})
        child = next(item for item in page['children'] if item['task_id'] == self.child.pk)
        self.assertEqual(urlsplit(child['url']).path, self.child_url())
        self.assertEqual(urlsplit(child['edit_url']).path, self.child_url(suffix='edit/'))
        self.assertEqual(urlsplit(child['action_url']).path, self.child_url(suffix='action/'))

    def test_edit_dialog_and_save_return_to_root_also_from_backlog_and_legacy_urls(self):
        for view in ['list', 'backlog']:
            for scoped in [False, True]:
                for target in [self.child_url(self.nested, 'edit/', scoped),
                               scoped_workplace_app_path(self.workspace, 'spaces', f'items/{self.nested.work_item.pk}/edit/') if scoped
                               else f'/spaces/items/{self.nested.work_item.pk}/edit/']:
                    with self.subTest(view=view, target=target):
                        target += '?' + urlencode({'view': view, 'q': 'kontekst', 'tab': 'subtasks'})
                        response = self.client.get(self.api(scoped), {'url': target}, follow=True)
                        self.assertEqual(response.status_code, 200)
                        self.assert_parent_url(response.json()['data']['return_url'], view)
                        response = self.client.post(self.api(scoped) + '?' + urlencode({'url': target}), {
                            'title': 'Zmienione podzadanie', 'description': 'Zapis w oknie', 'priority': 'high', 'work_type': 'task',
                        })
                        self.assertEqual(response.status_code, 200)
                        self.assert_parent_url(response.json()['redirect'], view)
        self.nested.refresh_from_db()
        self.assertEqual(self.nested.title, 'Zmienione podzadanie')
        self.assertEqual(self.nested.parent_id, self.child.pk)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Praca w przestrzeni')

    def test_status_and_existing_autosave_write_child_only(self):
        for target in ('in_progress', 'resolved'):
            response = self.client.post(self.api() + '?' + urlencode({'url': self.child_url(suffix='action/')}), {
                'action': 'status', 'status': target, 'return_view': 'list',
            })
            self.assertEqual(response.status_code, 200)
        response = self.client.post(self.api() + '?' + urlencode({'url': self.child_url(suffix='action/')}), {
            'action': 'status', 'status': 'closed', 'return_view': 'list',
        })
        self.assertEqual(response.status_code, 200)
        self.child.refresh_from_db()
        self.assertTrue(self.child.is_completed)
        self.assertIsNotNone(self.child.completion_date)
        self.assertTrue(self.child.activities.filter(action='status_changed', actor=self.owner).exists())
        response = self.client.post(self.child_url(), {
            'action': 'save', 'autosave_fields': json.dumps(['title']), 'title': 'Stary zapis podzadania',
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.child.refresh_from_db()
        self.task.refresh_from_db()
        self.assertEqual(self.child.title, 'Stary zapis podzadania')
        self.assertEqual(self.task.title, 'Praca w przestrzeni')
        self.assertFalse(self.task.is_completed)

    def test_subtask_edit_status_validates_transitions_and_keeps_modal_field_ids(self):
        target = self.child_url(suffix='edit/')
        endpoint = self.api() + '?' + urlencode({'url': target})
        response = self.client.get(endpoint)
        fields = {field['name']: field for field in response.json()['data']['form']['fields']}
        self.assertIn('status', fields)
        for field in fields.values():
            self.assertTrue(field['id'].startswith(f'subtask-{self.child.work_item.pk}-'), field)
        posted = {'title': 'Zamknięte podzadanie', 'priority': 'medium', 'work_type': 'task', 'status': 'closed'}
        for target_status in ('in_progress', 'resolved'):
            self.assertEqual(self.client.post(endpoint, {**posted, 'status': target_status}).status_code, 200)
        response = self.client.post(endpoint, posted)
        self.assertEqual(response.status_code, 200)
        self.child.refresh_from_db()
        self.assertTrue(self.child.is_completed)
        self.assertIsNotNone(self.child.completion_date)
        self.assertTrue(self.child.activities.filter(action='status_changed', actor=self.owner).exists())
        settings = self.config.settings
        next(status for status in settings['statuses'] if status['key'] == 'closed')['transitions'] = []
        self.config.settings = settings
        self.config.save()
        for status in ['unknown', 'in_progress']:
            response = self.client.post(endpoint, {**posted, 'title': 'Nie zapisuj', 'status': status})
            self.assertEqual(response.status_code, 400)
            fields = {field['name']: field for field in response.json()['data']['form']['fields']}
            self.assertTrue(fields['status']['errors'])
            self.assertEqual(fields['title']['id'], f'subtask-{self.child.work_item.pk}-title')
            self.child.refresh_from_db()
            self.assertEqual(self.child.title, 'Zamknięte podzadanie')
            self.assertEqual(self.child.status, 'closed')
        parent = self.client.get(self.api(), {'url': self.task_url('edit/')}).json()['data']['form']
        self.assertNotIn('status', {field['name'] for field in parent['fields']})

    def test_root_bulk_delete_accepts_nested_selection_and_preserves_access_checks(self):
        protected = SpaceTask.objects.create(space=self.space, parent=self.nested, title='Chronione', created_by=self.owner,
                                             visibility='private', private_owner=self.owner)
        self.login(self.member)
        target = self.task_url('?tab=subtasks')
        self.assertEqual(self.client.post(target, {'action': 'delete_subtasks', 'subtask_ids': [protected.pk]}).status_code, 404)
        self.assertEqual(self.client.post(target, {'action': 'delete_subtasks', 'subtask_ids': [self.nested.pk]}).status_code, 403)
        self.assertTrue(SpaceTask.objects.filter(pk=self.nested.pk).exists())
        self.login(self.owner)
        self.assertEqual(self.client.post(target, {'action': 'delete_subtasks', 'subtask_ids': [self.task.pk]}).status_code, 404)
        response = self.client.post(target, {'action': 'delete_subtasks', 'subtask_ids': [self.nested.pk]})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(SpaceTask.objects.filter(pk=self.child.pk).exists())
        self.assertFalse(SpaceTask.objects.filter(pk__in=[self.nested.pk, protected.pk]).exists())
