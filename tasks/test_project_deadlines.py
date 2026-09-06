from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from workplaces.models import Workplace
from .models import TaskProject, TaskProjectDeadlineRule, TaskProjectFieldOption


class DeadlineColorTests(SimpleTestCase):
    def test_boundaries_and_overlapping_rules_use_smallest_matching_threshold(self):
        today = date(2026, 9, 6)
        rules = [TaskProjectDeadlineRule(days=days, color=color) for days, color in reversed(TaskProjectDeadlineRule.DEFAULTS)]
        for days, expected in (
            (-10, '#FFE0DC'), (0, '#FFE0DC'), (1, '#FFE0DC'), (2, '#FFE0DC'),
            (3, '#FFEBC9'), (16, '#FFEBC9'), (17, '#DFF1E7'), (30, '#DFF1E7'), (31, ''),
        ):
            with self.subTest(days=days):
                self.assertEqual(TaskProjectDeadlineRule.color_for_date(today + timedelta(days=days), rules, today), expected)
        self.assertEqual(TaskProjectDeadlineRule.color_for_date(None, rules, today), '')
        self.assertEqual(TaskProjectDeadlineRule.color_for_date(today, [], today), '')

    def test_color_changes_on_the_next_local_calendar_day(self):
        rule = TaskProjectDeadlineRule(days=2, color='#FFE0DC')
        due_at = date(2026, 9, 9)
        with patch('tasks.models.timezone.localdate', return_value=date(2026, 9, 6)):
            self.assertEqual(TaskProjectDeadlineRule.color_for_date(due_at, [rule]), '')
        with patch('tasks.models.timezone.localdate', return_value=date(2026, 9, 7)):
            self.assertEqual(TaskProjectDeadlineRule.color_for_date(due_at, [rule]), '#FFE0DC')


class ProjectDeadlineSettingsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='deadline-owner', email='deadline-owner@example.com', password='test-pass')
        self.workplace = Workplace.objects.create(owner=self.user, name='Deadline workspace')
        self.client.force_login(self.user)
        self.url = reverse('project_field_settings')

    def post_rule(self, action, **data):
        return self.client.post(self.url, {'action': f'{action}_project_deadline_rule', **data}, follow=True)

    def test_existing_field_settings_gain_default_deadline_rules_once(self):
        TaskProjectFieldOption.ensure_defaults(self.user, self.workplace)
        for _ in range(2):
            response = self.client.get(self.url)
            self.assertContains(response, 'id="project-field-group-deadline"')
            self.assertContains(response, 'Dodaj regułę terminu')
        self.assertEqual(list(TaskProjectDeadlineRule.for_scope(self.user, self.workplace).values_list('days', 'color')), list(TaskProjectDeadlineRule.DEFAULTS))

    def test_create_edit_delete_and_reuse_threshold(self):
        response = self.post_rule('create', days=7, color='#abc123')
        self.assertContains(response, 'Zapisano regułę terminu.')
        rule = TaskProjectDeadlineRule.objects.get(owner=self.user, days=7)
        self.assertEqual(rule.color, '#ABC123')
        self.post_rule('update', rule_id=rule.pk, days=10, color='#123456')
        rule.refresh_from_db()
        self.assertEqual((rule.days, rule.color), (10, '#123456'))
        self.post_rule('delete', rule_id=rule.pk)
        rule.refresh_from_db()
        self.assertFalse(rule.is_active)
        self.post_rule('create', days=10, color='#654321')
        self.assertEqual(TaskProjectDeadlineRule.for_scope(self.user, self.workplace).filter(days=10, is_active=True).count(), 1)

    def test_rejects_duplicate_days_invalid_numbers_and_invalid_colors(self):
        self.client.get(self.url)
        for data in (
            {'days': 16, 'color': '#123456'}, {'days': -1, 'color': '#123456'},
            {'days': '2.5', 'color': '#123456'}, {'days': '', 'color': '#123456'},
            {'days': 36501, 'color': '#123456'}, {'days': 7, 'color': 'red'},
            {'days': 7, 'color': '#123456;display:none'},
        ):
            with self.subTest(data=data):
                response = self.post_rule('create', **data)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(TaskProjectDeadlineRule.for_scope(self.user, self.workplace).count(), 3)
        rule = TaskProjectDeadlineRule.for_scope(self.user, self.workplace).get(days=2)
        response = self.post_rule('update', rule_id=rule.pk, days=16, color='#123456')
        self.assertContains(response, 'Reguła dla tej liczby dni już istnieje.')
        rule.refresh_from_db()
        self.assertEqual(rule.days, 2)

    def test_removing_all_rules_does_not_restore_defaults(self):
        for rule in list(TaskProjectDeadlineRule.active_for_scope(self.user, self.workplace)):
            self.post_rule('delete', rule_id=rule.pk)
        self.client.get(self.url)
        self.assertFalse(TaskProjectDeadlineRule.active_for_scope(self.user, self.workplace).exists())

    def test_cannot_edit_or_delete_another_users_or_workplaces_rule(self):
        other = get_user_model().objects.create_user(username='other-owner', email='other-owner@example.com')
        workplace = Workplace.objects.create(owner=self.user, name='Other workspace')
        foreign_rules = [
            TaskProjectDeadlineRule.objects.create(owner=other, days=7, color='#123456'),
            TaskProjectDeadlineRule.objects.create(owner=self.user, workplace=workplace, days=7, color='#123456'),
        ]
        for rule in foreign_rules:
            for action in ('update', 'delete'):
                response = self.post_rule(action, rule_id=rule.pk, days=8, color='#654321')
                self.assertEqual(response.status_code, 404)
            rule.refresh_from_db()
            self.assertEqual((rule.days, rule.color, rule.is_active), (7, '#123456', True))

    @patch('tasks.views.tasks.timezone.localdate', return_value=date(2026, 9, 6))
    def test_directory_renders_configured_colors_and_preserves_finished_projects(self, _today):
        for days in (2, 16, 30, 31):
            TaskProject.objects.create(user=self.user, workplace=self.workplace, name=f'Deadline {days}', due_at=date(2026, 9, 6) + timedelta(days=days))
        for status in ('completed', 'cancelled'):
            TaskProject.objects.create(user=self.user, workplace=self.workplace, name=status, status=status, due_at=date(2026, 9, 5))
        TaskProject.objects.create(user=self.user, workplace=self.workplace, name='No deadline')
        self.post_rule('update', rule_id=list(TaskProjectDeadlineRule.active_for_scope(self.user, self.workplace))[1].pk, days=16, color='#ABC123')
        response = self.client.get(reverse('tasks:tasks'))
        projects = {project.name: project for project in response.context['projects']}
        for name, color in (
            ('Deadline 2', '#FFE0DC'), ('Deadline 16', '#ABC123'), ('Deadline 30', '#DFF1E7'),
            ('Deadline 31', '#DFEFFF'), ('completed', ''), ('cancelled', ''), ('No deadline', ''),
        ):
            self.assertEqual(projects[name].due_color, color)
        self.assertContains(response, 'style="--tasks-project-highlight-bg: #ABC123;" title="Dni do terminu: 16"')
        self.assertContains(response, 'Brak terminu')
