from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from workplaces.models import Workplace
from .models import TaskProject, TaskProjectDeadlineRule
from .views.tasks import _decorate_project_field_values, _project_field_configuration


class ProjectDeadlineOverrideTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='override-owner', email='override@example.com')
        self.workplace = Workplace.objects.create(owner=self.user, name='Workspace')
        self.projects = [TaskProject.objects.create(
            user=self.user, workplace=self.workplace, name=name,
            due_at=date(2026, 9, 16),
        ) for name in ('Projekt A', 'Projekt B')]
        self.project, self.other_project = self.projects
        self.defaults = list(TaskProjectDeadlineRule.active_for_scope(self.user, self.workplace))
        self.url = reverse('project_field_settings')
        self.client.force_login(self.user)
        session = self.client.session
        session['active_workplace_id'] = self.workplace.pk
        session.save()

    def post(self, action, project=None, **data):
        return self.client.post(self.url, {
            'action': action,
            'project_id': (project or self.project).pk,
            **data,
        }, follow=True)

    def rules(self, project=None):
        return TaskProjectDeadlineRule.for_scope(
            self.user, self.workplace, project or self.project,
        ).filter(is_active=True)

    def enable(self, project=None):
        return self.post('enable_project_deadline_rules', project=project)

    def test_existing_projects_inherit_and_require_enabling_before_editing(self):
        response = self.client.get(self.url, {'project_id': self.project.pk})
        self.assertTrue(response.context['deadline_inherited'])
        self.assertContains(response, 'Ustaw własne progi')
        self.assertContains(response, 'class="tasks-project-deadline-rules" disabled')
        self.assertFalse(self.project.use_custom_deadline_rules)
        self.assertFalse(self.rules().exists())
        self.assertEqual(self.post('create_project_deadline_rule', days=7, color='#123456').status_code, 403)

    def test_enable_copies_current_defaults_once_and_preserves_project_selection(self):
        default = self.defaults[0]
        default.days, default.color = 4, '#ABC123'
        default.save()
        response = self.enable()
        self.assertRedirects(response, f'{self.url}?project_id={self.project.pk}#project-field-group-deadline')
        self.assertFalse(response.context['deadline_inherited'])
        self.project.refresh_from_db()
        self.assertTrue(self.project.use_custom_deadline_rules)
        self.assertEqual(list(self.rules().values_list('days', 'color')), [(4, '#ABC123'), (16, '#FFEBC9'), (30, '#DFF1E7')])
        self.post('update_project_deadline_rule', rule_id=self.rules().get(days=4).pk, days=5, color='#123456')
        self.enable()
        self.assertTrue(self.rules().filter(days=5, color='#123456').exists())
        self.assertEqual(self.rules().count(), 3)

    def test_each_project_can_use_the_same_threshold_with_a_different_color(self):
        self.enable()
        self.enable(self.other_project)
        for project, color in ((self.project, '#AABBCC'), (self.other_project, '#112233')):
            response = self.post('update_project_deadline_rule', project=project,
                                 rule_id=self.rules(project).get(days=16).pk, days=16, color=color)
            self.assertContains(response, 'Zapisano regułę terminu.')
        with patch('tasks.views.tasks.timezone.localdate', return_value=date(2026, 9, 6)):
            response = self.client.get(reverse('tasks:tasks'))
        projects = {project.pk: project for project in response.context['projects']}
        self.assertEqual(projects[self.project.pk].due_color, '#AABBCC')
        self.assertEqual(projects[self.other_project.pk].due_color, '#112233')
        self.assertEqual(TaskProjectDeadlineRule.for_scope(self.user, self.workplace).get(days=16).color, '#FFEBC9')

    def test_global_changes_only_affect_projects_without_overrides(self):
        self.enable()
        self.defaults[1].color = '#123456'
        self.defaults[1].save()
        with patch('tasks.views.tasks.timezone.localdate', return_value=date(2026, 9, 6)):
            response = self.client.get(reverse('tasks:tasks'))
        colors = {project.pk: project.due_color for project in response.context['projects']}
        self.assertEqual(colors, {self.project.pk: '#FFEBC9', self.other_project.pk: '#123456'})

    def test_override_crud_validates_within_selected_project(self):
        self.enable()
        self.post('create_project_deadline_rule', days=7, color='#abcdef')
        rule = self.rules().get(days=7)
        self.assertEqual(rule.color, '#ABCDEF')
        for data in ({'days': 16, 'color': '#123456'}, {'days': -1, 'color': '#123456'},
                     {'days': '2.5', 'color': '#123456'}, {'days': 36501, 'color': '#123456'},
                     {'days': 8, 'color': 'invalid'}):
            with self.subTest(data=data):
                self.post('update_project_deadline_rule', rule_id=rule.pk, **data)
                rule.refresh_from_db()
                self.assertEqual((rule.days, rule.color), (7, '#ABCDEF'))
        self.post('delete_project_deadline_rule', rule_id=rule.pk)
        self.post('create_project_deadline_rule', days=7, color='#123456')
        self.assertEqual(self.rules().get(days=7).color, '#123456')

    def test_empty_override_survives_reload_without_falling_back_to_defaults(self):
        self.enable()
        for rule in list(self.rules()):
            self.post('delete_project_deadline_rule', rule_id=rule.pk)
        self.project.refresh_from_db()
        self.assertTrue(self.project.use_custom_deadline_rules)
        response = self.client.get(self.url, {'project_id': self.project.pk})
        self.assertEqual(response.context['project_deadline_rules'], [])
        self.assertFalse(response.context['deadline_inherited'])
        with patch('tasks.views.tasks.timezone.localdate', return_value=date(2026, 9, 6)):
            response = self.client.get(reverse('tasks:tasks'))
        project = next(project for project in response.context['projects'] if project.pk == self.project.pk)
        self.assertEqual(project.due_color, '#DFEFFF')

    def test_enable_with_empty_defaults_and_reset_to_current_defaults(self):
        TaskProjectDeadlineRule.for_scope(self.user, self.workplace).update(is_active=False)
        self.enable()
        self.project.refresh_from_db()
        self.assertTrue(self.project.use_custom_deadline_rules)
        self.assertFalse(self.rules().exists())
        self.post('create_project_deadline_rule', days=7, color='#ABCDEF')
        self.defaults[1].is_active = True
        self.defaults[1].save()
        response = self.post('reset_project_deadline_rules')
        self.project.refresh_from_db()
        self.assertFalse(self.project.use_custom_deadline_rules)
        self.assertFalse(self.project.deadline_rules.exists())
        self.assertTrue(response.context['deadline_inherited'])
        self.assertEqual([rule.days for rule in response.context['project_deadline_rules']], [16])
        self.enable()
        self.assertEqual(list(self.rules().values_list('days', flat=True)), [16])

    def test_cannot_modify_rules_from_another_project_or_shared_defaults(self):
        self.enable()
        self.enable(self.other_project)
        for rule in (self.rules(self.other_project).first(), self.defaults[0]):
            for action in ('update', 'delete'):
                response = self.post(f'{action}_project_deadline_rule', rule_id=rule.pk, days=8, color='#123456')
                self.assertEqual(response.status_code, 404)
        response = self.client.post(self.url, {
            'action': 'delete_project_deadline_rule', 'rule_id': self.rules().first().pk,
        })
        self.assertEqual(response.status_code, 404)

    def test_cannot_access_projects_from_other_users_or_workspaces(self):
        other_user = get_user_model().objects.create_user(username='other-override-owner', email='other-override@example.com')
        other_workplace = Workplace.objects.create(owner=self.user, name='Other workspace')
        forbidden = [
            TaskProject.objects.create(user=other_user, workplace=self.workplace, name='Private'),
            TaskProject.objects.create(user=self.user, workplace=other_workplace, name='Elsewhere'),
        ]
        for project in forbidden:
            self.assertEqual(self.client.get(self.url, {'project_id': project.pk}).status_code, 404)
            for action in ('enable_project_deadline_rules', 'reset_project_deadline_rules', 'create_project_deadline_rule'):
                self.assertEqual(self.post(action, project=project, days=7, color='#123456').status_code, 404)
        for project_id in ('invalid', '-1', '0'):
            self.assertEqual(self.client.get(self.url, {'project_id': project_id}).status_code, 404)

    def test_active_threshold_unique_per_project_and_rules_deleted_with_project(self):
        self.enable()
        with self.assertRaises(IntegrityError), transaction.atomic():
            TaskProjectDeadlineRule.objects.create(owner=self.user, workplace=self.workplace,
                                                  project=self.project, days=16, color='#123456')
        rule_ids = list(self.rules().values_list('pk', flat=True))
        self.project.delete()
        self.assertFalse(TaskProjectDeadlineRule.objects.filter(pk__in=rule_ids).exists())
        self.assertEqual(TaskProjectDeadlineRule.for_scope(self.user, self.workplace).count(), 3)

    def test_decoration_fetches_all_overrides_together_and_preserves_finished_projects(self):
        self.enable()
        self.enable(self.other_project)
        configuration = _project_field_configuration(self.user, self.workplace)
        projects = list(TaskProject.objects.filter(pk__in=[project.pk for project in self.projects]))
        with self.assertNumQueries(1):
            _decorate_project_field_values(projects, configuration)
        for status in ('completed', 'cancelled'):
            projects[0].status = status
            projects[0].due_at = date.today() - timedelta(days=1)
            _decorate_project_field_values(projects, configuration)
            self.assertEqual(projects[0].due_color, '')
