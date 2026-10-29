"""Autosave uses the existing task form, live values, ACL and file transaction."""
import json
from datetime import date, datetime, timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from tasks.models import TaskTag
from . import test_independent_tasks as fixtures
from .models import SpaceTask, SpaceTaskFile, SpaceTaskMembership, Sprint, Team


class TaskAutosaveTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.IndependentTaskTests.setUpTestData.__func__(cls)

    login = fixtures.IndependentTaskTests.login
    url = fixtures.IndependentTaskTests.url
    task_url = fixtures.IndependentTaskTests.task_url

    def setUp(self):
        self.login(self.owner)

    def save(self, fields, url=None, **data):
        return self.client.post(url or self.task_url('?view=backlog&tab=history'),
            {'action': 'save', 'autosave_fields': json.dumps(fields), **data},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def test_json_save_updates_history_author_and_keeps_unsent_values(self):
        self.login(self.member)
        response = self.save(['title'], title='Nowy tytuł')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertEqual(response.json()['task']['title'], 'Nowy tytuł')
        self.assertIn('zaktualizował zadanie', response.json()['activity_html'])
        self.task.refresh_from_db()
        self.assertEqual(self.task.priority, 'medium')
        activity = self.task.activities.get(action='updated')
        self.assertEqual(activity.actor, self.member)
        self.assertEqual([change['field'] for change in activity.metadata['changes']], ['tytuł'])

    def test_only_changed_fields_preserve_concurrent_properties_and_planning(self):
        due = timezone.now().replace(second=17, microsecond=123456) + timedelta(days=3)
        self.task.priority, self.task.due_at, self.task.description = 'high', due, '  Zachowany opis  '
        self.task.save()
        sprint = Sprint.objects.create(space=self.space, name='Aktualny sprint', start_on=timezone.localdate(), end_on=timezone.localdate()+timedelta(days=7))
        item = self.task.work_item
        item.sprint, item.points, item.in_backlog, item.status = sprint, 8, False, 'in_progress'
        item.save()
        response = self.save(['description'], description='Zapisany opis', priority='low', due_at='', status='new', sprint='', points='1', in_backlog='on')
        self.assertEqual(response.status_code, 200, response.content)
        self.task.refresh_from_db(); item.refresh_from_db()
        self.assertEqual(self.task.description, 'Zapisany opis')
        self.assertEqual(self.task.priority, 'high')
        self.assertEqual(self.task.due_at, due)
        self.assertEqual((item.sprint, item.points, item.in_backlog, item.status), (sprint, 8, False, 'in_progress'))
        count = self.task.activities.count()
        response = self.save(['title'], title=self.task.title)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.task.activities.count(), count)
        self.task.description = '  Zachowany opis  '
        self.task.save()
        response = self.save(['title'], title='Nowy tytuł')
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.description, '  Zachowany opis  ')

    def test_status_completion_reopen_and_noop_history(self):
        response = self.save(['status'], status='closed')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['task']['completion_date'])
        self.task.refresh_from_db()
        self.assertTrue(self.task.is_completed)
        count = self.task.activities.count()
        response = self.save(['status'], status='closed')
        self.assertEqual(response.json()['activity_html'], '')
        self.assertEqual(self.task.activities.count(), count)
        response = self.save(['status'], status='reopened')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['task']['completion_date'], '')
        self.assertEqual(self.task.activities.filter(action='status_changed', actor=self.owner).count(), 2)

    @override_settings(TIME_ZONE='Europe/Warsaw')
    def test_schedule_controls_and_api_show_existing_dates_and_allow_empty_start(self):
        self.task.due_at = datetime(2026, 11, 8, 16, 37, tzinfo=ZoneInfo('Europe/Warsaw'))
        self.task.save(update_fields=['due_at'])
        item = self.task.work_item
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
        for start in (None, datetime(2026, 10, 29, 9, 15, tzinfo=ZoneInfo('Europe/Warsaw'))):
            item.start_at = start
            item.save(update_fields=['start_at'])
            for target in (self.task_url(), f'/space/{self.space.slug}/tasks/{self.key}/'):
                with self.subTest(start=start, target=target):
                    response = self.client.get(api, {'url': target})
                    self.assertEqual(response.status_code, 200)
                    data = response.json()['data']
                    fields = {field['name']: field for field in data['form']['fields']}
                    self.assertEqual(fields['start_at']['label'], 'Data rozpoczęcia')
                    self.assertEqual(fields['start_at']['type'], 'datetime-local')
                    self.assertEqual(fields['start_at']['value'], start.strftime('%Y-%m-%dT%H:%M') if start else None)
                    self.assertFalse(fields['start_at']['hidden'])
                    self.assertEqual(fields['due_at']['label'], 'Termin zakończenia')
                    self.assertEqual(fields['due_at']['value'], '2026-11-08T16:37')
                    self.assertEqual(data['item']['start_on'], start.date().isoformat() if start else None)
                    self.assertEqual(data['item']['end_on'], '2026-11-08')
                    html = self.client.get(target, follow=True)
                    self.assertContains(html, 'name="start_at"', count=1)
                    self.assertContains(html, '<label for="id_start_at">Data rozpoczęcia</label>')
                    self.assertContains(html, '<label for="id_due_at">Termin zakończenia</label>')
        self.login(self.observer)
        data = self.client.get(api, {'url': self.task_url()}).json()['data']
        fields = {field['name']: field for field in data['form']['fields']}
        self.assertTrue(fields['start_at']['disabled'])
        self.assertTrue(fields['due_at']['disabled'])

    @override_settings(TIME_ZONE='Europe/Warsaw')
    def test_schedule_autosave_records_date_values_actor_and_noop(self):
        self.login(self.member)
        values = {'start_at': '2026-10-29T09:15', 'due_at': '2026-11-08T18:45'}
        response = self.save(['start_at', 'due_at'], **values)
        self.assertEqual(response.status_code, 200, response.content)
        self.task.refresh_from_db()
        self.assertEqual(timezone.localtime(self.task.work_item.start_at).strftime('%Y-%m-%dT%H:%M'), '2026-10-29T09:15')
        self.assertEqual(timezone.localtime(self.task.due_at).strftime('%Y-%m-%dT%H:%M'), values['due_at'])
        self.assertEqual(self.task.status, 'new')
        self.assertIsNone(self.task.completion_date)
        activity = self.task.activities.get(action='updated')
        self.assertEqual(activity.actor, self.member)
        self.assertEqual(activity.metadata['changes'], [
            {'field': 'planowane rozpoczęcie', 'from_label': '—', 'to_label': '29.10.2026 09:15'},
            {'field': 'termin wykonania', 'from_label': '—', 'to_label': '08.11.2026 18:45'},
        ])
        count = self.task.activities.count()
        self.assertEqual(self.save(['start_at', 'due_at'], **values).status_code, 200)
        self.assertEqual(self.task.activities.count(), count)

    @override_settings(TIME_ZONE='Europe/Warsaw')
    def test_schedule_can_clear_each_date_and_preserves_unedited_due_time(self):
        due = datetime(2026, 11, 8, 16, 37, 12, 987654, tzinfo=ZoneInfo('Europe/Warsaw'))
        self.task.due_at = due
        self.task.save(update_fields=['due_at'])
        response = self.save(['start_at'], start_at='2026-10-29T09:15', due_at='')
        self.assertEqual(response.status_code, 200, response.content)
        self.task.refresh_from_db()
        self.assertEqual(self.task.due_at, due)
        self.assertEqual(timezone.localtime(self.task.work_item.start_at).strftime('%Y-%m-%dT%H:%M'), '2026-10-29T09:15')
        self.assertEqual(self.save(['start_at'], start_at='').status_code, 200)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.work_item.start_at)
        self.assertEqual(self.task.due_at, due)
        self.assertEqual(self.save(['start_at'], start_at='2026-10-29T09:15').status_code, 200)
        self.assertEqual(self.save(['due_at'], due_at='').status_code, 200)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.due_at)
        self.assertEqual(timezone.localtime(self.task.work_item.start_at).strftime('%Y-%m-%dT%H:%M'), '2026-10-29T09:15')
        self.assertEqual(self.save(['start_at'], start_at='').status_code, 200)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.work_item.start_at)
        self.assertIsNone(self.task.due_at)

    @override_settings(TIME_ZONE='Europe/Warsaw')
    def test_schedule_invalid_date_or_reversed_range_does_not_partially_save(self):
        due = datetime(2026, 11, 8, 16, 37, tzinfo=ZoneInfo('Europe/Warsaw'))
        self.task.due_at = due
        self.task.save(update_fields=['due_at'])
        item = self.task.work_item
        item.start_at = datetime(2026, 10, 29, 9, 15, tzinfo=ZoneInfo('Europe/Warsaw'))
        item.save(update_fields=['start_at'])
        count = self.task.activities.count()
        for field, value, error_field in (
            ('start_at', '2026-11-09T09:15', 'due_at'),
            ('due_at', '2026-10-28T23:59', 'due_at'),
            ('start_at', '2026-02-30', 'start_at'),
        ):
            with self.subTest(field=field, value=value):
                response = self.save(['title', field], title='Nie zapisuj', **{field: value})
                self.assertEqual(response.status_code, 400)
                self.assertIn(error_field, response.json()['errors'])
                self.task.refresh_from_db()
                item.refresh_from_db()
                self.assertEqual(self.task.title, 'Praca w przestrzeni')
                self.assertEqual(self.task.due_at, due)
                self.assertEqual(timezone.localtime(item.start_at).strftime('%Y-%m-%dT%H:%M'), '2026-10-29T09:15')
                self.assertEqual(self.task.activities.count(), count)

    @override_settings(TIME_ZONE='Europe/Warsaw')
    def test_schedule_round_trip_between_task_api_and_timeline(self):
        self.login(self.member)
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
        for base in (self.url(), f'/space/{self.space.slug}/'):
            with self.subTest(base=base):
                target = base + f'tasks/{self.key}/'
                response = self.client.post(api + '?' + urlencode({'url': target}), {
                    'action': 'save', 'autosave_fields': '["start_at", "due_at"]',
                    'start_at': '2026-10-29T09:15', 'due_at': '2026-11-08T18:45',
                })
                self.assertEqual(response.status_code, 200, response.content)
                timeline = self.client.get(api, {'url': base + '?view=timeline'}).json()['data']
                row = next(row for row in timeline['items'] if row['task_id'] == self.task.pk)
                self.assertEqual((row['start_on'], row['end_on']), ('2026-10-29', '2026-11-08'))
                response = self.client.post(api + '?' + urlencode({'url': row['update_dates_url']}), {
                    'start_on': '2026-10-30', 'end_on': '2026-11-09',
                    'source_start_at': row['start_at'], 'source_due_at': row['due_at'],
                })
                self.assertEqual(response.status_code, 200, response.content)
                page = self.client.get(api, {'url': target}).json()['data']
                fields = {field['name']: field for field in page['form']['fields']}
                self.assertEqual(fields['start_at']['value'], '2026-10-30T09:15')
                self.assertEqual(fields['due_at']['value'], '2026-11-09T18:45')
                self.assertEqual((page['item']['start_on'], page['item']['end_on']), ('2026-10-30', '2026-11-09'))
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'new')
        self.assertIsNone(self.task.completion_date)

    @override_settings(TIME_ZONE='Europe/Warsaw')
    def test_schedule_same_day_range_and_invalid_dst_wall_times(self):
        for start, due in (
            ('2026-10-29T18:00', '2026-10-29T09:00'),
            ('2026-03-29T02:30', '2026-03-29T17:00'),
            ('2026-10-25T02:30', '2026-10-25T17:00'),
            ('2026-10-29', '2026-10-29T17:00'),
            ('2026-10-29T09:00', '2026-10-29'),
        ):
            with self.subTest(start=start, due=due):
                response = self.save(['start_at', 'due_at'], start_at=start, due_at=due)
                self.assertEqual(response.status_code, 400, response.content)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.work_item.start_at)
        self.assertIsNone(self.task.due_at)
        self.assertEqual(self.save(['start_at', 'due_at'], start_at='2026-10-29T09:00', due_at='2026-10-29T17:00').status_code, 200)

    @override_settings(TIME_ZONE='Europe/Warsaw')
    def test_autosave_other_property_preserves_exact_repeated_hour_instants(self):
        zone = ZoneInfo('Europe/Warsaw')
        item = self.task.work_item
        item.start_at = datetime(2026, 10, 25, 2, 45, 12, 345678, tzinfo=zone, fold=0)
        item.save(update_fields=['start_at'])
        self.task.due_at = datetime(2026, 10, 25, 2, 15, 42, 876543, tzinfo=zone, fold=1)
        self.task.save(update_fields=['due_at'])
        original = item.start_at, self.task.due_at
        response = self.save(['title'], title='Zachowane godziny')
        self.assertEqual(response.status_code, 200, response.content)
        item.refresh_from_db()
        self.task.refresh_from_db()
        self.assertEqual(item.start_at.timestamp(), original[0].timestamp())
        self.assertEqual(self.task.due_at.timestamp(), original[1].timestamp())
        response = self.save(['start_at'], start_at='2026-10-25T02:30:00+01:00')
        self.assertEqual(response.status_code, 400, response.content)
        item.refresh_from_db()
        self.assertEqual(item.start_at.timestamp(), original[0].timestamp())

    @override_settings(TIME_ZONE='Europe/Warsaw')
    def test_create_and_edit_task_keep_date_and_time_and_reject_reversed_range(self):
        values = {'title': 'Z godzinami', 'work_type': 'task', 'priority': 'medium',
                  'start_at': '2026-10-29T09:15', 'due_at': '2026-10-29T17:45'}
        response = self.client.post(self.url('items/create/'), values)
        self.assertEqual(response.status_code, 302)
        task = SpaceTask.objects.get(space=self.space, title='Z godzinami')
        self.assertEqual(timezone.localtime(task.work_item.start_at).time().isoformat(), '09:15:00')
        self.assertEqual(timezone.localtime(task.due_at).time().isoformat(), '17:45:00')
        target = self.url(f'tasks/{task.work_item.key}/edit/')
        response = self.client.post(target, {**values, 'start_at': '2026-10-29T10:30'})
        self.assertEqual(response.status_code, 302)
        task.refresh_from_db()
        self.assertEqual(timezone.localtime(task.work_item.start_at).time().isoformat(), '10:30:00')
        response = self.client.post(target, {**values, 'start_at': '2026-10-29T18:00'})
        self.assertEqual(response.status_code, 400)
        task.refresh_from_db()
        self.assertEqual(timezone.localtime(task.work_item.start_at).time().isoformat(), '10:30:00')

    def test_former_assignee_is_preserved_but_cannot_be_selected_again(self):
        self.task.assignee = self.member
        self.task.save()
        WorkplaceMembership.objects.get(workplace=self.workspace, user=self.member).delete()
        for url in (self.task_url(), f'/space/{self.space.slug}/tasks/{self.key}/'):
            with self.subTest(url=url):
                response = self.save(['title'], url=url, title='Zachowane przypisanie', assignee=self.observer.pk)
                self.assertEqual(response.status_code, 200, response.content)
                self.task.refresh_from_db()
                self.assertEqual((self.task.title, self.task.assignee_id), ('Zachowane przypisanie', self.member.pk))
        response = self.save(['title', 'assignee'], title='Niedozwolona zmiana', assignee=self.member.pk)
        self.assertEqual(response.status_code, 400)
        self.assertIn('assignee', response.json()['errors'])
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Zachowane przypisanie')
        self.assertEqual(self.save(['assignee'], assignee='').status_code, 200)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.assignee_id)

    def test_hidden_epic_is_preserved_without_becoming_a_choice_in_api(self):
        from urllib.parse import quote
        from workplaces.services import scoped_workplace_app_path
        epic = SpaceTask.objects.create(space=self.space, title='Poufny epik', created_by=self.owner,
                                        visibility='private', private_owner=self.owner)
        epic_item = epic.work_item
        epic_item.work_type = 'epic'
        epic_item.save()
        item = self.task.work_item
        item.epic = epic_item
        item.save()
        self.login(self.member)
        target = self.task_url('?view=list')
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') + '?url=' + quote(target, safe='')
        response = self.client.post(api, {'action': 'save', 'autosave_fields': '["title"]',
                                          'title': 'Dostępne zadanie', 'epic': ''})
        self.assertEqual(response.status_code, 200, response.content)
        self.task.refresh_from_db(); item.refresh_from_db()
        self.assertEqual((self.task.title, item.epic_id), ('Dostępne zadanie', epic_item.pk))
        response = self.client.get(api)
        self.assertEqual(response.status_code, 200, response.content)
        field = next(field for field in response.json()['data']['form']['fields'] if field['name'] == 'epic')
        self.assertNotIn(str(epic_item.pk), {choice['value'] for choice in field['choices']})
        self.assertNotIn('Poufny epik', response.content.decode())
        response = self.save(['epic'], epic=epic_item.pk)
        self.assertEqual(response.status_code, 400)
        self.assertIn('epic', response.json()['errors'])
        self.assertEqual(self.save(['epic'], epic='').status_code, 200)
        item.refresh_from_db()
        self.assertIsNone(item.epic_id)

    def test_unlinked_team_is_preserved_but_new_assignments_remain_scoped(self):
        team = Team.objects.create(workplace=self.workspace, owner=self.owner, created_by=self.owner, name='Odłączony zespół')
        item = self.task.work_item
        item.team = team
        item.save()
        response = self.save(['description'], description='Zmieniony opis')
        self.assertEqual(response.status_code, 200, response.content)
        item.refresh_from_db()
        self.assertEqual(item.team_id, team.pk)
        response = self.save(['team'], team=team.pk)
        self.assertEqual(response.status_code, 400)
        self.assertIn('team', response.json()['errors'])

    def test_preserved_relations_still_participate_in_cross_field_validation(self):
        epic = SpaceTask.objects.create(space=self.space, title='Epik', created_by=self.owner)
        epic_item = epic.work_item
        epic_item.work_type = 'epic'
        epic_item.save()
        item = self.task.work_item
        item.epic = epic_item
        item.save()
        response = self.save(['work_type'], work_type='epic')
        self.assertEqual(response.status_code, 400)
        self.assertIn('epic', response.json()['errors'])
        item.refresh_from_db()
        self.assertEqual(item.work_type, 'task')

    def test_clearing_tags_and_optional_fields_and_preserving_custom_zero(self):
        tag = TaskTag.objects.create(name='Tag', user=self.owner, workplace=self.workspace, space=self.space)
        self.task.tags.add(tag)
        self.task.assignee = self.member
        self.task.save()
        self.config.settings['fields'] = [{'key': 'cost', 'label': 'Koszt', 'type': 'number', 'required': False}]
        self.config.save()
        item = self.task.work_item
        item.custom_values = {'cost': '0'}
        item.save()
        response = self.save(['tags', 'assignee'], assignee='')
        self.assertEqual(response.status_code, 200, response.content)
        self.task.refresh_from_db(); item.refresh_from_db()
        self.assertIsNone(self.task.assignee)
        self.assertFalse(self.task.tags.exists())
        self.assertEqual(item.custom_values, {'cost': '0'})

    def test_invalid_title_status_and_date_do_not_partially_save(self):
        for fields, data in [(['title', 'status'], {'title': '', 'status': 'closed'}),
                             (['title', 'status'], {'title': 'Szkic', 'status': 'unknown'}),
                             (['title', 'due_at'], {'title': 'Szkic', 'due_at': 'bad'})]:
            response = self.save(fields, **data)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()['status'], 'error')
            self.task.refresh_from_db()
            self.assertEqual(self.task.title, 'Praca w przestrzeni')
            self.assertEqual(self.task.status, 'new')
        self.assertIn('due_at', response.json()['errors'])
        self.assertFalse(self.task.activities.filter(action='updated').exists())

    def test_required_custom_field_can_be_completed_with_pending_autosave_fields(self):
        from urllib.parse import urlencode
        from workplaces.services import scoped_workplace_app_path
        self.config.settings['fields'] = [{'key': 'cost', 'label': 'Koszt', 'type': 'number', 'required': True}]
        self.config.save()
        api = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') + '?' + urlencode({'url': self.task_url()})
        response = self.client.post(api, {'action': 'save', 'autosave_fields': '["title"]', 'title': 'Szkic tytułu'})
        self.assertEqual(response.status_code, 400)
        fields = {field['name']: field for field in response.json()['data']['form']['fields']}
        self.assertEqual(fields['title']['value'], 'Szkic tytułu')
        self.assertTrue(fields['custom_cost']['required'])
        self.assertTrue(fields['custom_cost']['errors'])
        self.assertFalse(fields['custom_cost']['disabled'])
        response = self.client.post(api, {'action': 'save', 'autosave_fields': '["title", "custom_cost"]',
                                          'title': 'Szkic tytułu', 'custom_cost': '0'})
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Szkic tytułu')
        self.assertEqual(self.task.work_item.custom_values, {'cost': '0'})
        self.login(self.observer)
        payload = self.client.get(api).json()['data']
        self.assertTrue(next(field for field in payload['form']['fields'] if field['name'] == 'custom_cost')['disabled'])
        self.assertEqual(self.client.post(api, {'action': 'save', 'autosave_fields': '["custom_cost"]', 'custom_cost': '1'}).status_code, 403)

    def test_attachments_return_saved_cards_and_invalid_upload_rolls_back(self):
        with TemporaryDirectory() as root, patch.object(SpaceTaskFile._meta.get_field('file'), 'storage', FileSystemStorage(location=root)):
            response = self.save(['title', 'files'], title='Szkic', files=SimpleUploadedFile('blocked.exe', b'bad'))
            self.assertEqual(response.status_code, 400)
            self.task.refresh_from_db()
            self.assertEqual(self.task.title, 'Praca w przestrzeni')
            self.assertFalse(self.task.attachments.exists())
            response = self.save(['files'], files=SimpleUploadedFile('notatka.txt', b'Zalacznik'))
            self.assertEqual(response.status_code, 200)
            self.assertIn('notatka.txt', response.json()['attachments_html'])
            self.assertIn('tasks/' + self.key + '/files/', response.json()['attachments_html'])
            self.assertEqual(self.task.attachments.count(), 1)
            self.assertEqual(self.client.get(self.task_url(f'files/{self.task.attachments.get().pk}/')).status_code, 200)

    def test_observer_private_task_and_wrong_workspace_cannot_save(self):
        self.login(self.observer)
        self.assertEqual(self.save(['title'], title='Obserwator').status_code, 403)
        self.task.visibility, self.task.private_owner = 'private', self.owner
        self.task.save()
        self.login(self.member)
        self.assertEqual(self.save(['title'], title='Niedostępne').status_code, 404)
        self.login(self.owner)
        other = create_workplace_for_user(self.owner, 'Inny Workspace')
        self.assertEqual(self.save(['title'], url=f'/workplaces/{other.slug}/space/{self.space.slug}/tasks/{self.key}/', title='Obce').status_code, 404)

    def test_visibility_updates_member_panel_and_clears_private_memberships(self):
        self.assertEqual(self.save(['visibility'], visibility='private').status_code, 200)
        self.task.refresh_from_db()
        SpaceTaskMembership.objects.create(task=self.task, user=self.member)
        response = self.save(['visibility'], visibility='public')
        self.assertEqual(response.status_code, 200)
        self.assertIn('members', response.json()['team'])
        self.assertFalse(self.task.memberships.exists())

    def test_malformed_field_list_is_rejected_and_csrf_is_required(self):
        for fields in ['title', {'title': True}, ['bad'], [42]]:
            self.assertEqual(self.save(fields, title='Bad').status_code, 400)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(self.task_url(), {'action': 'save', 'autosave_fields': '["title"]', 'title': 'CSRF'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest').status_code, 403)

    def test_plain_and_scoped_addresses_and_regular_post_fallback(self):
        for url in [self.task_url(), f'/space/{self.space.slug}/tasks/{self.key}/']:
            response = self.save(['title'], url=url, title='Zapis adresu')
            self.assertEqual(response.status_code, 200)
        response = self.client.post(self.task_url(), {'action': 'save', 'title': 'Zwykły zapis', 'priority': 'medium', 'work_type': 'task'})
        self.assertEqual(response.status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Zwykły zapis')
