from .testing import make_space
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import close_old_connections
from django.test import RequestFactory, TransactionTestCase

from django.db.models.query import QuerySet
from .models import SpaceTask, Space, SpaceMembership
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from . import views


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
