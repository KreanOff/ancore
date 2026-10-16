from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from kanban.models import Kanban
from tasks.models import Task
from spaces.models import SpaceTask
from spaces.testing import make_space
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import CalendarEvent


class TaskCalendarTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='calendar-owner', email='calendar-owner@example.test')
        self.member = get_user_model().objects.create_user(username='calendar-member', email='calendar-member@example.test')
        self.workspace = create_workplace_for_user(self.owner, 'Kalendarz zespołu')
        self.other = create_workplace_for_user(self.owner, 'Inny kalendarz')
        self.membership = WorkplaceMembership.objects.create(workplace=self.workspace, user=self.member)
        self.client.force_login(self.member)
        self.space = make_space(user=self.owner, workplace=self.workspace, name='Praca')
        self.other_space = make_space(user=self.owner, workplace=self.other, name='Inna praca')
        self.due = timezone.now().replace(microsecond=0)
        self.url = scoped_workplace_app_path(self.workspace, 'calendar', 'events/')
        self.params = {'start': (self.due - timedelta(days=1)).isoformat(), 'end': (self.due + timedelta(days=1)).isoformat()}

    def test_events_and_space_tasks_have_distinct_identity_and_stable_links(self):
        event = CalendarEvent.objects.create(user=self.owner, workplace=self.workspace, title='Spotkanie', start=self.due, end=self.due + timedelta(hours=1))
        parent = SpaceTask.objects.create(space=self.space, created_by=self.owner, title='Praca', due_at=self.due)
        child = SpaceTask.objects.create(space=self.space, created_by=self.owner, title='Część', due_at=self.due, parent=parent)
        for model in (Task, Kanban):
            model.objects.create(user=self.owner, workplace=self.workspace, title='Archiwalne', due_at=self.due)
        payload = self.client.get(self.url, self.params).json()['events']
        by_id = {item['id']: item for item in payload}
        self.assertCountEqual(by_id, [event.pk, f'space_tasks:{parent.pk}', f'space_tasks:{child.pk}'])
        item = by_id[f'space_tasks:{child.pk}']
        self.assertEqual(item['source'], 'tasks')
        self.assertIn(f'/space/{self.space.slug}/tasks/{child.work_item.key}/', item['url'])
        self.assertEqual(item['start'], item['end'])
        self.assertEqual(self.client.get(item['url']).status_code, 200)
        self.assertEqual(CalendarEvent.objects.count(), 1)

    def test_only_open_in_range_current_workspace_visible_items(self):
        for values in [dict(status='closed'), dict(due_at=None), dict(due_at=self.due + timedelta(days=3)), dict(space=self.other_space), dict(visibility='private', private_owner=self.owner)]:
            SpaceTask.objects.create(**dict(dict(space=self.space, created_by=self.owner, title='Ukryte', due_at=self.due), **values))
        self.assertEqual(self.client.get(self.url, self.params).json()['events'], [])

    def test_normal_route_and_revoked_access(self):
        SpaceTask.objects.create(space=self.space, created_by=self.owner, title='Termin', due_at=self.due)
        self.client.get(self.url, self.params)
        self.assertEqual(len(self.client.get('/calendar/events/', self.params, follow=True).json()['events']), 1)
        self.membership.delete()
        self.assertRedirects(self.client.get(self.url, self.params), '/workplaces/', fetch_redirect_response=False)

    def test_bad_and_excessive_ranges_are_rejected(self):
        for params in [{}, {'start': 'x', 'end': 'y'}, {'start': self.params['end'], 'end': self.params['start']},
                       {'start': self.due.isoformat(), 'end': (self.due + timedelta(days=500)).isoformat()}]:
            self.assertEqual(self.client.get(self.url, params).status_code, 400)
