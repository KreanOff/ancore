from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import Kanban, KanbanProject, KanbanSection


class KanbanDeadlineTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='card-owner', email='card-owner@example.test')
        self.member = get_user_model().objects.create_user(username='card-member', email='card-member@example.test')
        self.workspace = create_workplace_for_user(self.owner, 'Terminy kart')
        WorkplaceMembership.objects.create(workplace=self.workspace, user=self.member)
        project = KanbanProject.objects.create(user=self.owner, workplace=self.workspace, name='Karty')
        self.section = KanbanSection.objects.create(project=project, title='Tablica')
        self.base = scoped_workplace_app_path(self.workspace, 'kanban')
        self.client.force_login(self.member)

    def test_create_edit_and_clear_deadline_with_history(self):
        response = self.client.post(self.base, {
            'action': 'create_task_modal', 'title': 'Z terminem', 'section': self.section.pk,
            'status': 'new', 'priority': 'medium', 'due_at': '2026-10-15T13:45',
        })
        self.assertEqual(response.status_code, 302)
        card = Kanban.objects.get(title='Z terminem')
        self.assertEqual(timezone.localtime(card.due_at).strftime('%Y-%m-%dT%H:%M'), '2026-10-15T13:45')
        url = self.base + f'view-task/{card.task_id}/?task_pk={card.pk}'
        for value in ['2026-10-16T14:30', '']:
            response = self.client.post(url, {'title': card.title, 'section': self.section.pk,
                                             'status': 'new', 'priority': 'medium', 'due_at': value})
            self.assertEqual(response.status_code, 302)
            card.refresh_from_db()
            self.assertEqual(timezone.localtime(card.due_at).strftime('%Y-%m-%dT%H:%M') if card.due_at else '', value)
            activity = card.activities.filter(action='updated').latest('pk')
            self.assertEqual(activity.actor, self.member)
            self.assertIn('termin', activity.metadata['fields'])

    def test_invalid_deadline_keeps_form_and_does_not_create_card(self):
        response = self.client.post(self.base, {'action': 'create_task_modal', 'title': 'Niepoprawny',
            'section': self.section.pk, 'status': 'new', 'priority': 'medium', 'due_at': 'nie-data'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('due_at', response.context['task_modal_form'].errors)
        self.assertFalse(Kanban.objects.exists())
