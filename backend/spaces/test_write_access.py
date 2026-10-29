from .testing import make_space
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import close_old_connections
from django.test import Client, RequestFactory, TestCase, TransactionTestCase
from urllib.parse import urlencode

from django.db.models.query import QuerySet
from .models import SpaceTask, Space, SpaceMembership
from .access import editable_to
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from . import views


class SpaceWorkspaceRoleTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='role-owner', email='role-owner@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Role Workspace')
        for role in ('admin', 'member', 'guest'):
            person = users.objects.create_user(username='role-' + role, email=role + '@example.test')
            setattr(cls, role, person)
            WorkplaceMembership.objects.create(workplace=cls.workspace, user=person, role=role)
        cls.public = make_space(user=cls.owner, workplace=cls.workspace, name='Publiczna')
        cls.private = make_space(user=cls.owner, workplace=cls.workspace, name='Prywatna',
                                 visibility='private', private_owner=cls.owner)
        for person in (cls.admin, cls.member, cls.guest):
            SpaceMembership.objects.create(space=cls.private, user=person, role='admin')
        cls.tasks = [SpaceTask.objects.create(space=space, title=space.name, created_by=cls.owner)
                     for space in (cls.public, cls.private)]
        cls.child = SpaceTask.objects.create(space=cls.private, parent=cls.tasks[1],
                                             title='Podzadanie', created_by=cls.owner)

    def client_for(self, person):
        client = Client()
        client.force_login(person)
        session = client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()
        return client

    def test_active_or_inactive_guest_does_not_block_other_workspace_roles(self):
        for active in (True, False):
            membership = WorkplaceMembership.objects.get(workplace=self.workspace, user=self.guest)
            membership.is_active = active
            membership.save(update_fields=['is_active'])
            for person in (self.owner, self.admin, self.member):
                with self.subTest(active=active, person=person.username):
                    self.assertCountEqual(editable_to(Space.objects.all(), person), [self.public, self.private])
                    self.assertCountEqual(editable_to(SpaceTask.objects.all(), person), [*self.tasks, self.child])
            self.assertFalse(editable_to(Space.objects.all(), self.guest).exists())
            self.assertFalse(editable_to(SpaceTask.objects.all(), self.guest).exists())

    def test_owner_admin_and_member_can_write_with_a_guest_in_the_workspace(self):
        for person in (self.owner, self.admin, self.member):
            client = self.client_for(person)
            for task in self.tasks:
                with self.subTest(person=person.username, space=task.space.name):
                    base = scoped_workplace_app_path(self.workspace, 'space', task.space.slug + '/')
                    response = client.post(base + 'items/create/', {
                        'title': 'Nowe zadanie ' + person.username,
                        'work_type': 'task', 'priority': 'medium',
                    })
                    self.assertEqual(response.status_code, 302)
                    self.assertTrue(task.space.tasks.filter(title='Nowe zadanie ' + person.username).exists())
                    action = base + f'tasks/{task.work_item.key}/action/'
                    self.assertEqual(client.post(action, {'action': 'status', 'status': 'in_progress'}).status_code, 302)
                    for api in ('/api/v1/page/', scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')):
                        response = client.post(api + '?' + urlencode({'url': action}),
                                               {'action': 'status', 'status': 'new'})
                        self.assertEqual(response.status_code, 200)
                    task.refresh_from_db()
                    self.assertEqual(task.status, 'new')

    def test_guest_cannot_write_even_with_private_space_admin_role(self):
        task = self.tasks[1]
        request = RequestFactory().post('/space/action/', {'action': 'status', 'status': 'closed'})
        request.user, request.workplace = self.guest, self.workspace
        with self.assertRaises(PermissionDenied):
            views.item_action(request, pk=task.work_item.pk)
        task.refresh_from_db()
        self.assertEqual(task.status, 'new')


class SpaceWriteAccessRaceTests(TransactionTestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='write-owner', email='write-owner@example.test')
        self.member = get_user_model().objects.create_user(username='write-member', email='write-member@example.test')
        self.workspace = create_workplace_for_user(self.owner, 'Write races')
        self.membership = WorkplaceMembership.objects.create(workplace=self.workspace, user=self.member)
        self.project = make_space(user=self.owner, workplace=self.workspace, name='Private', visibility='private', private_owner=self.owner)
        self.grant = SpaceMembership.objects.create(space=self.project, user=self.member, role='member')
        self.section = self.project
        self.task = SpaceTask.objects.create(created_by=self.owner, space=self.section, title='Original')

    def request(self, suffix, data):
        request = RequestFactory().post('/spaces/' + suffix, data)
        request.user, request.workplace = self.member, self.workspace
        return request

    @contextmanager
    def changed_access_before_lock(self, *, remove_workspace=False):
        def change_access():
            close_old_connections()
            try:
                if remove_workspace:
                    self.membership.delete()
                else:
                    SpaceMembership.objects.filter(pk=self.grant.pk).update(role='observer')
            finally:
                close_old_connections()

        original = QuerySet.select_for_update
        changed = False

        def paused_lock(queryset, *args, **kwargs):
            nonlocal changed
            if not changed:
                changed = True
                with ThreadPoolExecutor(max_workers=1) as executor:
                    executor.submit(change_access).result(timeout=10)
            return original(queryset, *args, **kwargs)

        with patch.object(QuerySet, 'select_for_update', paused_lock):
            yield

    def test_backlog_action_rechecks_role_after_waiting_for_lock(self):
        item = self.task.work_item
        request = self.request(f'items/{item.pk}/action/', {'action': 'backlog'})
        with self.changed_access_before_lock(), self.assertRaises(PermissionDenied):
            views.item_action(request, item.pk)
        item.refresh_from_db()
        self.assertFalse(item.in_backlog)
        self.assertEqual(self.task.activities.count(), 1)

    def test_timeline_rechecks_role_after_waiting_for_lock(self):
        from .timeline import update_dates
        item = self.task.work_item
        request = self.request('dates/', {'start_on': '2026-10-28', 'end_on': '2026-10-29',
                                          'source_start_at': '', 'source_due_at': ''})
        with self.changed_access_before_lock(), self.assertRaises(PermissionDenied):
            update_dates(request, self.project.slug, item.key)
        item.refresh_from_db()
        self.task.refresh_from_db()
        self.assertIsNone(item.start_at)
        self.assertIsNone(self.task.due_at)
        self.assertEqual(self.task.activities.count(), 1)

    def test_timeline_rechecks_workspace_membership_after_waiting_for_lock(self):
        from .timeline import update_dates
        item = self.task.work_item
        request = self.request('dates/', {'start_on': '2026-10-28', 'end_on': '2026-10-29',
                                          'source_start_at': '', 'source_due_at': ''})
        with self.changed_access_before_lock(remove_workspace=True), self.assertRaises(PermissionDenied):
            update_dates(request, self.project.slug, item.key)
        item.refresh_from_db()
        self.task.refresh_from_db()
        self.assertIsNone(item.start_at)
        self.assertIsNone(self.task.due_at)
        self.assertEqual(self.task.activities.count(), 1)

    def test_item_edit_rechecks_role_after_waiting_for_lock(self):
        item = self.task.work_item
        request = self.request(f'items/{item.pk}/edit/', {'title': 'Forbidden edit', 'work_type': 'task', 'priority': 'medium', 'section': self.section.pk})
        with self.changed_access_before_lock(), self.assertRaises(PermissionDenied):
            views.item_edit(request, item.pk)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Original')

    def test_backlog_drag_rechecks_role_after_waiting_for_lock(self):
        item = self.task.work_item
        item.in_backlog = True
        item.save(update_fields=['in_backlog'])
        request = self.request(f'items/{item.pk}/action/', {
            'action': 'plan', 'space': item.space_id, 'source_sprint': '',
            'source_rank': item.rank, 'sprint': '', 'before': '', 'after': '',
        })
        with self.changed_access_before_lock(), self.assertRaises(PermissionDenied):
            views.item_action(request, item.pk)
        item.refresh_from_db()
        self.assertTrue(item.in_backlog)
        self.assertEqual(self.task.activities.count(), 1)

    def test_item_create_rechecks_project_role_after_waiting_for_lock(self):
        request = self.request(f'{self.project.pk}/items/create/', {'title': 'Forbidden creation', 'work_type': 'task', 'priority': 'medium', 'section': self.section.pk})
        with self.changed_access_before_lock(), self.assertRaises(PermissionDenied):
            views.item_edit(request, space_pk=self.project.pk)
        self.assertEqual(SpaceTask.objects.count(), 1)

    def test_revoked_workspace_membership_blocks_started_action(self):
        item = self.task.work_item
        request = self.request(f'items/{item.pk}/action/', {'action': 'backlog'})
        with self.changed_access_before_lock(remove_workspace=True), self.assertRaises(PermissionDenied):
            views.item_action(request, item.pk)
        item.refresh_from_db()
        self.assertFalse(item.in_backlog)
