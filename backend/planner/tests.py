from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from workplaces.models import create_workplace_for_user
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
