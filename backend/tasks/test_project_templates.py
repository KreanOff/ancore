from datetime import timedelta
from importlib import import_module
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.apps import apps
from django.db import connection
from django.test import TestCase
from django.utils import timezone

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import Task, TaskProject, TaskProjectTemplate, TaskSection


class ProjectTemplateTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='template-owner', email='template-owner@example.test')
        self.member = get_user_model().objects.create_user(username='template-member', email='template-member@example.test')
        self.workspace = create_workplace_for_user(self.owner, 'Szablony')
        self.other = create_workplace_for_user(self.owner, 'Inne szablony')
        self.membership = WorkplaceMembership.objects.create(workplace=self.workspace, user=self.member)
        self.project = TaskProject.objects.create(user=self.owner, workplace=self.workspace, name='Wdrożenie', description='Plan realizacji')
        self.section = TaskSection.objects.create(project=self.project, title='Przygotowanie', description='Opis grupy', order=2, status='closed')
        self.empty = TaskSection.objects.create(project=self.project, title='Pusta grupa', order=3)
        self.task = Task.objects.create(user=self.owner, section=self.section, title='Materiały', description='Sprawdź dane',
                                       priority='high', status='closed', assignee=self.member, estimated_minutes=45,
                                       time_spent_hours=2, due_at=timezone.now(), reminder_at=timezone.now() - timedelta(hours=1))
        self.child = Task.objects.create(user=self.owner, section=self.section, parent=self.task, title='Brief')
        self.url = scoped_workplace_app_path(self.workspace, 'tasks')
        self.client.force_login(self.member)

    def save_template(self):
        return TaskProjectTemplate.objects.create(
            user=self.owner, workplace=self.workspace, name=self.project.name,
            template_name=self.project.name, description=self.project.description,
            structure={'version': 1, 'sections': [{'id': self.section.pk, 'title': self.section.title}],
                       'tasks': [{'id': self.task.pk, 'title': self.task.title, 'section': self.section.pk}]},
        )

    def test_retired_template_creation_cannot_populate_another_workspace(self):
        template = self.save_template()
        project = TaskProject.objects.create(user=self.owner, workplace=self.other, name='Obcy')
        response = self.client.post(scoped_workplace_app_path(self.other, 'tasks'), {
            'action': 'create_project', 'template': template.pk, 'name': 'Nie twórz',
        })
        self.assertRedirects(response, '/workplaces/', fetch_redirect_response=False)
        self.assertFalse(project.sections.exists())
        self.assertFalse(TaskProject.objects.filter(name='Nie twórz').exists())

    def test_revoked_member_cannot_use_templates(self):
        template = self.save_template()
        self.membership.delete()
        for path in [self.url + 'templates/', self.url + f'?template={template.pk}']:
            self.assertRedirects(self.client.get(path), '/workplaces/', fetch_redirect_response=False)

    def test_existing_templates_get_names_during_backfill(self):
        legacy = TaskProjectTemplate.objects.create(user=self.owner, workplace=self.workspace, name='Stary projekt')
        named = TaskProjectTemplate.objects.create(user=self.owner, workplace=self.workspace, name='Inny projekt', template_name='Własna nazwa')
        migration = import_module('tasks.migrations.0049_taskprojecttemplate_template_name')
        migration.populate_template_names(apps, SimpleNamespace(connection=connection))
        legacy.refresh_from_db()
        named.refresh_from_db()
        self.assertEqual(legacy.template_name, 'Stary projekt')
        self.assertEqual(legacy.name, 'Stary projekt')
        self.assertEqual(named.template_name, 'Własna nazwa')
