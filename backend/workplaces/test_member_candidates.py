from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import WorkplaceMembership, create_workplace_for_user


class MemberCandidateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='owner', email='owner@example.test')
        cls.admin = users.objects.create_user(username='admin', email='admin@example.test')
        cls.member = users.objects.create_user(username='member', email='member@example.test')
        cls.person = users.objects.create_user(
            username='@jan.nowak', email='jan.nowak@example.test',
            first_name='Jan', middle_name='Adam', last_name='Nowak',
        )
        cls.active = create_workplace_for_user(cls.owner, 'Active')
        cls.selected = create_workplace_for_user(cls.owner, 'Selected')
        cls.foreign = create_workplace_for_user(cls.person, 'Foreign')
        WorkplaceMembership.objects.create(workplace=cls.selected, user=cls.admin, role='admin')
        WorkplaceMembership.objects.create(workplace=cls.selected, user=cls.member)
        cls.url = reverse('workplaces:member-candidates', args=[cls.selected.pk])

    def setUp(self):
        self.client.force_login(self.owner)
        session = self.client.session
        session['active_workplace_id'] = self.active.pk
        session.save()

    def test_searches_names_id_and_email_case_insensitively(self):
        for query in ['Jan Nowak', 'nowak jan', 'Adam', '@JAN.NOW', 'JAN.NOWAK@EXAMPLE.TEST']:
            with self.subTest(query=query):
                response = self.client.get(self.url, {'q': query})
                self.assertEqual(response.status_code, 200)
                self.assertEqual([p['email'] for p in response.json()['results']], [self.person.email])
                self.assertEqual(response.json()['results'][0]['id'], str(self.person.pk))
                self.assertEqual(response.json()['results'][0]['name'], 'Jan Adam Nowak')
                self.assertIn('no-store', response.headers['Cache-Control'])
        self.assertEqual(self.client.session['active_workplace_id'], self.active.pk)

    def test_empty_short_unknown_and_oversized_queries_return_no_people(self):
        for query in ['', ' ', 'j', 'missing-address', 'a' * 255]:
            with self.subTest(query=query):
                self.assertEqual(self.client.get(self.url, {'q': query}).json(), {'results': [], 'has_more': False})

    def test_requires_manager_of_requested_workspace(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url, {'q': 'jan'}).status_code, 302)
        for user, status in [(self.member, 403), (self.person, 404), (self.admin, 200)]:
            with self.subTest(user=user.username):
                self.client.force_login(user)
                self.assertEqual(self.client.get(self.url, {'q': 'jan'}).status_code, status)
        self.client.force_login(self.owner)
        foreign_url = reverse('workplaces:member-candidates', args=[self.foreign.pk])
        self.assertEqual(self.client.get(foreign_url, {'q': 'jan'}).status_code, 404)
        self.assertEqual(self.client.post(self.url, {'q': 'jan'}).status_code, 405)

    def test_removed_admin_loses_lookup_access(self):
        self.client.force_login(self.admin)
        WorkplaceMembership.objects.filter(workplace=self.selected, user=self.admin).update(is_active=False)
        self.assertEqual(self.client.get(self.url, {'q': 'jan'}).status_code, 404)

    def test_excludes_current_team_and_inactive_accounts(self):
        users = get_user_model()
        users.objects.create_user(username='inactive', email='inactive@example.test', is_active=False)
        WorkplaceMembership.objects.create(workplace=self.selected, user=self.person)
        self.assertEqual(self.client.get(self.url, {'q': 'example.test'}).json()['results'], [])

    def test_candidates_follow_selected_team_not_active_team(self):
        WorkplaceMembership.objects.create(workplace=self.active, user=self.person)
        WorkplaceMembership.objects.create(workplace=self.selected, user=self.person, is_active=False)
        self.assertEqual(self.client.get(self.url, {'q': 'jan'}).json()['results'][0]['email'], self.person.email)
        self.assertEqual(self.client.session['active_workplace_id'], self.active.pk)

    def test_results_are_limited_and_html_is_escaped(self):
        users = get_user_model()
        for number in range(11):
            users.objects.create_user(username=f'candidate{number}', email=f'candidate{number:02}@example.test')
        payload = self.client.get(self.url, {'q': 'candidate'}).json()
        self.assertEqual(len(payload['results']), 10)
        self.assertTrue(payload['has_more'])
        self.person.first_name = '<img src=x onerror=alert(1)>'
        self.person.save()
        html = self.client.get(self.url, {'q': self.person.email}).json()['results'][0]['html']
        self.assertIn('&lt;img', html)
        self.assertNotIn('<img src=x', html)

    def test_lookup_does_not_add_and_submit_revalidates_selected_person(self):
        self.client.get(self.url, {'q': self.person.email})
        self.assertFalse(self.selected.memberships.filter(user=self.person).exists())
        WorkplaceMembership.objects.create(workplace=self.selected, user=self.person)
        response = self.client.post(reverse('workplaces:team', args=[self.selected.pk]), {
            'user_id': self.person.pk, 'role': 'member',
        })
        self.assertContains(response, 'Ta osoba jest już członkiem Workspace.')
        self.assertIn('user_id', response.context['add_form'].errors)
        self.assertEqual(self.selected.memberships.filter(user=self.person).count(), 1)

    def test_submit_rejects_an_account_disabled_after_lookup(self):
        person = self.client.get(self.url, {'q': self.person.email}).json()['results'][0]
        self.person.is_active = False
        self.person.save(update_fields=['is_active'])
        response = self.client.post(reverse('workplaces:team', args=[self.selected.pk]), {
            'user_id': person['id'], 'role': 'member',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('user_id', response.context['add_form'].errors)
        self.assertFalse(self.selected.memberships.filter(user=self.person).exists())

    def test_exact_email_is_not_hidden_by_the_result_limit(self):
        for number in range(11):
            get_user_model().objects.create_user(
                username=f'prefix{number}', email=f'prefix{number}{self.person.email}', first_name='Adam',
            )
        payload = self.client.get(self.url, {'q': self.person.email.upper()}).json()
        self.assertEqual(payload['results'][0]['email'], self.person.email)
        self.assertTrue(payload['has_more'])
