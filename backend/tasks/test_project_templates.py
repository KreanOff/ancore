from datetime import timedelta
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.apps import apps
from django.db import connection
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.utils import timezone

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .forms import TaskProjectForm
from .models import Task, TaskActivity, TaskProject, TaskProjectTemplate, TaskSection
from .project_templates import populate_project_from_template, save_project_template


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
        return save_project_template(self.project)

    def test_save_then_create_copies_structure_and_resets_execution_state(self):
        response = self.client.post(self.url, {'action': 'save_project_template', 'project_id': self.project.pk})
        self.assertRedirects(response, self.url + 'templates/')
        template = TaskProjectTemplate.objects.get()
        response = self.client.post(self.url, {'action': 'create_project', 'name': 'Nowy klient', 'template': template.pk})
        project = TaskProject.objects.get(name='Nowy klient')
        self.assertRedirects(response, self.url + f'?project={project.pk}')
        self.assertEqual(project.user, self.owner)
        self.assertEqual(project.workplace, self.workspace)
        self.assertEqual(project.sections.count(), 2)
        self.assertEqual(list(project.sections.values_list('title', flat=True)), ['Przygotowanie', 'Pusta grupa'])
        tasks = Task.objects.filter(section__project=project)
        self.assertEqual(tasks.count(), 2)
        parent, child = tasks.get(title='Materiały'), tasks.get(title='Brief')
        self.assertEqual(child.parent, parent)
        self.assertIsNone(parent.estimated_minutes)
        self.task.refresh_from_db()
        self.assertEqual(self.task.estimated_minutes, 45)
        self.assertEqual(parent.priority, 'high')
        self.assertNotEqual(parent.task_id, self.task.task_id)
        self.assertEqual(parent.status, 'new')
        self.assertEqual(parent.section.status, 'open')
        self.assertFalse(parent.is_completed)
        for name in ['completion_date', 'due_at', 'reminder_at', 'time_spent_hours', 'time_spent_minutes', 'assignee']:
            self.assertIsNone(getattr(parent, name))
        self.assertEqual(parent.activities.count(), 1)
        self.assertEqual(parent.activities.get().actor, self.member)

    def test_snapshot_survives_source_edit_and_deletion(self):
        template = self.save_template()
        template.structure['tasks'][0]['estimated_minutes'] = 45
        template.save(update_fields=['structure'])
        self.project.delete()
        template.refresh_from_db()
        self.assertEqual(template.structure['tasks'][0]['title'], 'Materiały')
        response = self.client.post(self.url, {'action': 'create_project', 'name': 'Niezależny', 'template': template.pk})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Task.objects.filter(section__project__name='Niezależny').count(), 2)
        self.assertFalse(Task.objects.filter(section__project__name='Niezależny', estimated_minutes__isnull=False).exists())
        template.refresh_from_db()
        self.assertEqual(template.structure['tasks'][0]['estimated_minutes'], 45)

    def test_template_choices_and_forged_submission_are_workspace_scoped(self):
        template = self.save_template()
        other_url = scoped_workplace_app_path(self.other, 'tasks')
        self.client.force_login(self.owner)
        response = self.client.post(other_url, {'action': 'create_project', 'name': 'Obcy', 'template': template.pk})
        self.assertEqual(response.status_code, 200)
        self.assertIn('template', response.context['project_form'].errors)
        self.assertFalse(TaskProject.objects.filter(name='Obcy').exists())
        self.assertEqual(self.client.get(other_url + f'?template={template.pk}').status_code, 404)
        self.assertEqual(self.client.post(other_url + 'templates/', {'template_id': template.pk}).status_code, 404)
        self.assertFalse(TaskProjectForm(user=self.owner, workplace=self.other).fields['template'].queryset.exists())

    def test_template_service_also_rejects_wrong_owner_or_workspace(self):
        template = self.save_template()
        project = TaskProject.objects.create(user=self.owner, workplace=self.other, name='Obcy')
        with self.assertRaises(ValidationError):
            populate_project_from_template(project, template, self.member)
        self.assertFalse(project.sections.exists())

    def test_source_snapshot_excludes_foreign_owned_tasks(self):
        Task.objects.create(user=self.member, section=self.section, title='Niepoprawny właściciel')
        template = self.save_template()
        self.assertEqual(len(template.structure['tasks']), 2)

    def test_regular_creation_still_creates_initial_group_and_normal_route_works(self):
        self.client.get(self.url)
        response = self.client.post('/tasks/', {'action': 'create_project', 'name': 'Zwykły', 'section_title': 'Pierwsza'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(TaskProject.objects.get(name='Zwykły').sections.get().title, 'Pierwsza')

    def test_template_preselection_opens_existing_modal_and_removal_keeps_projects(self):
        template = self.save_template()
        response = self.client.get(self.url, {'template': template.pk})
        self.assertTrue(response.context['project_modal_open'])
        self.assertEqual(response.context['project_form'].initial['description'], 'Plan realizacji')
        response = self.client.post(self.url + 'templates/', {'template_id': template.pk})
        self.assertRedirects(response, self.url + 'templates/')
        self.assertTrue(TaskProject.objects.filter(pk=self.project.pk).exists())
        self.assertFalse(TaskProjectTemplate.objects.exists())

    def test_revoked_member_cannot_use_templates(self):
        template = self.save_template()
        self.membership.delete()
        for path in [self.url + 'templates/', self.url + f'?template={template.pk}']:
            self.assertRedirects(self.client.get(path), '/workplaces/', fetch_redirect_response=False)

    def test_creation_failure_rolls_back_whole_project(self):
        template = self.save_template()
        with patch('tasks.models.Task.save', side_effect=RuntimeError('failed')):
            with self.assertRaises(RuntimeError):
                self.client.post(self.url, {'action': 'create_project', 'name': 'Wycofany', 'template': template.pk})
        self.assertFalse(TaskProject.objects.filter(name='Wycofany').exists())

    def test_malformed_template_identifiers_return_404(self):
        for value in ['abc', '-1', '9' * 30]:
            self.assertEqual(self.client.get(self.url, {'template': value}).status_code, 404)
            self.assertEqual(self.client.post(self.url + 'templates/', {'template_id': value}).status_code, 404)
            self.assertEqual(self.client.post(self.url, {'action': 'save_project_template', 'project_id': value}).status_code, 404)

    def test_directory_search_filter_and_sort_preserve_workspace_scope(self):
        template = self.save_template()
        empty = TaskProjectTemplate.objects.create(user=self.owner, workplace=self.workspace, name='Alfa', structure={})
        TaskProjectTemplate.objects.create(user=self.owner, workplace=self.other, name='Wdrożenie obce', structure={})
        TaskProjectTemplate.objects.create(user=self.member, workplace=self.workspace, name='Wdrożenie cudze', structure={})
        for query in ['WDROŻENIE', 'realizacji']:
            response = self.client.get(self.url + 'templates/', {'q': query})
            self.assertEqual([item.pk for item in response.context['templates']], [template.pk])
        response = self.client.get(self.url + 'templates/', {'sort': 'name_asc'})
        self.assertEqual([item.pk for item in response.context['templates']], [empty.pk, template.pk])
        response = self.client.get(self.url + 'templates/', {'description_filter': 'without'})
        self.assertEqual([item.pk for item in response.context['templates']], [empty.pk])
        response = self.client.get(self.url + 'templates/', {'q': 'nie ma takiego szablonu'})
        self.assertEqual(response.context['templates'].paginator.count, 0)
        self.assertContains(response, 'Brak pasujących szablonów')

    def test_directory_pagination_retains_search_sort_and_filter(self):
        TaskProjectTemplate.objects.bulk_create([
            TaskProjectTemplate(user=self.owner, workplace=self.workspace, name=f'Szablon {index:02}', description='Plan', structure={})
            for index in range(27)
        ])
        response = self.client.get(self.url + 'templates/', {'q': 'Szablon', 'sort': 'name_desc', 'description_filter': 'with', 'page_size': 25})
        window = response.context['template_window']
        self.assertEqual(len(response.context['templates']), 25)
        self.assertEqual(response.context['templates'][0].name, 'Szablon 26')
        params = parse_qs(urlsplit(window['next_url']).query)
        self.assertEqual(params, {'q': ['Szablon'], 'sort': ['name_desc'], 'description_filter': ['with'], 'page_size': ['25'], 'page': ['2']})
        response = self.client.get(window['next_url'])
        self.assertEqual([item.name for item in response.context['templates']], ['Szablon 01', 'Szablon 00'])
        response = self.client.get(self.url + 'templates/', {'page_size': 50})
        self.assertEqual(len(response.context['templates']), 27)

    def test_directory_invalid_parameters_use_safe_defaults(self):
        self.save_template()
        self.client.get(self.url)
        response = self.client.get('/tasks/templates/', {'sort': 'structure__password', 'page_size': 'all', 'page': 'invalid', 'description_filter': 'anything'}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['sort_field'], 'created_at')
        self.assertEqual(response.context['template_window']['page_size'], 25)
        self.assertEqual(response.context['template_window']['page'], 1)
        self.assertEqual(response.context['description_filter'], '')

    def test_rename_template_keeps_project_name_and_snapshot(self):
        template = self.save_template()
        self.assertEqual(template.template_name, self.project.name)
        structure = template.structure
        response = self.client.post(self.url + 'templates/', {
            'action': 'rename', 'template_id': template.pk, 'template_name': '  Standard wdrożenia  ',
        })
        self.assertRedirects(response, self.url + 'templates/')
        template.refresh_from_db()
        self.assertEqual(template.template_name, 'Standard wdrożenia')
        self.assertEqual(template.name, self.project.name)
        self.assertEqual(template.structure, structure)
        self.assertEqual(str(template), 'Standard wdrożenia')
        response = self.client.get(self.url, {'template': template.pk})
        self.assertEqual(response.context['project_form'].initial['name'], self.project.name)
        choices = response.context['project_form'].fields['template']
        self.assertEqual(choices.label_from_instance(template), 'Standard wdrożenia')

    def test_invalid_template_name_keeps_modal_open_and_saved_name(self):
        template = self.save_template()
        for value in ['', '   ', 'a' * 121]:
            response = self.client.post(self.url + 'templates/', {
                'action': 'rename', 'template_id': template.pk, 'template_name': value,
            })
            self.assertEqual(response.status_code, 200)
            self.assertIn('template_name', response.context['rename_form'].errors)
            self.assertEqual(response.context['rename_template_id'], template.pk)
            template.refresh_from_db()
            self.assertEqual(template.template_name, self.project.name)

    def test_template_name_search_sort_and_rename_are_scoped(self):
        template = self.save_template()
        template.template_name = 'Żółty standard'
        template.save(update_fields=['template_name'])
        other = TaskProjectTemplate.objects.create(user=self.owner, workplace=self.workspace, name='Inny projekt', template_name='Alfa')
        response = self.client.get(self.url + 'templates/', {'q': 'ŻÓŁTY'})
        self.assertEqual([item.pk for item in response.context['templates']], [template.pk])
        response = self.client.get(self.url + 'templates/', {'sort': 'template_name_asc'})
        self.assertEqual([item.pk for item in response.context['templates']], [other.pk, template.pk])
        self.client.force_login(self.owner)
        response = self.client.post(scoped_workplace_app_path(self.other, 'tasks', 'templates/'), {
            'action': 'rename', 'template_id': template.pk, 'template_name': 'Obca zmiana',
        })
        self.assertEqual(response.status_code, 404)
        template.refresh_from_db()
        self.assertEqual(template.template_name, 'Żółty standard')

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

    def editor_post(self, template, form_kind, **data):
        return self.client.post(self.url + f'templates/{template.pk}/edit/', {
            'action': f'save_{form_kind}', **{f'{form_kind}-{key}': '' if value is None else value for key, value in data.items()},
        })

    def test_template_editor_changes_metadata_without_changing_existing_projects(self):
        template = self.save_template()
        original_structure = template.structure
        response = self.editor_post(template, 'details', template_name='Standard', name='Nowy projekt', description='Nowy opis')
        self.assertEqual(response.status_code, 302)
        template.refresh_from_db()
        self.assertEqual((template.template_name, template.name, template.description), ('Standard', 'Nowy projekt', 'Nowy opis'))
        self.assertEqual(template.structure, original_structure)
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, 'Wdrożenie')
        self.assertEqual(self.client.get('/tasks/templates/' + str(template.pk) + '/edit/', follow=True).status_code, 200)

    def test_template_editor_adds_and_edits_groups_tasks_and_subtasks_used_by_new_projects(self):
        template = self.save_template()
        self.assertEqual(self.editor_post(template, 'section', title='Nowa grupa', description='Etap', priority='high', kind='milestones', wip_limit=4, order=1).status_code, 302)
        template.refresh_from_db()
        group = next(s for s in template.structure['sections'] if s['title'] == 'Nowa grupa')
        self.assertEqual(self.editor_post(template, 'task', title='Nowe zadanie', description='Opis', section=group['id'], parent='', priority='low', task_type='call', estimated_minutes=25).status_code, 302)
        template.refresh_from_db()
        task = next(t for t in template.structure['tasks'] if t['title'] == 'Nowe zadanie')
        self.assertEqual(self.editor_post(template, 'task', title='Nowe podzadanie', section=group['id'], parent=task['id'], priority='medium', task_type='email').status_code, 302)
        edited = {key: value for key, value in task.items() if key != 'id'}
        edited.update(item_id=task['id'], title='Zmienione zadanie', estimated_minutes=40)
        self.assertEqual(self.editor_post(template, 'task', **edited).status_code, 302)
        response = self.client.post(self.url, {'action': 'create_project', 'name': 'Z edytowanego szablonu', 'template': template.pk})
        self.assertEqual(response.status_code, 302)
        created = TaskProject.objects.get(name='Z edytowanego szablonu')
        copied = Task.objects.get(section__project=created, title='Zmienione zadanie')
        self.assertEqual((copied.estimated_minutes, copied.task_type, copied.section.wip_limit), (None, 'call', 4))
        self.assertEqual(copied.subtasks.get().title, 'Nowe podzadanie')
        self.assertEqual(list(created.sections.values_list('title', flat=True)), ['Nowa grupa', 'Przygotowanie', 'Pusta grupa'])
        self.assertEqual(self.project.sections.count(), 2)
        self.assertEqual(Task.objects.filter(section__project=self.project).count(), 2)

    def test_template_editor_validation_keeps_snapshot_and_reopens_correct_modal(self):
        template = self.save_template()
        original = template.structure
        for kind, data in [('details', {'template_name': ' ', 'name': 'Nazwa'}),
                           ('section', {'title': ' ', 'order': -1}),
                           ('task', {'title': 'Nieprawidłowe', 'section': 999999, 'priority': 'bad', 'estimated_minutes': -1})]:
            response = self.editor_post(template, kind, **data)
            self.assertEqual(response.status_code, 200)
            if kind == 'details':
                self.assertTrue(response.context['details_form'].errors)
            else:
                active = next(m for m in response.context['editor_modals'] if m['kind'] == kind)
                self.assertTrue(active['active'])
                self.assertTrue(active['form'].errors)
            template.refresh_from_db()
            self.assertEqual(template.structure, original)
            self.assertEqual(template.template_name, 'Wdrożenie')

    def test_template_editor_rejects_cycles_and_cross_group_parents(self):
        template = self.save_template()
        parent = template.structure['tasks'][0]
        child = template.structure['tasks'][1]
        for parent_id, section_id in [(parent['id'], self.section.pk), (child['id'], self.section.pk), (child['id'], self.empty.pk)]:
            values = {key: value for key, value in parent.items() if key != 'id'}
            values.update(item_id=parent['id'], parent=parent_id, section=section_id)
            response = self.editor_post(template, 'task', **values)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(next(modal['form'] for modal in response.context['editor_modals'] if modal['kind'] == 'task').errors)
        template.refresh_from_db()
        self.assertIsNone(template.structure['tasks'][0]['parent'])

    def test_template_editor_moves_descendants_with_parent(self):
        template = self.save_template()
        parent = template.structure['tasks'][0]
        values = {key: value for key, value in parent.items() if key != 'id'}
        values.update(item_id=parent['id'], section=self.empty.pk)
        self.assertEqual(self.editor_post(template, 'task', **values).status_code, 302)
        template.refresh_from_db()
        self.assertEqual({t['section'] for t in template.structure['tasks']}, {self.empty.pk})

    def test_template_editor_removals_cascade_only_inside_snapshot(self):
        template = self.save_template()
        editor = self.url + f'templates/{template.pk}/edit/'
        response = self.client.post(editor, {'action': 'delete_task', 'item_id': self.task.pk})
        self.assertEqual(response.status_code, 302)
        template.refresh_from_db()
        self.assertEqual(template.structure['tasks'], [])
        self.assertEqual(len(template.structure['sections']), 2)
        template.structure = self.save_template().structure
        template.save()
        response = self.client.post(editor, {'action': 'delete_section', 'item_id': self.section.pk})
        self.assertEqual(response.status_code, 302)
        template.refresh_from_db()
        self.assertEqual(template.structure['tasks'], [])
        self.assertEqual([s['id'] for s in template.structure['sections']], [self.empty.pk])
        self.assertEqual(Task.objects.filter(section__project=self.project).count(), 2)

    def test_template_editor_access_and_identifiers_are_scoped(self):
        template = self.save_template()
        editor = self.url + f'templates/{template.pk}/edit/'
        for action in ['save_task', 'save_section', 'delete_task', 'delete_section']:
            kind = action.split('_')[1]
            for value in ['garbage', '-1', '9' * 30, '999999']:
                key = f'{kind}-item_id' if action.startswith('save') else 'item_id'
                self.assertEqual(self.client.post(editor, {'action': action, key: value}).status_code, 404)
        self.client.force_login(self.owner)
        other_editor = scoped_workplace_app_path(self.other, 'tasks', f'templates/{template.pk}/edit/')
        self.assertEqual(self.client.get(other_editor).status_code, 404)
        self.assertEqual(self.client.post(other_editor, {'action': 'delete_task', 'item_id': self.task.pk}).status_code, 404)
        foreign = TaskProjectTemplate.objects.create(user=self.member, workplace=self.workspace, name='Obcy', structure={})
        self.assertEqual(self.client.get(self.url + f'templates/{foreign.pk}/edit/').status_code, 404)
        self.client.force_login(self.member)
        self.membership.delete()
        self.assertIn(self.client.get(editor).status_code, [302, 403, 404])
        self.assertIn(self.client.post(editor, {'action': 'delete_task', 'item_id': self.task.pk}).status_code, [302, 403, 404])
        template.refresh_from_db()
        self.assertEqual(len(template.structure['tasks']), 2)

    def test_empty_template_can_gain_structure_and_be_copied(self):
        template = TaskProjectTemplate.objects.create(user=self.owner, workplace=self.workspace, name='Pusty', structure={})
        self.assertEqual(self.editor_post(template, 'section', title='Pierwsza', priority='none', kind='issues', order=0).status_code, 302)
        response = self.client.post(self.url, {'action': 'create_project', 'name': 'Z pustego', 'template': template.pk})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(TaskProject.objects.get(name='Z pustego').sections.count(), 1)

    def test_template_editor_does_not_reuse_removed_snapshot_identifiers(self):
        template = self.save_template()
        editor = self.url + f'templates/{template.pk}/edit/'
        old_task_ids = {item['id'] for item in template.structure['tasks']}
        self.client.post(editor, {'action': 'delete_task', 'item_id': self.task.pk})
        self.assertEqual(self.editor_post(template, 'task', title='Nowe', section=self.section.pk,
                                          priority='medium', task_type='general').status_code, 302)
        template.refresh_from_db()
        self.assertNotIn(template.structure['tasks'][0]['id'], old_task_ids)
        self.assertEqual(self.client.post(editor, {'action': 'delete_task', 'item_id': self.task.pk}).status_code, 404)

    def test_modal_endpoint_loads_details_and_saves_without_redirecting(self):
        template = self.save_template()
        editor = self.url + f'templates/{template.pk}/edit/'
        self.assertRedirects(self.client.get(editor), self.url + 'templates/')
        response = self.client.get(editor, HTTP_X_TEMPLATE_MODAL='true')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['saved'])
        self.assertIn('name="details-template_name"', response.json()['html'])
        self.assertNotIn('<html', response.json()['html'])
        response = self.client.post(editor, {
            'action': 'save_details', 'details-template_name': 'Standard',
            'details-name': 'Projekt', 'details-description': 'Opis',
        }, HTTP_X_TEMPLATE_MODAL='true')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['saved'])
        self.assertIn('value="Standard"', response.json()['html'])
        template.refresh_from_db()
        self.assertEqual(template.template_name, 'Standard')
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, 'Wdrożenie')

    def test_modal_validation_preserves_input_and_new_groups_refresh_task_choices(self):
        template = self.save_template()
        editor = self.url + f'templates/{template.pk}/edit/'
        response = self.client.post(editor, {
            'action': 'save_details', 'details-template_name': '',
            'details-name': 'Zachowaj ten wpis',
        }, HTTP_X_TEMPLATE_MODAL='true')
        self.assertFalse(response.json()['saved'])
        self.assertIn('value="Zachowaj ten wpis"', response.json()['html'])
        self.assertIn('aria-invalid="true"', response.json()['html'])
        response = self.client.post(editor, {
            'action': 'save_section', 'section-title': 'Nowa grupa w modalu',
            'section-priority': 'none', 'section-kind': 'issues', 'section-order': '0',
        }, HTTP_X_TEMPLATE_MODAL='true')
        self.assertTrue(response.json()['saved'])
        template.refresh_from_db()
        section = next(s for s in template.structure['sections'] if s['title'] == 'Nowa grupa w modalu')
        self.assertIn(f'<option value="{section["id"]}">Nowa grupa w modalu</option>', response.json()['html'])
        self.assertFalse(TaskSection.objects.filter(title='Nowa grupa w modalu').exists())

    def test_modal_requests_preserve_workspace_scope_and_csrf(self):
        template = self.save_template()
        editor = self.url + f'templates/{template.pk}/edit/'
        foreign = scoped_workplace_app_path(self.other, 'tasks', f'templates/{template.pk}/edit/')
        self.client.force_login(self.owner)
        for method in [self.client.get, self.client.post]:
            self.assertEqual(method(foreign, HTTP_X_TEMPLATE_MODAL='true').status_code, 404)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.member)
        data = {'action': 'save_details', 'details-template_name': 'CSRF', 'details-name': 'Projekt'}
        self.assertEqual(client.post(editor, data, HTTP_X_TEMPLATE_MODAL='true').status_code, 403)
        client.get(editor, HTTP_X_TEMPLATE_MODAL='true')
        response = client.post(editor, data, HTTP_X_TEMPLATE_MODAL='true', HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
        self.assertTrue(response.json()['saved'])
        self.membership.delete()
        self.assertIn(client.get(editor, HTTP_X_TEMPLATE_MODAL='true').status_code, [302, 403, 404])
