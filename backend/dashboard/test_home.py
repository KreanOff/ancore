from datetime import datetime

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from spaces.models import SpaceTask, WorkItem
from spaces.testing import make_space
from workplaces.models import create_workplace_for_user
from workplaces.services import ACTIVE_WORKPLACE_SESSION_KEY, scoped_workplace_app_path


class DashboardHomeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='overview', email='overview@example.test')
        cls.other_user = get_user_model().objects.create_user(username='other', email='other@example.test')
        cls.workplace = create_workplace_for_user(cls.user, 'Bieżąca przestrzeń')
        cls.other_workplace = create_workplace_for_user(cls.user, 'Druga przestrzeń')
        cls.foreign_workplace = create_workplace_for_user(cls.other_user, 'Obca przestrzeń')
        cls.now = timezone.make_aware(datetime(2026, 9, 15, 12, 0))

    def setUp(self):
        self.client.force_login(self.user)
        session = self.client.session
        session[ACTIVE_WORKPLACE_SESSION_KEY] = self.workplace.pk
        session.save()

    def task(self, **kwargs):
        owner = kwargs.pop('user', self.user)
        workplace = kwargs.pop('workplace', self.workplace)
        selected = kwargs.pop('section', None)
        if kwargs.get('parent'):
            selected = kwargs['parent'].space
        if selected is None or selected.user_id != owner.pk or selected.workplace_id != workplace.pk:
            if not hasattr(self, '_task_spaces'):
                self._task_spaces = {}
            key = (owner.pk, workplace.pk)
            if key not in self._task_spaces:
                self._task_spaces[key] = make_space(user=owner, workplace=workplace, name='Zadania')
            selected = self._task_spaces[key]
        kwargs.setdefault('title', 'Zadanie')
        return SpaceTask.objects.create(space=selected, created_by=owner, **kwargs)

    def test_home_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_foreign_space_metadata_is_not_exposed_by_an_owned_item(self):
        foreign = make_space(user=self.other_user, workplace=self.workplace, name='Poufna przestrzeń')
        task = self.task(due_at=self.now)
        WorkItem.objects.filter(task=task).update(space=foreign)
        response = self.client.get(reverse('home'))
        self.assertEqual(response.context['columns'][0][0]['count'], 0)
        self.assertNotContains(response, 'Poufna przestrzeń')

    def test_empty_workspace_and_partial_navigation_response(self):
        response = self.client.get(reverse('home'), {'focus': 'kanban'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        data = response.context['columns'][0][0]
        self.assertEqual(data['count'], 0)
        self.assertEqual(data['percent'], 0)
        self.assertContains(response, 'Postęp pracy')
        self.assertContains(response, 'Edytuj pulpit')
        self.assertTrue(response.context['dashboard'].is_default)
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_scoped_module_visit_switches_dashboard_context(self):
        self.task(title='Zadanie pierwszej przestrzeni', priority='urgent')
        self.client.get(scoped_workplace_app_path(self.other_workplace, 'tasks'))
        response = self.client.get(reverse('home'), {'focus': 'priority'})
        self.assertEqual(response.context['current_workplace'], self.other_workplace)
        self.assertEqual(response.context['columns'][0][0]['count'], 0)
        self.assertNotContains(response, 'Zadanie pierwszej przestrzeni')
