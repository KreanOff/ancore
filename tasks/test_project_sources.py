from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.urls import reverse

from workplaces.models import Workplace
from .forms import TaskProjectForm, TaskProjectRenameForm
from .models import TaskProject, TaskProjectFieldOption


class ProjectSourceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='source-owner', email='source-owner@example.com')
        self.workplace = Workplace.objects.create(owner=self.user, name='Sources workspace')
        self.client.force_login(self.user)
        session = self.client.session
        session['active_workplace_id'] = self.workplace.pk
        session.save()
        self.settings_url = reverse('project_field_settings')

    def source(self, label='Polecenie', color='#ABCDEF'):
        self.client.post(self.settings_url, {
            'action': 'create_project_field_option', 'field_type': 'source', 'label': label, 'color': color,
        })
        return TaskProjectFieldOption.for_scope(self.user, self.workplace).get(field_type='source', label=label)

    def test_source_settings_start_empty_and_allow_named_colored_sources(self):
        response = self.client.get(self.settings_url)
        self.assertContains(response, 'id="project-field-group-source"')
        self.assertContains(response, 'Dodaj pierwsze źródło')
        option = self.source(color='#abcdef')
        self.assertEqual(option.color, '#ABCDEF')
        response = self.client.get(self.settings_url)
        self.assertContains(response, 'Kolor wartości Polecenie')
        self.assertContains(response, 'style="--tasks-project-highlight-bg: #ABCDEF;"')

    def test_create_edit_and_clear_source_on_project(self):
        first, second = self.source(), self.source('Strona internetowa', '#123456')
        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project', 'name': 'Nowy projekt', 'source': first.label,
        })
        self.assertEqual(response.status_code, 302)
        project = TaskProject.objects.get(user=self.user, name='Nowy projekt')
        self.assertEqual(project.source, 'Polecenie')
        for value in (second.label, ''):
            response = self.client.post(reverse('tasks:tasks'), {
                'action': 'edit_project', 'project_id': project.pk, 'name': project.name, 'source': value,
            })
            self.assertEqual(response.status_code, 302)
            project.refresh_from_db()
            self.assertEqual(project.source, value)

    def test_source_rename_and_color_update_follow_all_using_projects_in_scope(self):
        option = self.source()
        projects = [TaskProject.objects.create(user=self.user, workplace=self.workplace, name=name, source='Polecenie') for name in ('Pierwszy', 'Drugi')]
        other_workspace = Workplace.objects.create(owner=self.user, name='Other')
        foreign_project = TaskProject.objects.create(user=self.user, workplace=other_workspace, name='Foreign', source='Polecenie')
        other_user = get_user_model().objects.create_user(username='other-source-owner', email='other-source@example.com')
        foreign_user_project = TaskProject.objects.create(user=other_user, workplace=self.workplace, name='Other owner', source='Polecenie')
        response = self.client.post(self.settings_url, {
            'action': 'update_project_field_option', 'option_id': option.pk,
            'label': 'Polecenie klienta', 'color': '#123456',
        }, follow=True)
        self.assertContains(response, 'Zapisano wartość')
        for project in projects:
            project.refresh_from_db()
            self.assertEqual(project.source, 'Polecenie klienta')
        for project in (foreign_project, foreign_user_project):
            project.refresh_from_db()
            self.assertEqual(project.source, 'Polecenie')
        response = self.client.get(reverse('tasks:tasks'))
        self.assertEqual([project.source_color for project in response.context['projects']], ['#123456', '#123456'])
        self.assertContains(response, 'tasks-project-value-badge--source" style="--tasks-project-highlight-bg: #123456;"')
        for query in ({'q': 'Polecenie klienta'}, {'source': 'klienta'}, {'source': 'Polecenie klienta', 'source_op': 'equals'}):
            response = self.client.get(reverse('tasks:tasks'), query)
            self.assertEqual({project.pk for project in response.context['projects']}, {project.pk for project in projects})

    def test_deletion_is_blocked_when_used_but_last_unused_source_can_be_deleted(self):
        option = self.source()
        project = TaskProject.objects.create(user=self.user, workplace=self.workplace, name='Project', source=option.label)
        response = self.client.post(self.settings_url, {'action': 'delete_project_field_option', 'option_id': option.pk}, follow=True)
        self.assertContains(response, 'jest używana przez projekt')
        option.refresh_from_db()
        self.assertTrue(option.is_active)
        project.source = ''
        project.save()
        self.client.post(self.settings_url, {'action': 'delete_project_field_option', 'option_id': option.pk})
        self.client.get(self.settings_url)
        self.assertFalse(TaskProjectFieldOption.active_for_scope(self.user, self.workplace).filter(field_type='source').exists())

    def test_duplicate_invalid_color_and_too_long_source_are_rejected(self):
        self.source()
        for label, color in (('polecenie', '#123456'), ('   ', '#123456'), ('Nowe', 'red'), ('X' * 121, '#123456')):
            self.client.post(self.settings_url, {'action': 'create_project_field_option', 'field_type': 'source', 'label': label, 'color': color})
        self.assertEqual(TaskProjectFieldOption.for_scope(self.user, self.workplace).filter(field_type='source').count(), 1)
        self.source('Ź' * 120)

    def test_project_forms_keep_scoped_choices_and_accept_manual_sources(self):
        option = self.source()
        legacy = 'Źródło z dawnego importu'
        project = TaskProject.objects.create(user=self.user, workplace=self.workplace, name='Legacy', source=legacy)
        other_workspace = Workplace.objects.create(owner=self.user, name='Elsewhere')
        TaskProject.objects.create(user=self.user, workplace=other_workspace, name='Foreign', source='Foreign source')
        for form_class in (TaskProjectForm, TaskProjectRenameForm):
            unbound = form_class(user=self.user, workplace=self.workplace)
            available = dict(unbound.fields['source'].widget.choices)
            self.assertIn(option.label, available)
            self.assertIn(legacy, available)
            self.assertNotIn('Foreign source', available)
            for source, valid in ((option.label, True), (legacy, True), ('', True), ('Wpisane ręcznie', True), ('Ź' * 120, True), ('Ź' * 121, False)):
                form = form_class({'name': project.name, 'source': source}, user=self.user, workplace=self.workplace)
                self.assertEqual(form.is_valid(), valid, form.errors)
        response = self.client.get(reverse('tasks:tasks'))
        self.assertContains(response, f'data-project-source="{legacy}"')
        self.assertContains(response, '<select name="source"')

    def test_manual_source_can_be_created_edited_and_replaced_with_a_preset(self):
        option = self.source()
        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'create_project', 'name': 'Ręczne źródło', 'source': '  Spotkanie na targach  ',
        })
        self.assertEqual(response.status_code, 302)
        project = TaskProject.objects.get(user=self.user, name='Ręczne źródło')
        self.assertEqual(project.source, 'Spotkanie na targach')
        self.assertEqual(TaskProjectFieldOption.for_scope(self.user, self.workplace).filter(field_type='source').count(), 1)
        response = self.client.get(reverse('tasks:tasks'))
        self.assertEqual(response.context['projects'][0].source_color, '')
        for value in ('Rozmowa telefoniczna', option.label, ''):
            response = self.client.post(reverse('tasks:tasks'), {
                'action': 'edit_project', 'project_id': project.pk, 'name': project.name, 'source': value,
            })
            self.assertEqual(response.status_code, 302)
            project.refresh_from_db()
            self.assertEqual(project.source, value)
        self.assertEqual(TaskProjectFieldOption.for_scope(self.user, self.workplace).filter(field_type='source').count(), 1)

    def test_manual_source_survives_other_form_errors_and_is_escaped(self):
        value = 'Targi "2026" <branżowe>'
        for form_class in (TaskProjectForm, TaskProjectRenameForm):
            form = form_class({'name': '', 'source': value}, user=self.user, workplace=self.workplace)
            self.assertFalse(form.is_valid())
            self.assertNotIn('source', form.errors)
            self.assertEqual(dict(form.fields['source'].widget.choices)[value], value)
            self.assertIn('selected', str(form['source']))
            self.assertIn('&lt;branżowe&gt;', str(form['source']))
            self.assertNotIn('<branżowe>', str(form['source']))

    def test_too_long_manual_source_does_not_overwrite_existing_value(self):
        project = TaskProject.objects.create(user=self.user, workplace=self.workplace, name='Project', source='Poprzednie')
        response = self.client.post(reverse('tasks:tasks'), {
            'action': 'edit_project', 'project_id': project.pk, 'name': project.name, 'source': 'X' * 121,
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('source', response.context['project_rename_form'].errors)
        project.refresh_from_db()
        self.assertEqual(project.source, 'Poprzednie')

    def test_cannot_edit_another_workspaces_source(self):
        other_workspace = Workplace.objects.create(owner=self.user, name='Elsewhere')
        option = TaskProjectFieldOption.objects.create(owner=self.user, workplace=other_workspace, field_type='source', value='foreign', label='Foreign')
        for action in ('update', 'delete'):
            response = self.client.post(self.settings_url, {'action': f'{action}_project_field_option', 'option_id': option.pk, 'label': 'Changed', 'color': '#123456'})
            self.assertEqual(response.status_code, 404)

    def test_migration_imports_existing_sources_without_changing_project_text(self):
        names = ('Polecenie', 'Polecenie', 'Zażółć', 'Zazolc', 'Ź' * 120, '')
        projects = [TaskProject.objects.create(user=self.user, workplace=self.workplace, name=f'Import {i}', source=source) for i, source in enumerate(names)]
        personal = TaskProject.objects.create(user=self.user, name='Personal', source='Polecenie')
        migration = import_module('tasks.migrations.0046_project_source_options')
        for _ in range(2):
            migration.import_existing_sources(apps, SimpleNamespace(connection=connection))
        options = TaskProjectFieldOption.for_scope(self.user, self.workplace).filter(field_type='source')
        self.assertEqual(set(options.values_list('label', flat=True)), set(names) - {''})
        self.assertEqual(options.count(), 4)
        self.assertEqual(len(set(options.values_list('value', flat=True))), 4)
        self.assertTrue(all(option.color == '#ECE8FF' for option in options))
        self.assertTrue(TaskProjectFieldOption.for_scope(self.user).filter(field_type='source', label=personal.source).exists())
        for project, source in zip(projects, names):
            project.refresh_from_db()
            self.assertEqual(project.source, source)
        # Seeding just sources must not suppress defaults for the other fields.
        self.assertEqual(TaskProjectFieldOption.active_for_scope(self.user, self.workplace).exclude(field_type='source').count(), 14)

    def test_existing_case_variants_can_be_recolored_without_renaming(self):
        for source in ('Polecenie', 'polecenie'):
            TaskProject.objects.create(user=self.user, workplace=self.workplace, name=source, source=source)
        migration = import_module('tasks.migrations.0046_project_source_options')
        migration.import_existing_sources(apps, SimpleNamespace(connection=connection))
        option = TaskProjectFieldOption.for_scope(self.user, self.workplace).get(field_type='source', label='Polecenie')
        response = self.client.post(self.settings_url, {
            'action': 'update_project_field_option', 'option_id': option.pk, 'label': option.label, 'color': '#123456',
        }, follow=True)
        self.assertContains(response, 'Zapisano wartość')
        option.refresh_from_db()
        self.assertEqual(option.color, '#123456')
