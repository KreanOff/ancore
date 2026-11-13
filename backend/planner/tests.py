from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import CalendarEvent

User = get_user_model()


class CalendarEventTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='calendar@test.com',
            email='calendar@test.com',
            password='testpass123',
        )
        self.workspace = create_workplace_for_user(self.user, 'Kalendarz testowy')
        self.client = Client()
        self.client.login(username='calendar@test.com', password='testpass123')

    def test_index_requires_login(self):
        anonymous = Client()
        response = anonymous.get(reverse('planner:index'))
        self.assertEqual(response.status_code, 302)

    def test_create_and_list_events(self):
        start = timezone.now().replace(minute=0, second=0, microsecond=0)
        end = start + timedelta(hours=1)
        create_response = self.client.post(reverse('planner:create_event'), {
            'title': 'Spotkanie',
            'description': 'Opis',
            'start': start.strftime('%Y-%m-%dT%H:%M'),
            'end': end.strftime('%Y-%m-%dT%H:%M'),
            'color': 'blue',
        })
        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(create_response.json()['status'], 'success')

        range_start = start - timedelta(days=1)
        range_end = end + timedelta(days=1)
        list_response = self.client.get(reverse('planner:events'), {
            'start': range_start.isoformat(),
            'end': range_end.isoformat(),
        })
        self.assertEqual(list_response.status_code, 200)
        payload = list_response.json()
        self.assertEqual(len(payload['events']), 1)
        self.assertEqual(payload['events'][0]['title'], 'Spotkanie')

    def test_user_cannot_access_other_users_event(self):
        other = User.objects.create_user(
            username='other@test.com',
            email='other@test.com',
            password='testpass123',
        )
        start = timezone.now()
        event = CalendarEvent.objects.create(
            user=other,
            title='Prywatne',
            start=start,
            end=start + timedelta(hours=1),
        )
        response = self.client.post(reverse('planner:delete_event', args=[event.id]))
        self.assertEqual(response.status_code, 404)

    def calendar_endpoint(self, suffix, *, scoped, delegated, params=None):
        target = (scoped_workplace_app_path(self.workspace, 'calendar', suffix)
                  if scoped else '/calendar/' + suffix)
        if params:
            target += '?' + urlencode(params)
        if not delegated:
            return target
        api = (scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
               if scoped else '/api/v1/page/')
        return api + '?' + urlencode({'url': target})

    def test_custom_color_survives_create_update_and_feed_in_every_endpoint(self):
        for scoped in (False, True):
            for delegated in (False, True):
                with self.subTest(scoped=scoped, delegated=delegated):
                    values = {'title': 'Własny kolor', 'start': '2026-11-12T09:00:00Z',
                              'end': '2026-11-12T10:00:00Z', 'color': '#2563EB'}
                    response = self.client.post(self.calendar_endpoint(
                        'events/create/', scoped=scoped, delegated=delegated), values)
                    self.assertEqual(response.status_code, 200, response.content)
                    event = CalendarEvent.objects.get(pk=response.json()['event']['id'])
                    self.assertEqual(event.color, '#2563eb')
                    self.assertEqual(response.json()['event']['color'], '#2563eb')
                    self.assertEqual((event.user_id, event.workplace_id), (self.user.pk, self.workspace.pk))

                    values['color'] = '#bA127F'
                    response = self.client.post(self.calendar_endpoint(
                        f'events/{event.pk}/update/', scoped=scoped, delegated=delegated), values)
                    self.assertEqual(response.status_code, 200, response.content)
                    event.refresh_from_db()
                    self.assertEqual(event.color, '#ba127f')
                    self.assertEqual(response.json()['event']['color'], '#ba127f')

                    response = self.client.get(self.calendar_endpoint(
                        'events/', scoped=scoped, delegated=delegated, params={
                        'start': '2026-11-12T00:00:00Z', 'end': '2026-11-13T00:00:00Z',
                    }))
                    self.assertEqual(response.status_code, 200, response.content)
                    listed = next(item for item in response.json()['events'] if item['id'] == event.pk)
                    self.assertEqual(listed['color'], '#ba127f')

    def test_legacy_colors_remain_valid_and_are_preserved(self):
        for color in ('red', 'blue', 'green', 'amber', 'slate'):
            with self.subTest(color=color):
                event = CalendarEvent.objects.create(
                    user=self.user, workplace=self.workspace, title='Dotychczasowy kolor',
                    start=timezone.now(), end=timezone.now() + timedelta(hours=1), color=color,
                )
                values = {'title': event.title, 'description': 'Zmieniony opis',
                          'start': event.start.isoformat(), 'end': event.end.isoformat(), 'color': color}
                response = self.client.post(reverse('planner:update_event', args=[event.pk]), values)
                self.assertEqual(response.status_code, 200, response.content)
                self.assertEqual(response.json()['event']['color'], color)
                event.refresh_from_db()
                self.assertEqual(event.color, color)
                self.assertEqual(event.description, 'Zmieniony opis')
                response = self.client.post(reverse('planner:create_event'), values)
                self.assertEqual(response.status_code, 200, response.content)
                self.assertEqual(response.json()['event']['color'], color)

    def test_empty_and_omitted_colors_use_default(self):
        for color_values in ({'color': ''}, {}):
            with self.subTest(color_values=color_values):
                values = {'title': 'Domyślny kolor', 'start': '2026-11-12T09:00:00Z',
                          'end': '2026-11-12T10:00:00Z', **color_values}
                response = self.client.post(reverse('planner:create_event'), values)
                self.assertEqual(response.status_code, 200, response.content)
                event = CalendarEvent.objects.get(pk=response.json()['event']['id'])
                self.assertEqual(event.color, CalendarEvent.DEFAULT_COLOR)
                event.color = '#2563eb'
                event.save(update_fields=['color'])
                response = self.client.post(reverse('planner:update_event', args=[event.pk]), values)
                self.assertEqual(response.status_code, 200, response.content)
                event.refresh_from_db()
                self.assertEqual(event.color, CalendarEvent.DEFAULT_COLOR)

    def test_invalid_colors_are_rejected_without_creating_or_changing_an_event(self):
        event = CalendarEvent.objects.create(
            user=self.user, workplace=self.workspace, title='Bez zmian',
            start=timezone.now(), end=timezone.now() + timedelta(hours=1), color='#2563eb',
        )
        for scoped in (False, True):
            for delegated in (False, True):
                for color in ('#abc', '#12345678', '#12345g', 'purple', 'rgb(0,0,0)', 'red;--x:1'):
                    with self.subTest(scoped=scoped, delegated=delegated, color=color):
                        values = {'title': 'Odrzucona zmiana', 'start': event.start.isoformat(),
                                  'end': event.end.isoformat(), 'color': color}
                        for suffix in ('events/create/', f'events/{event.pk}/update/'):
                            response = self.client.post(self.calendar_endpoint(
                                suffix, scoped=scoped, delegated=delegated), values)
                            self.assertEqual(response.status_code, 400, response.content)
                            self.assertIn('color', response.json()['errors'])
                        self.assertEqual(CalendarEvent.objects.count(), 1)
                        event.refresh_from_db()
                        self.assertEqual((event.title, event.color), ('Bez zmian', '#2563eb'))

    def test_custom_colors_keep_workspace_scope_and_member_write_permissions(self):
        other_workspace = create_workplace_for_user(self.user, 'Inny Workspace')
        event = CalendarEvent.objects.create(
            user=self.user, workplace=other_workspace, title='Poza Workspace',
            start=timezone.now(), end=timezone.now() + timedelta(hours=1), color='#2563eb',
        )
        values = {'title': event.title, 'start': event.start.isoformat(),
                  'end': event.end.isoformat(), 'color': '#ab1256'}
        member = User.objects.create_user(username='event-color-member', email='event-color-member@example.test')
        membership = WorkplaceMembership.objects.create(workplace=self.workspace, user=member)
        self.client.force_login(member)
        for delegated in (False, True):
            endpoint = self.calendar_endpoint(f'events/{event.pk}/update/', scoped=True, delegated=delegated)
            self.assertEqual(self.client.post(endpoint, values).status_code, 404)
            response = self.client.get(self.calendar_endpoint('events/', scoped=True, delegated=delegated, params={
                'start': (event.start - timedelta(days=1)).isoformat(),
                'end': (event.end + timedelta(days=1)).isoformat(),
            }))
            self.assertEqual(response.status_code, 200)
            self.assertNotIn(event.pk, [item['id'] for item in response.json()['events']])
        event.refresh_from_db()
        self.assertEqual(event.color, '#2563eb')

        endpoint = self.calendar_endpoint('events/create/', scoped=True, delegated=True)
        response = self.client.post(endpoint, values)
        self.assertEqual(response.status_code, 200, response.content)
        shared = CalendarEvent.objects.get(pk=response.json()['event']['id'])
        self.assertEqual((shared.user_id, shared.workplace_id, shared.color),
                         (self.user.pk, self.workspace.pk, '#ab1256'))
        membership.role = WorkplaceMembership.Role.GUEST
        membership.save(update_fields=['role'])
        self.assertEqual(self.client.post(endpoint, values).status_code, 403)
        self.assertEqual(self.client.post(self.calendar_endpoint(
            f'events/{shared.pk}/update/', scoped=True, delegated=True), values).status_code, 403)

    def test_model_color_validation_accepts_hex_and_legacy_names_only(self):
        field = CalendarEvent._meta.get_field('color')
        for color in ('#000000', '#FFFFFF', '#2563eb', 'red', 'blue', 'green', 'amber', 'slate'):
            self.assertEqual(field.clean(color, None), color)
        for color in ('#fff', '#12345678', '#gggggg', 'purple', 'red\n', '#123456\n'):
            with self.subTest(color=color), self.assertRaises(ValidationError):
                field.clean(color, None)

    def test_explicit_timed_values_survive_create_edit_and_dst_in_every_endpoint(self):
        for scoped in (False, True):
            for delegated in (False, True):
                for start, end in [
                    ('2026-06-01T10:00:00Z', '2026-06-01T11:00:00Z'),
                    ('2026-03-29T01:30:00+01:00', '2026-03-29T03:30:00+02:00'),
                    ('2026-10-25T02:45:17+02:00', '2026-10-25T02:15:19+01:00'),
                    ('2026-06-01T10:00:00-04:00', '2026-06-01T11:00:00-04:00'),
                ]:
                    with self.subTest(scoped=scoped, delegated=delegated, start=start):
                        values = {'title': 'Spotkanie', 'description': '',
                                  'start': start, 'end': end, 'color': 'blue'}
                        response = self.client.post(self.calendar_endpoint(
                            'events/create/', scoped=scoped, delegated=delegated), values)
                        self.assertEqual(response.status_code, 200, response.content)
                        event = CalendarEvent.objects.latest('pk')
                        expected = (datetime.fromisoformat(start).astimezone(UTC),
                                    datetime.fromisoformat(end).astimezone(UTC))
                        self.assertEqual((event.start, event.end), expected)
                        values['description'] = 'Tylko nowy opis'
                        response = self.client.post(self.calendar_endpoint(
                            f'events/{event.pk}/update/', scoped=scoped, delegated=delegated), values)
                        self.assertEqual(response.status_code, 200, response.content)
                        event.refresh_from_db()
                        self.assertEqual((event.start, event.end), expected)
                        self.assertEqual(event.description, 'Tylko nowy opis')

    def test_all_day_calendar_dates_survive_dst_and_edits_in_every_endpoint(self):
        for scoped in (False, True):
            for delegated in (False, True):
                for start, end in [('2026-03-29', '2026-03-30'), ('2026-10-25', '2026-10-26')]:
                    with self.subTest(scoped=scoped, delegated=delegated, start=start):
                        values = {'title': 'Cały dzień', 'start': start + 'T00:00',
                                  'end': end + 'T23:59', 'all_day': 'on', 'color': 'blue'}
                        response = self.client.post(self.calendar_endpoint(
                            'events/create/', scoped=scoped, delegated=delegated), values)
                        self.assertEqual(response.status_code, 200, response.content)
                        event = CalendarEvent.objects.latest('pk')
                        self.assertEqual(timezone.localtime(event.start).isoformat()[:16], start + 'T00:00')
                        self.assertEqual(timezone.localtime(event.end).isoformat()[:19], end + 'T23:59:59')
                        original = (event.start, event.end)
                        values['description'] = 'Zmieniony opis wydarzenia całodniowego'
                        response = self.client.post(self.calendar_endpoint(
                            f'events/{event.pk}/update/', scoped=scoped, delegated=delegated), values)
                        self.assertEqual(response.status_code, 200, response.content)
                        event.refresh_from_db()
                        self.assertEqual((event.start, event.end), original)

    def test_naive_missing_and_repeated_warsaw_hours_remain_invalid(self):
        for value in ('2026-03-29T02:30', '2026-10-25T02:30'):
            response = self.client.post(reverse('planner:create_event'), {
                'title': 'Nieprawidłowa godzina', 'start': value,
                'end': value[:10] + 'T04:00', 'color': 'blue',
            })
            self.assertEqual(response.status_code, 400)
            self.assertIn('start', response.json()['errors'])
        self.assertFalse(CalendarEvent.objects.exists())
