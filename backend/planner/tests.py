from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from workplaces.models import create_workplace_for_user
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

    def calendar_endpoint(self, suffix, *, scoped, delegated):
        target = (scoped_workplace_app_path(self.workspace, 'calendar', suffix)
                  if scoped else '/calendar/' + suffix)
        if not delegated:
            return target
        api = (scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
               if scoped else '/api/v1/page/')
        return api + '?' + urlencode({'url': target})

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
