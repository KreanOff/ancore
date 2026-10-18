from datetime import UTC, datetime
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import Client, TestCase

from spaces.forms import WorkLogForm
from spaces.models import SpaceTaskWorkLog
from spaces.testing import make_space, make_task
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class SpaceTaskWorkLogTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='log-owner', email='log-owner@example.test')
        cls.member = users.objects.create_user(username='log-member', email='log-member@example.test')
        cls.outsider = users.objects.create_user(username='log-outsider', email='log-outsider@example.test')
        cls.team = create_workplace_for_user(cls.owner, 'Log team')
        cls.other_team = create_workplace_for_user(cls.owner, 'Other log team')
        WorkplaceMembership.objects.create(workplace=cls.team, user=cls.member, role='member')
        cls.space = make_space(user=cls.owner, workplace=cls.team, name='Dziennik pracy')
        cls.task = make_task(user=cls.owner, workplace=cls.team, space=cls.space, title='Work log target')

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.team.pk
        session.save()

    def url(self, task=None, scoped=True):
        task = task or self.task
        suffix = f'{task.space.slug}/tasks/{task.work_item.key}/'
        return scoped_workplace_app_path(self.team, 'space', suffix) if scoped else f'/space/{suffix}'

    def post(self, action='add_work_log', task=None, scoped=True, **data):
        task = task or self.task
        return self.client.post(self.url(task, scoped), {
            'action': action, 'task_pk': task.pk,
            'worklog-started_at': '2026-09-24T09:00',
            'worklog-ended_at': '2026-09-24T10:30',
            'worklog-description': 'Przygotowanie planu', **data,
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def test_create_uses_actor_and_calculates_duration_without_changing_task(self):
        for scoped in (False, True):
            with self.subTest(scoped=scoped):
                response = self.post(scoped=scoped, author=self.outsider.pk, duration_minutes=999)
                self.assertEqual(response.status_code, 200)
                entry = self.task.work_logs.latest('pk')
                self.assertEqual(entry.author, self.member)
                self.assertEqual(entry.duration_minutes, 90)
                self.assertEqual(entry.started_at.hour, 7)
                activity = self.task.activities.filter(action='work_log_added').latest('pk')
                self.assertEqual(activity.actor, self.member)
                self.assertIn('90 min', response.json()['work_log_html'])
        self.task.refresh_from_db()
        self.assertEqual(self.task.space, self.space)
        self.assertEqual(self.task.title, 'Work log target')
        self.assertEqual(self.task.status, 'new')

    def test_edit_and_delete_keep_original_author_and_update_totals(self):
        self.post()
        entry = self.task.work_logs.get()
        self.client.force_login(self.owner)
        response = self.post('edit_work_log', work_log_id=entry.pk, **{'worklog-ended_at': '2026-09-24T11:00'})
        self.assertEqual(response.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(entry.author, self.member)
        self.assertEqual(entry.duration_minutes, 120)
        self.assertIn('120 min', response.json()['work_log_html'])
        self.assertEqual(self.task.activities.get(action='work_log_updated').actor, self.owner)
        response = self.post('delete_work_log', work_log_id=entry.pk)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.task.work_logs.exists())
        self.assertIn('Brak wpisów', response.json()['work_log_html'])
        self.assertEqual(self.task.activities.get(action='work_log_deleted').actor, self.owner)

    def test_invalid_data_preserves_entry_and_returns_field_errors(self):
        invalid = [
            {'worklog-started_at': ''}, {'worklog-ended_at': ''},
            {'worklog-ended_at': '2026-09-24T08:59'}, {'worklog-ended_at': '2026-09-24T09:00'},
            {'worklog-description': '   '}, {'worklog-description': 'x' * 4001},
            {'worklog-started_at': 'bad date'}, {'worklog-started_at': '2026-09-24T09:00:30'},
            {'worklog-started_at': '2026-03-29T02:30'}, {'worklog-started_at': '2026-10-25T02:30'},
        ]
        for values in invalid:
            with self.subTest(values=str(values)[:100]):
                response = self.post(**values)
                self.assertEqual(response.status_code, 400)
                self.assertIn('form_html', response.json())
        self.assertFalse(self.task.work_logs.exists())
        self.post()
        entry = self.task.work_logs.get()
        response = self.post('edit_work_log', work_log_id=entry.pk, **{'worklog-ended_at': '2026-09-24T08:00'})
        self.assertEqual(response.status_code, 400)
        entry.refresh_from_db()
        self.assertEqual(entry.duration_minutes, 90)

    def test_midnight_and_daylight_saving_intervals(self):
        for start, end, minutes in [
            ('2026-09-24T23:30', '2026-09-25T01:00', 90),
            ('2026-03-29T01:30', '2026-03-29T03:30', 60),
            ('2026-10-25T01:30', '2026-10-25T03:30', 180),
        ]:
            with self.subTest(start=start):
                response = self.post(**{'worklog-started_at': start, 'worklog-ended_at': end})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.task.work_logs.latest('pk').duration_minutes, minutes)
                form = WorkLogForm({'started_at': start, 'ended_at': end, 'description': 'Praca'})
                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(form.save(commit=False).duration_minutes, minutes)

    def test_subtask_has_separate_log(self):
        subtask = make_task(user=self.owner, workplace=self.team, parent=self.task, title='Child')
        self.assertEqual(self.post(task=subtask).status_code, 200)
        self.assertEqual(subtask.work_logs.count(), 1)
        self.assertFalse(self.task.work_logs.exists())
        self.assertContains(self.client.get(self.url(subtask)), 'Dziennik pracy')

    def test_duration_only_calculates_interval_ending_now(self):
        now = datetime(2026, 9, 24, 14, 0, 37, tzinfo=UTC)
        with patch('core.work_logs.timezone.now', return_value=now):
            response = self.post(**{
                'worklog-calculation_mode': 'duration', 'worklog-hours': 2, 'worklog-minutes': 15,
                'worklog-started_at': '', 'worklog-ended_at': '',
            })
        self.assertEqual(response.status_code, 200)
        entry = self.task.work_logs.get()
        self.assertEqual(entry.duration_minutes, 135)
        self.assertEqual(entry.started_at, datetime(2026, 9, 24, 11, 45, tzinfo=UTC))
        self.assertEqual(entry.ended_at, now.replace(second=0))

    def test_duration_uses_end_and_ignores_stale_start(self):
        for hours, minutes, start, end, expected in [
            (2, 15, 'bad stale date', '2026-09-24T16:00', '24.09.2026 13:45'),
            ('', 45, '', '2026-09-24T00:15', '23.09.2026 23:30'),
            (25, '', '', '2026-09-24T12:00', '23.09.2026 11:00'),
            (1, 0, '', '2026-03-29T03:30', '29.03.2026 01:30'),
            (3, 0, '', '2026-10-25T03:30', '25.10.2026 01:30'),
            (2, 0, '', '2026-10-25T03:30', '25.10.2026 02:30'),
        ]:
            with self.subTest(hours=hours, minutes=minutes, end=end):
                response = self.post(**{
                    'worklog-calculation_mode': 'duration', 'worklog-hours': hours, 'worklog-minutes': minutes,
                    'worklog-started_at': start, 'worklog-ended_at': end,
                })
                self.assertEqual(response.status_code, 200)
                self.assertIn(expected, response.json()['work_log_html'])
                self.assertEqual(self.task.work_logs.latest('pk').duration_minutes, (hours or 0) * 60 + (minutes or 0))

    def test_duration_validation_rejects_invalid_parts_and_dates(self):
        for values in [
            {'worklog-hours': 0, 'worklog-minutes': 0},
            {'worklog-hours': '', 'worklog-minutes': ''},
            {'worklog-hours': -1}, {'worklog-hours': '1.5'}, {'worklog-hours': 'invalid'},
            {'worklog-minutes': -1}, {'worklog-minutes': 60}, {'worklog-minutes': '0.5'},
            {'worklog-hours': str(10**20)}, {'worklog-ended_at': 'invalid'},
            {'worklog-ended_at': '2026-09-24T10:30:15'}, {'worklog-ended_at': '2026-03-29T02:30'},
            {'worklog-calculation_mode': 'unknown'},
        ]:
            with self.subTest(values=values):
                response = self.post(**{'worklog-calculation_mode': 'duration', 'worklog-hours': 1,
                                        'worklog-minutes': 0, **values})
                self.assertEqual(response.status_code, 400)
                self.assertIn('form_html', response.json())
        self.assertFalse(self.task.work_logs.exists())

    def test_interval_mode_recalculates_duration_and_preserves_it_after_errors(self):
        form = WorkLogForm({'calculation_mode': 'interval', 'hours': -10, 'minutes': 99,
                               'started_at': '2026-09-24T09:00', 'ended_at': '2026-09-24T11:15',
                               'description': ''})
        self.assertFalse(form.is_valid())
        self.assertEqual(set(form.errors), {'description'})
        self.assertEqual(form['hours'].value(), 2)
        self.assertEqual(form['minutes'].value(), 15)
        self.assertEqual(form['started_at'].value(), '2026-09-24T09:00')

    def test_duration_mode_preserves_inputs_after_description_error(self):
        form = WorkLogForm({'calculation_mode': 'duration', 'hours': 2, 'minutes': 15,
                               'ended_at': '2026-09-24T16:00', 'description': ''})
        self.assertFalse(form.is_valid())
        self.assertEqual(set(form.errors), {'description'})
        self.assertEqual(form['hours'].value(), 2)
        self.assertEqual(form['minutes'].value(), 15)
        self.assertEqual(form['started_at'].value(), '2026-09-24T13:45')
        self.assertEqual(form['calculation_mode'].value(), 'duration')

    def test_duration_edit_preserves_author_and_initializes_split_fields(self):
        self.post()
        entry = self.task.work_logs.get()
        initial = WorkLogForm(instance=entry)
        self.assertEqual((initial['hours'].value(), initial['minutes'].value()), (1, 30))
        self.client.force_login(self.owner)
        response = self.post('edit_work_log', work_log_id=entry.pk, **{
            'worklog-calculation_mode': 'duration', 'worklog-hours': 3, 'worklog-minutes': 10,
            'worklog-ended_at': '2026-09-24T16:00',
        })
        self.assertEqual(response.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(entry.duration_minutes, 190)
        self.assertEqual(entry.author, self.member)
        self.assertEqual(entry.started_at, datetime(2026, 9, 24, 10, 50, tzinfo=UTC))

    def test_react_edit_values_preserve_hours_when_only_minutes_change(self):
        self.post()
        entry = self.task.work_logs.get()
        for scoped in (False, True):
            with self.subTest(scoped=scoped):
                api = scoped_workplace_app_path(self.team, 'api', 'v1/page/')
                response = self.client.get(api, {'url': self.url(scoped=scoped)})
                values = response.json()['data']['work_log']['results'][0]['form_values']
                self.assertEqual((values['hours'], values['minutes']), (1, 30))
                self.assertEqual(values['duration_minutes'], 90)
        response = self.client.post(api + '?url=' + self.url(), {
            'action': 'edit_work_log', 'work_log_id': entry.pk,
            **{'worklog-' + name: value for name, value in values.items()},
            'worklog-minutes': '45', 'worklog-calculation_mode': 'duration',
        })
        self.assertEqual(response.status_code, 200)
        entry.refresh_from_db()
        self.assertEqual(entry.duration_minutes, 105)
        self.assertEqual(entry.author, self.member)

    def test_scope_rejects_foreign_task_owner_workspace_and_entry(self):
        elsewhere = make_task(user=self.owner, workplace=self.other_team, title='Elsewhere')
        foreign = make_task(user=self.outsider, workplace=self.team, title='Foreign')
        for task in (elsewhere, foreign):
            self.assertEqual(self.post(task=task).status_code, 404)
        second = make_task(user=self.owner, workplace=self.team, title='Second')
        self.post(task=second)
        entry = second.work_logs.get()
        for action in ('edit_work_log', 'delete_work_log'):
            self.assertEqual(self.post(action, work_log_id=entry.pk).status_code, 404)
            for invalid in ('bad', '0', '-1', str(2**80)):
                self.assertEqual(self.post(action, work_log_id=invalid).status_code, 404)
        self.assertEqual(second.work_logs.count(), 1)

    def test_revoked_member_and_assignee_have_no_access(self):
        self.task.assignee = self.outsider
        self.task.save()
        self.client.force_login(self.outsider)
        self.assertIn(self.post().status_code, (302, 403, 404))
        self.client.force_login(self.member)
        WorkplaceMembership.objects.filter(workplace=self.team, user=self.member).delete()
        self.assertIn(self.post().status_code, (302, 403, 404))
        self.assertFalse(self.task.work_logs.exists())

    def test_stable_url_ignores_forged_posted_pk_and_survives_other_deletions(self):
        other = make_task(user=self.owner, workplace=self.team, space=self.space, title='Later task')
        stable_url = self.url(other)
        deleted_pk = self.task.pk
        self.task.delete()
        response = self.client.post(stable_url, {
            'task_pk': deleted_pk, 'action': 'add_work_log', 'worklog-started_at': '2026-09-24T09:00',
            'worklog-ended_at': '2026-09-24T10:00', 'worklog-description': 'Stable identity',
        }, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(other.work_logs.count(), 1)
        other.delete()
        self.assertEqual(self.client.post(stable_url, {'action': 'add_work_log'}).status_code, 404)

    def test_scoped_url_keeps_original_workspace_after_session_switch(self):
        self.client.force_login(self.owner)
        session = self.client.session
        session['active_workplace_id'] = self.other_team.pk
        session.save()
        self.assertEqual(self.post().status_code, 200)
        self.assertEqual(self.task.work_logs.count(), 1)

    def test_pagination_totals_and_escaped_description(self):
        entries = [SpaceTaskWorkLog(task=self.task, author=self.member,
                              started_at=datetime(2026, 9, 24, 7, tzinfo=UTC),
                              ended_at=datetime(2026, 9, 24, 8, tzinfo=UTC),
                              description='<script>alert("x")</script>') for _ in range(26)]
        SpaceTaskWorkLog.objects.bulk_create(entries)
        response = self.client.get(self.url(), {'tab': 'work-log', 'work_log_page': 2})
        self.assertEqual(response.context['work_log_page'].paginator.count, 26)
        self.assertEqual(len(response.context['work_log_page']), 1)
        self.assertEqual(response.context['work_log_total_minutes'], 1560)
        self.assertNotContains(response, '<script>alert("x")</script>')
        self.assertContains(response, '&lt;script&gt;')
        self.assertContains(response, f'/tasks/{self.task.work_item.key}/')
        self.assertContains(response, 'Strona 2 z 2')

    def test_history_failure_rolls_back_create_edit_and_delete(self):
        with patch('spaces.task_views.record', side_effect=RuntimeError('Unavailable')):
            with self.assertRaises(RuntimeError):
                self.post()
        self.assertFalse(self.task.work_logs.exists())
        self.post()
        entry = self.task.work_logs.get()
        for action in ('edit_work_log', 'delete_work_log'):
            with patch('spaces.task_views.record', side_effect=RuntimeError('Unavailable')):
                with self.assertRaises(RuntimeError):
                    self.post(action, work_log_id=entry.pk, **{'worklog-ended_at': '2026-09-24T12:00'})
            entry.refresh_from_db()
            self.assertEqual(entry.duration_minutes, 90)

    def test_non_ajax_validation_keeps_tab_and_valid_post_redirects_scoped(self):
        url = self.url() + '?tab=work-log'
        data = {'action': 'add_work_log', 'worklog-description': 'Still here'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 400)
        self.assertTrue(response.context['work_log_modal_open'])
        self.assertEqual(response.context['task_tab'], 'work-log')
        self.assertContains(response, 'Still here', status_code=400)
        data.update({'worklog-started_at': '2026-09-24T09:00', 'worklog-ended_at': '2026-09-24T10:00'})
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, url)

    def test_author_removal_preserves_log_and_task_removal_cascades(self):
        self.post()
        entry = self.task.work_logs.get()
        self.member.delete()
        entry.refresh_from_db()
        self.assertIsNone(entry.author)
        self.client.force_login(self.owner)
        self.assertContains(self.client.get(self.url()), 'Usunięte konto')
        self.task.delete()
        self.assertFalse(SpaceTaskWorkLog.objects.filter(pk=entry.pk).exists())

    def test_database_rejects_nonpositive_interval(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            SpaceTaskWorkLog.objects.create(task=self.task, author=self.member,
                                       started_at=datetime(2026, 9, 24, 8, tzinfo=UTC),
                                       ended_at=datetime(2026, 9, 24, 8, tzinfo=UTC), description='Invalid')

    def test_login_and_csrf_required(self):
        self.client.logout()
        self.assertEqual(self.post().status_code, 302)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.member)
        self.assertEqual(client.post(self.url(), {'action': 'add_work_log', 'task_pk': self.task.pk}).status_code, 403)
