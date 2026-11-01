from .testing import make_space
from datetime import date, datetime

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.test import Client, TestCase

from .models import SpaceTask, Space, SpaceMembership
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .defaults import TEMPLATES, template_settings
from .models import Space, SpaceTaskMembership, Sprint, Team, TeamMembership, WorkItem


class SpaceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(username='space-owner', email='space-owner@example.test')
        cls.member = User.objects.create_user(username='space-member', email='space-member@example.test')
        cls.observer = User.objects.create_user(username='space-observer', email='space-observer@example.test')
        cls.other = User.objects.create_user(username='space-other', email='space-other@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Praca')
        cls.foreign = create_workplace_for_user(cls.other, 'Obcy Workspace')
        for person in (cls.member, cls.observer):
            WorkplaceMembership.objects.create(workplace=cls.workspace, user=person, role='member')
        cls.project = make_space(name='Produkt', user=cls.owner, workplace=cls.workspace, visibility='private', private_owner=cls.owner)
        SpaceMembership.objects.create(space=cls.project, user=cls.member, role='member')
        SpaceMembership.objects.create(space=cls.project, user=cls.observer, role='observer')
        cls.space = cls.project
        cls.space.template = 'scrum'
        cls.space.kind = 'software'
        cls.space.save()
        cls.space.configuration.settings = template_settings('scrum')
        cls.space.configuration.save()
        cls.section = cls.project
        cls.task = SpaceTask.objects.create(created_by=cls.owner, space=cls.section, title='Wspólne zadanie')
        cls.item = cls.task.work_item
        cls.hidden_project = make_space(name='Poufna przestrzeń', user=cls.owner, workplace=cls.workspace, visibility='private', private_owner=cls.owner)
        cls.foreign_project = make_space(name='Obca przestrzeń', user=cls.other, workplace=cls.foreign)

    def setUp(self):
        self.client.force_login(self.owner)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, suffix='', app='spaces'):
        return scoped_workplace_app_path(self.workspace, app, suffix)

    def space_url(self, suffix=''):
        return scoped_workplace_app_path(self.workspace, 'space', f'{self.space.slug}/{suffix}')

    def test_directory_plain_and_scoped_and_privacy(self):
        self.client.force_login(self.member)
        for url in ['/spaces/', self.url()]:
            response = self.client.get(url, follow=True)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Produkt')
            self.assertNotContains(response, 'Poufna przestrzeń')
            self.assertNotContains(response, 'Obca przestrzeń')
            self.assertContains(response, 'Zespoły')

    def test_all_space_views_render(self):
        for view in ('overview', 'list', 'board', 'backlog', 'timeline', 'reports', 'settings'):
            with self.subTest(view=view):
                response = self.client.get(self.space_url(f'?view={view}'))
                self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(self.space_url('configuration/')).status_code, 200)

    def test_space_search_respects_workspace_and_project_access(self):
        self.client.force_login(self.member)
        for url in ['/spaces/search/', self.url('search/')]:
            for query in ('produkt', self.space.key.lower()):
                response = self.client.get(url, {'q': query})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['count'], 1)
                self.assertIn(self.space_url(''), response.json()['html'])
                self.assertIn('data-space-avatar=', response.json()['html'])
                self.assertEqual(response.headers['Cache-Control'], 'private, no-store')
            for query in ('Poufna', 'Obca'):
                self.assertEqual(self.client.get(url, {'q': query}).json()['count'], 0)
        self.client.force_login(self.observer)
        self.assertEqual(self.client.get(self.url('search/'), {'q': 'Produkt'}).json()['count'], 1)
        SpaceMembership.objects.filter(space=self.project, user=self.observer).delete()
        self.assertEqual(self.client.get(self.url('search/'), {'q': 'Produkt'}).json()['count'], 0)

    def test_space_search_limits_results_and_escapes_names(self):
        for number in range(22):
            make_space(user=self.owner, workplace=self.workspace, name=f'Wyszukiwanie {number:02}')
        response = self.client.get(self.url('search/'), {'q': 'Wyszukiwanie'})
        self.assertEqual(response.json()['count'], 20)
        self.assertIn('Więcej wyników', response.json()['html'])
        self.assertNotIn('Wyszukiwanie 20', response.json()['html'])
        self.project.name = '<script>Przestrzeń</script>'
        self.project.save()
        html = self.client.get(self.url('search/'), {'q': '<script>'}).json()['html']
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>', html)

    def test_space_search_requires_login_and_get(self):
        self.assertEqual(self.client.get(self.url('search/'), {'q': '   '}).json()['count'], 0)
        self.assertEqual(self.client.post(self.url('search/')).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.get(self.url('search/')).status_code, 302)

    def test_create_space_and_template_are_independent_of_management(self):
        payload = {'name': 'Nowa przestrzeń', 'key': 'NOW', 'kind': 'software', 'template': 'scrum', 'management': 'company', 'visibility': 'private'}
        response = self.client.post(self.url('create/'), payload, HTTP_X_WORK_MODAL='true')
        self.assertTrue(response.json()['saved'])
        space = Space.objects.get(key='NOW')
        self.assertTrue(space.configuration.shared)
        self.assertEqual(space.private_owner, self.owner)
        self.assertEqual(self.client.post(self.url('create/'), payload, HTTP_X_WORK_MODAL='true').status_code, 400)
        payload.update(key='BAD', kind='business')
        self.assertEqual(self.client.post(self.url('create/'), payload, HTTP_X_WORK_MODAL='true').status_code, 400)

    def test_create_page_keeps_visible_directory_behind_modal(self):
        self.client.force_login(self.member)
        for url in ['/spaces/create/', self.url('create/')]:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertTemplateUsed(response, 'spaces/index.html')
                self.assertTemplateNotUsed(response, 'spaces/form_page.html')
                self.assertContains(response, 'Produkt')
                self.assertNotContains(response, 'Poufna przestrzeń')
                self.assertNotContains(response, 'Obca przestrzeń')
                self.assertEqual(response.context['modal']['directory_url'], self.url())
                self.assertEqual(response.context['modal']['action'], url)
                self.assertContains(response, 'Nazwa przestrzeni')
                self.assertNotContains(response, '>Wróć</a>')

    def test_create_page_preserves_invalid_form_over_directory(self):
        payload = {'name': 'Szkic przestrzeni', 'key': '!', 'kind': 'software', 'template': 'kanban', 'management': 'team', 'visibility': 'private'}
        for url in ['/spaces/create/', self.url('create/')]:
            with self.subTest(url=url):
                response = self.client.post(url, payload)
                self.assertEqual(response.status_code, 400)
                self.assertTemplateUsed(response, 'spaces/index.html')
                self.assertTemplateNotUsed(response, 'spaces/form_page.html')
                self.assertIn('key', response.context['modal']['form'].errors)
                self.assertContains(response, 'Szkic przestrzeni', status_code=400)
                self.assertContains(response, 'Produkt', status_code=400)
        self.assertFalse(Space.objects.filter(name='Szkic przestrzeni').exists())

    def test_template_picker_is_only_used_when_creating_spaces(self):
        for suffix in ('create/', 'manage/create/'):
            response = self.client.get(self.url(suffix), HTTP_X_WORK_MODAL='true')
            self.assertEqual(response.status_code, 200)
            html = response.json()['html']
            for key, template in TEMPLATES.items():
                self.assertIn(f'data-space-template="{key}"', html)
                self.assertIn(template['description'], html)
            self.assertIn('data-space-fields disabled', html)
            self.assertIn('data-space-create hidden', html)
        response = self.client.get(self.space_url('edit/'), HTTP_X_WORK_MODAL='true')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('data-space-wizard', response.json()['html'])
        self.assertIn('<select name="template"', response.json()['html'])

    def test_each_template_creates_its_matching_configuration(self):
        for number, (key, template) in enumerate(TEMPLATES.items()):
            with self.subTest(template=key):
                payload = {'name': f'Przestrzeń {key}', 'key': f'TPL{number}', 'kind': template['kind'], 'template': key, 'management': 'team', 'visibility': 'private'}
                response = self.client.post(self.url('create/'), payload, HTTP_X_WORK_MODAL='true')
                self.assertTrue(response.json()['saved'])
                space = Space.objects.get(workplace=self.workspace, key=payload['key'])
                self.assertEqual(space.template, key)
                self.assertEqual(space.kind, template['kind'])
                self.assertEqual(space.configuration.settings, template_settings(key))
                self.assertEqual(space.private_owner, self.owner)

    def test_template_error_keeps_selection_and_space_details(self):
        payload = {'name': 'Szkic rekrutacji', 'key': '!', 'kind': 'business', 'template': 'recruitment', 'management': 'team', 'visibility': 'private'}
        response = self.client.post(self.url('create/'), payload, HTTP_X_WORK_MODAL='true')
        self.assertEqual(response.status_code, 400)
        html = response.json()['html']
        self.assertIn('value="Szkic rekrutacji"', html)
        self.assertIn('value="recruitment"', html)
        self.assertIn('data-space-template-picker hidden', html)
        self.assertNotIn('data-space-fields disabled', html)
        payload.update(template='unknown')
        response = self.client.post(self.url('create/'), payload, HTTP_X_WORK_MODAL='true')
        self.assertEqual(response.status_code, 400)
        self.assertIn('data-space-fields disabled', response.json()['html'])
        self.assertFalse(Space.objects.filter(name=payload['name']).exists())

    def test_member_cannot_create_organization_managed_space(self):
        self.client.force_login(self.member)
        response = self.client.post(self.url('create/'), {'name': 'Nie', 'key': 'NO', 'kind': 'software', 'template': 'kanban', 'management': 'company', 'visibility': 'public'}, HTTP_X_WORK_MODAL='true')
        self.assertEqual(response.status_code, 400)

    def test_item_create_uses_actual_actor_and_same_task(self):
        self.client.force_login(self.member)
        response = self.client.post(self.space_url('items/create/'), {'title': 'Nowe wspólne zadanie', 'work_type': 'story', 'priority': 'high', 'points': 5}, HTTP_X_WORK_MODAL='true')
        self.assertTrue(response.json()['saved'])
        task = SpaceTask.objects.get(title='Nowe wspólne zadanie')
        self.assertEqual(task.space.user, self.owner)
        self.assertEqual(task.activities.get(action='created').actor, self.member)
        self.assertEqual(task.work_item.points, 5)
        self.assertEqual(task.work_item.space, self.space)
        self.assertContains(self.client.get(self.space_url('?view=list')), task.title)
        self.assertContains(self.client.get(self.space_url(f'?view=backlog')), task.title)

    def test_closed_status_and_history_are_synchronized(self):
        self.client.force_login(self.member)
        response = self.client.post(self.url(f'items/{self.item.pk}/action/'), {'action': 'status', 'status': 'closed'}, HTTP_X_WORK_ACTION='true')
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertTrue(self.task.is_completed)
        self.assertIsNotNone(self.task.completion_date)
        event = self.task.activities.get(action='status_changed')
        self.assertEqual(event.actor, self.member)
        self.client.post(self.url(f'items/{self.item.pk}/action/'), {'action': 'status', 'status': 'reopened'})
        self.task.refresh_from_db()
        self.assertFalse(self.task.is_completed)
        self.assertIsNone(self.task.completion_date)

    def test_disallowed_transition_rolls_back(self):
        config = self.space.configuration
        config.settings['statuses'][0]['transitions'] = ['in_progress']
        config.save()
        response = self.client.post(self.url(f'items/{self.item.pk}/action/'), {'action': 'status', 'status': 'closed'}, HTTP_X_WORK_ACTION='true')
        self.assertEqual(response.status_code, 400)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'new')
        self.assertFalse(self.task.activities.filter(action='status_changed').exists())

    def test_observer_cannot_edit_or_change_status(self):
        self.client.force_login(self.observer)
        self.assertEqual(self.client.get(self.url(f'items/{self.item.pk}/edit/')).status_code, 403)
        self.assertEqual(self.client.post(self.url(f'items/{self.item.pk}/action/'), {'action': 'status', 'status': 'closed'}).status_code, 403)
        self.assertEqual(self.client.get(self.space_url('configuration/')).status_code, 403)

    def test_hidden_groups_and_teams_never_grant_access(self):
        task = SpaceTask.objects.create(created_by=self.owner, space=self.space, title='Ukryte zadanie', visibility='private', private_owner=self.owner)
        team = Team.objects.create(workplace=self.workspace, owner=self.owner, name='Zespół')
        TeamMembership.objects.create(team=team, user=self.member)
        team.spaces.add(self.space)
        WorkItem.objects.filter(task=task).update(team=team)
        self.client.force_login(self.member)
        response = self.client.get(self.url(f'{team.pk}/', 'teams'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Ukryte zadanie')
        self.assertEqual(self.client.get(self.url(f'items/{task.work_item.pk}/edit/')).status_code, 404)

    def test_foreign_relations_are_rejected(self):
        team = Team.objects.create(workplace=self.foreign, owner=self.other, name='Obcy zespół')
        response = self.client.post(self.space_url('items/create/'), {'title': 'Nie', 'work_type': 'task', 'priority': 'medium', 'team': team.pk, 'assignee': self.other.pk}, HTTP_X_WORK_MODAL='true')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SpaceTask.objects.filter(title='Nie').exists())

    def test_stable_key_survives_task_number_compaction(self):
        second = SpaceTask.objects.create(created_by=self.owner, space=self.section, title='Drugie')
        key = second.work_item.key
        self.task.delete()
        second.refresh_from_db()
        self.assertEqual(second.work_item.key, key)
        third = SpaceTask.objects.create(created_by=self.owner, space=self.section, title='Trzecie')
        self.assertNotEqual(third.work_item.key, key)

    def test_sprint_completion_returns_unfinished_to_backlog(self):
        sprint = Sprint.objects.create(space=self.space, name='Sprint 1', start_on=date(2026, 10, 1), end_on=date(2026, 10, 14))
        WorkItem.objects.filter(pk=self.item.pk).update(sprint=sprint)
        self.client.post(self.space_url(f'sprints/{sprint.pk}/action/'), {'action': 'start'})
        sprint.refresh_from_db()
        self.assertEqual(sprint.state, 'active')
        self.assertContains(self.client.get(self.space_url('?view=board')), self.task.title)
        self.client.post(self.space_url(f'sprints/{sprint.pk}/action/'), {'action': 'close'})
        self.item.refresh_from_db()
        sprint.refresh_from_db()
        self.assertEqual(sprint.state, 'closed')
        self.assertIsNone(self.item.sprint_id)
        self.assertTrue(self.item.in_backlog)

    def test_team_lifecycle_and_last_admin(self):
        response = self.client.post(self.url('create/', 'teams'), {'name': 'Programiści', 'spaces': [self.space.pk]}, HTTP_X_WORK_MODAL='true')
        self.assertTrue(response.json()['saved'])
        team = Team.objects.get(name='Programiści')
        self.assertTrue(team.spaces.filter(pk=self.space.pk).exists())
        owner_membership = team.memberships.get(user=self.owner)
        self.client.post(self.url(f'{team.pk}/members/{owner_membership.pk}/remove/', 'teams'))
        self.assertTrue(team.memberships.filter(pk=owner_membership.pk).exists())
        response = self.client.post(self.url(f'{team.pk}/members/', 'teams'), {'person': self.member.pk, 'role': 'member'}, HTTP_X_WORK_MODAL='true')
        self.assertTrue(response.json()['saved'])
        self.assertEqual(self.client.get(self.url(f'{team.pk}/', 'teams')).status_code, 200)
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(self.url(f'{team.pk}/edit/', 'teams')).status_code, 403)

    def test_membership_revocation_removes_all_access(self):
        self.client.force_login(self.member)
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.member).update(is_active=False)
        response = self.client.get(self.space_url())
        self.assertEqual(response.status_code, 302)
        self.assertNotIn(f'/spaces/{self.space.pk}/', response['Location'])

    def test_csrf_is_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(self.url('create/'), {}).status_code, 403)
        self.assertEqual(client.post(self.url(f'items/{self.item.pk}/action/'), {'action': 'status', 'status': 'closed'}).status_code, 403)


    def test_publishing_space_preserves_private_task_memberships(self):
        self.task.visibility, self.task.private_owner = 'private', self.owner
        self.task.save()
        SpaceTaskMembership.objects.create(task=self.task, user=self.member, role='member')
        response = self.client.post(self.space_url('edit/'), {'name': 'Produkt', 'visibility': 'public'}, HTTP_X_WORK_MODAL='true')
        self.assertTrue(response.json()['saved'])
        self.assertTrue(self.task.memberships.filter(user=self.member).exists())


    def test_task_cannot_move_out_of_its_own_space(self):
        from django.core.exceptions import ValidationError
        from django.db import transaction
        original_key = self.item.key
        self.task.space = self.hidden_project
        with self.assertRaises(ValidationError), transaction.atomic():
            self.task.save()
        self.item.refresh_from_db()
        self.assertEqual(self.item.space, self.space)
        self.assertEqual(self.item.key, original_key)


    def test_foreign_parent_relation_is_rejected(self):
        from django.core.exceptions import ValidationError
        from django.db import transaction
        parent = SpaceTask.objects.create(space=self.foreign_project, created_by=self.other, title='Obcy rodzic')
        with self.assertRaises(ValidationError), transaction.atomic():
            SpaceTask.objects.create(space=self.space, created_by=self.owner, parent=parent, title='Niepoprawne powiązanie')


    def test_configuration_updates_workflow_and_rejects_stale_or_used_removal(self):
        url = self.space_url('configuration/')
        response = self.client.get(url)
        payload = {'revision': response.context['revision']}
        for group in response.context['sets']:
            formset = group['formset']
            payload.update({f'{formset.prefix}-TOTAL_FORMS': str(formset.total_form_count()), f'{formset.prefix}-INITIAL_FORMS': str(formset.initial_form_count())})
            for i, form in enumerate(formset.extra_forms, formset.initial_form_count()):
                for key, field in form.fields.items():
                    if field.initial is not None and not isinstance(field.initial, bool):
                        payload[f'{formset.prefix}-{i}-{key}'] = field.initial
            for i, initial in enumerate(formset.initial):
                for key, value in initial.items():
                    payload[f'{formset.prefix}-{i}-{key}'] = value if value is not None else ''
        payload['statuses-0-label'] = 'Zaplanowane'
        payload['statuses-0-transitions'] = ['in_progress']
        self.assertEqual(self.client.post(url, payload).status_code, 302)
        self.assertContains(self.client.post(url, payload), 'Konfiguracja zmieniła się', status_code=400)
        self.space.configuration.refresh_from_db()
        self.assertEqual(self.space.configuration.settings['statuses'][0]['label'], 'Zaplanowane')
        response = self.client.post(self.url(f'items/{self.item.pk}/action/'), {'action': 'status', 'status': 'closed'}, HTTP_X_WORK_ACTION='true')
        self.assertEqual(response.status_code, 400)

    def test_deleting_workspace_cascades_shared_configuration(self):
        workspace = self.workspace
        workspace.delete()
        self.assertFalse(Space.objects.filter(pk=self.space.pk).exists())


    def test_edit_date_and_completed_sprint_are_preserved_in_form(self):
        sprint = Sprint.objects.create(space=self.space, name='Zamknięty', start_on=date(2026, 10, 1), end_on=date(2026, 10, 14), state='closed')
        WorkItem.objects.filter(pk=self.item.pk).update(start_at=timezone.make_aware(datetime(2026, 10, 3)), sprint=sprint)
        response = self.client.get(self.url(f'items/{self.item.pk}/edit/'), HTTP_X_WORK_MODAL='true')
        self.assertIn('value="2026-10-03T00:00"', response.json()['html'])
        self.assertIn('Zamknięty', response.json()['html'])

    def test_team_photo_is_private_and_cleans_up_on_rollback_and_delete(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from django.core.files.storage import FileSystemStorage
        from core.test_comment_images import photo
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        field = Team._meta.get_field('photo')
        self.addCleanup(setattr, field, 'storage', field.storage)
        field.storage = FileSystemStorage(directory.name)
        url = self.url('create/', 'teams')
        bad = self.client.post(url, {'name': 'Zespół ze zdjęciem', 'photo': photo(content=b'not an image')}, HTTP_X_WORK_MODAL='true')
        self.assertEqual(bad.status_code, 400)
        with patch('spaces.teams.TeamMembership.objects.create', side_effect=RuntimeError('rollback')):
            with self.assertRaises(RuntimeError):
                self.client.post(url, {'name': 'Rollback', 'photo': photo()}, HTTP_X_WORK_MODAL='true')
        self.assertFalse(list(Path(directory.name).rglob('*.png')))
        self.assertFalse(Team.objects.filter(name='Rollback').exists())
        result = self.client.post(url, {'name': 'Zespół ze zdjęciem', 'photo': photo()}, HTTP_X_WORK_MODAL='true')
        self.assertTrue(result.json()['saved'])
        team = Team.objects.get(name='Zespół ze zdjęciem')
        name = team.photo.name
        response = self.client.get(self.url(f'{team.pk}/photo/', 'teams'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertTrue(b''.join(response.streaming_content))
        self.assertEqual(Client().get(self.url(f'{team.pk}/photo/', 'teams')).status_code, 302)
        with self.captureOnCommitCallbacks(execute=True):
            team.delete()
        self.assertFalse(field.storage.exists(name))
