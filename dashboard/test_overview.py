from datetime import datetime, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dashboard.overview import dashboard_overview
from kanban.models import Kanban
from planner.models import CalendarEvent
from tasks.models import Task, TaskProject, TaskSection
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import ACTIVE_WORKPLACE_SESSION_KEY, scoped_workplace_app_path


class DashboardOverviewTests(TestCase):
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

    def overview(self, focus='deadlines'):
        with patch('dashboard.overview.timezone.now', return_value=self.now):
            return dashboard_overview(self.user, self.workplace, focus)

    def task(self, **kwargs):
        values = {'user': self.user, 'workplace': self.workplace, 'title': 'Zadanie'}
        values.update(kwargs)
        return Task.objects.create(**values)

    def test_home_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_aggregates_use_status_and_exclude_subitems(self):
        self.task(priority='urgent', due_at=self.now-timedelta(hours=1))
        parent = self.task(status='resolved', priority='high')
        self.task(parent=parent, priority='urgent', due_at=self.now-timedelta(days=1))
        self.task(status='closed', priority='urgent')
        self.task(status='closed', completion_date=self.now-timedelta(days=8))
        card = Kanban.objects.create(user=self.user, workplace=self.workplace, title='Karta', status='in_progress', priority='high')
        Kanban.objects.create(user=self.user, workplace=self.workplace, title='Podkarta', parent=card)
        Kanban.objects.create(user=self.user, workplace=self.workplace, title='Zamknięta karta', status='closed')
        # Explicit dates make the fixtures independent of model save's clock.
        closed = Task.objects.filter(status='closed').order_by('pk').first()
        Task.objects.filter(pk=closed.pk).update(completion_date=self.now-timedelta(days=1))
        old = Task.objects.filter(status='closed').order_by('pk').last()
        Task.objects.filter(pk=old.pk).update(completion_date=self.now-timedelta(days=8))
        Kanban.objects.filter(status='closed').update(completion_date=self.now-timedelta(hours=1))
        context = self.overview()
        self.assertEqual(context['dashboard_totals'], {'total': 6, 'open': 3, 'priority': 3, 'closed_week': 2, 'overdue': 1})
        self.assertEqual(context['dashboard_completed_percent'], 50)
        self.assertEqual(context['dashboard_closed_count'], 3)

    def test_owner_workspace_membership_and_assignee_do_not_expand_access(self):
        visible = self.task(title='Widoczne', due_at=self.now)
        self.task(workplace=self.other_workplace, title='Drugi Workspace', due_at=self.now)
        self.task(user=self.other_user, workplace=self.workplace, title='Inny właściciel', due_at=self.now, assignee=self.user)
        WorkplaceMembership.objects.create(workplace=self.foreign_workplace, user=self.user)
        self.task(user=self.other_user, workplace=self.foreign_workplace, title='Samo członkostwo', due_at=self.now, assignee=self.user)
        Kanban.objects.create(user=self.other_user, workplace=self.workplace, title='Obca karta')
        TaskProject.objects.create(user=self.other_user, workplace=self.workplace, name='Obcy projekt')
        CalendarEvent.objects.create(user=self.other_user, workplace=self.workplace, title='Obce wydarzenie', start=self.now, end=self.now+timedelta(hours=1))
        context = self.overview()
        self.assertEqual(context['dashboard_totals']['total'], 1)
        self.assertEqual([row['object'] for row in context['dashboard_items']], [visible])
        self.assertEqual(context['dashboard_project_count'], 0)
        self.assertEqual(context['dashboard_event_count'], 0)

    def test_deadlines_have_a_local_seven_day_boundary_and_limit(self):
        self.task(title='Bez terminu')
        self.task(title='Następny tydzień', due_at=self.now.replace(hour=0)+timedelta(days=7))
        self.task(title='Zamknięte zaległe', status='closed', due_at=self.now-timedelta(days=2))
        expected = [self.task(title=f'Termin {i}', due_at=self.now+timedelta(hours=i-2)) for i in range(8)]
        context = self.overview('invalid')
        self.assertEqual(context['dashboard_focus'], 'deadlines')
        self.assertEqual(context['dashboard_item_count'], 8)
        self.assertEqual([row['object'] for row in context['dashboard_items']], expected[:6])
        self.assertTrue(context['dashboard_items'][0]['overdue'])
        self.assertFalse(context['dashboard_items'][2]['overdue'])
        self.assertTrue(context['dashboard_items'][2]['due_today'])

    def test_foreign_project_metadata_is_not_exposed_by_an_owned_item(self):
        project = TaskProject.objects.create(user=self.other_user, workplace=self.workplace, name='Poufny projekt')
        section = TaskSection.objects.create(project=project, title='Poufna grupa')
        self.task(section=section, due_at=self.now)
        context = self.overview()
        self.assertEqual(context['dashboard_items'][0]['location'], 'Zadania · Bez grupy')
        with patch('dashboard.overview.timezone.now', return_value=self.now):
            response = self.client.get(reverse('home'))
        self.assertNotContains(response, 'Poufny projekt')
        self.assertNotContains(response, 'Poufna grupa')

    def test_priority_and_kanban_filters_link_by_task_number_in_current_workspace(self):
        high = self.task(title='Wysokie', priority='high')
        urgent = self.task(title='Pilne', priority='urgent')
        self.task(title='Niskie', priority='low')
        self.task(title='Zamknięte', priority='urgent', status='closed')
        card = Kanban.objects.create(user=self.user, workplace=self.workplace, title='Karta', priority='urgent')
        context = self.overview('priority')
        self.assertEqual([row['object'] for row in context['dashboard_items']], [urgent, high])
        self.assertEqual(context['dashboard_items'][0]['url'], scoped_workplace_app_path(self.workplace, 'tasks', f'view-task/{urgent.task_id}/'))
        context = self.overview('kanban')
        self.assertEqual([row['object'] for row in context['dashboard_items']], [card])
        self.assertEqual(context['dashboard_items'][0]['url'], scoped_workplace_app_path(self.workplace, 'kanban', f'view-task/{card.task_id}/'))

    def test_calendar_includes_ongoing_and_all_day_events_but_excludes_finished(self):
        def event(title, start, end, **kwargs):
            return CalendarEvent.objects.create(user=self.user, workplace=self.workplace, title=title, start=start, end=end, **kwargs)
        ongoing = event('Trwające', self.now-timedelta(days=1), self.now+timedelta(hours=1))
        all_day = event('Całodniowe', self.now.replace(hour=0), self.now.replace(hour=0)+timedelta(days=1), all_day=True)
        next_event = event('Jutro', self.now+timedelta(days=1), self.now+timedelta(days=1, hours=1))
        event('Zakończone', self.now-timedelta(hours=2), self.now-timedelta(hours=1))
        event('Za tydzień', self.now.replace(hour=0)+timedelta(days=7), self.now+timedelta(days=7))
        context = self.overview()
        self.assertEqual([row['object'] for row in context['dashboard_events']], [ongoing, all_day, next_event])
        self.assertEqual(context['dashboard_events'][0]['url'], f'{scoped_workplace_app_path(self.workplace, "calendar")}?event={ongoing.pk}')

    def test_project_progress_counts_only_owned_top_level_tasks(self):
        project = TaskProject.objects.create(user=self.user, workplace=self.workplace, name='Projekt')
        section = TaskSection.objects.create(project=project, title='Grupa')
        parent = self.task(section=section)
        self.task(section=section, status='closed')
        self.task(section=section, parent=parent)
        self.task(user=self.other_user, section=section)
        TaskProject.objects.create(user=self.user, workplace=self.workplace, name='Gotowy', status='completed')
        TaskProject.objects.create(user=self.user, workplace=self.other_workplace, name='Poza przestrzenią')
        context = self.overview()
        self.assertEqual(context['dashboard_project_count'], 1)
        row = context['dashboard_projects'][0]
        self.assertEqual(row['object'].item_count, 2)
        self.assertEqual(row['percent'], 50)
        self.assertEqual(row['url'], f'{scoped_workplace_app_path(self.workplace, "tasks")}?project={project.pk}')

    def test_empty_workspace_and_partial_navigation_response(self):
        response = self.client.get(reverse('home'), {'focus': 'kanban'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['dashboard_totals']['total'], 0)
        self.assertEqual(response.context['dashboard_completed_percent'], 0)
        self.assertContains(response, 'Brak otwartych kart')
        self.assertContains(response, 'Miejsce na kolejny projekt')
        self.assertContains(response, 'Spokojny kalendarz')
        self.assertEqual(response['Cache-Control'], 'no-store')

    def test_scoped_module_visit_switches_dashboard_context(self):
        self.task(title='Zadanie pierwszej przestrzeni', priority='urgent')
        self.client.get(scoped_workplace_app_path(self.other_workplace, 'tasks'))
        response = self.client.get(reverse('home'), {'focus': 'priority'})
        self.assertEqual(response.context['current_workplace'], self.other_workplace)
        self.assertEqual(response.context['dashboard_totals']['total'], 0)
        self.assertNotContains(response, 'Zadanie pierwszej przestrzeni')
