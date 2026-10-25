"""Manual account grants stay bounded, explicit and safe across concurrent changes."""
import json
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Barrier
from unittest.mock import patch
from urllib.parse import urlencode
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.db import close_old_connections
from django.db.models.query import QuerySet
from django.test import Client, RequestFactory, TestCase, TransactionTestCase
from django.urls import reverse

from . import team_views
from .invitations import pending_join_url
from .models import Workplace, WorkplaceMembership, create_workplace_for_user
from .services import scoped_workplace_app_path


class ManualMemberTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='@manual.owner', email='manual-owner@example.test')
        cls.admin = users.objects.create_user(username='@manual.admin', email='manual-admin@example.test')
        cls.target = users.objects.create_user(username='@manual.target', email='manual-target@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Ręczne dostępy')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.admin, role='admin')

    def client_for(self, user):
        client = Client()
        client.force_login(user)
        session = client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()
        return client

    def team_url(self):
        return reverse('workplaces:team', args=[self.workspace.pk])

    def test_directory_does_not_serialize_the_global_account_directory(self):
        unrelated = [get_user_model().objects.create_user(username=f'@global.person{number}',
                     email=f'global-person{number}@other.example.test') for number in range(25)]
        client = self.client_for(self.owner)
        target = reverse('workplaces:workplaces') + f'?workspace={self.workspace.pk}&view=members'
        response = client.get(target)
        self.assertEqual(response.status_code, 200)
        for person in unrelated:
            self.assertNotContains(response, person.email)
        for api in ('/api/v1/page/', scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')):
            response = client.get(api, {'url': target}, follow=True)
            self.assertEqual(response.status_code, 200)
            schema = response.json()['data']['team']['add_form']
            account = next(field for field in schema['fields'] if field['name'] == 'user_id')
            self.assertLessEqual(len(account.get('choices', [])), 1)
            payload = json.dumps(response.json())
            for person in unrelated:
                self.assertNotIn(person.email, payload)

    def test_native_id_accepts_an_exact_public_username(self):
        client = self.client_for(self.owner)
        response = client.post(self.team_url(), {'user_id': ' @MANUAL.TARGET ', 'role': 'guest'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.workspace.memberships.filter(user=self.target, role='guest', is_active=True).exists())

    def test_email_strings_never_resolve_to_account_grants(self):
        # Django's UserAdmin can contain legacy IDs outside the public-ID format.
        deceptive = get_user_model().objects.create_user(username='@claimed@external.test', email='other@external.test')
        client = self.client_for(self.owner)
        for identity in (self.target.email, self.target.email.upper(), 'claimed@external.test', '@claimed@external.test'):
            with self.subTest(identity=identity):
                response = client.post(self.team_url(), {'user_id': identity, 'role': 'admin'})
                self.assertEqual(response.status_code, 200)
                self.assertIn('user_id', response.context['add_form'].errors)
        self.assertFalse(self.workspace.memberships.filter(user__in=[self.target, deceptive]).exists())

    def test_ambiguous_legacy_username_never_selects_the_first_account(self):
        duplicate = get_user_model().objects.create_user(username='@MANUAL.TARGET', email='manual-duplicate@example.test')
        client = self.client_for(self.owner)
        response = client.post(self.team_url(), {'user_id': '@manual.target', 'role': 'admin'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('user_id', response.context['add_form'].errors)
        self.assertFalse(self.workspace.memberships.filter(user__in=[self.target, duplicate]).exists())
        # The picker sends an unambiguous database identity, even for old accounts.
        response = client.post(self.team_url(), {'user_id': duplicate.pk, 'role': 'guest'})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.workspace.memberships.filter(user=duplicate, role='guest').exists())

    def test_admin_cannot_reactivate_or_downgrade_an_inactive_admin(self):
        membership = WorkplaceMembership.objects.create(workplace=self.workspace, user=self.target,
                                                        role='admin', is_active=False)
        client = self.client_for(self.admin)
        for role in ('member', 'guest'):
            response = client.post(self.team_url(), {'user_id': self.target.pk, 'role': role})
            self.assertEqual(response.status_code, 200)
            self.assertIn('user_id', response.context['add_form'].errors)
            membership.refresh_from_db()
            self.assertEqual((membership.role, membership.is_active), ('admin', False))
        candidates = client.get(reverse('workplaces:member-candidates', args=[self.workspace.pk]),
                                {'q': self.target.email}).json()['results']
        self.assertEqual(candidates, [])
        response = self.client_for(self.owner).post(self.team_url(), {'user_id': self.target.pk, 'role': 'admin'})
        self.assertEqual(response.status_code, 302)
        membership.refresh_from_db()
        self.assertEqual((membership.role, membership.is_active), ('admin', True))

    def test_removed_email_routes_are_unavailable_directly_and_through_both_delegates(self):
        client = self.client_for(self.owner)
        for target in (f'/workplaces/invite/{uuid4()}/', '/workplaces/invitations/1/respond/',
                       f'/workplaces/{self.workspace.pk}/invitations/1/resend/'):
            for method in ('get', 'post'):
                self.assertEqual(getattr(client, method)(target).status_code, 404)
                for api in ('/api/v1/page/', scoped_workplace_app_path(self.workspace, 'api', 'v1/page/'),
                            reverse('accounts-api')):
                    response = getattr(client, method)(api + '?' + urlencode({'url': target}), follow=True)
                    self.assertEqual(response.status_code, 404)
        request = RequestFactory().get('/')
        request.session = {'workspace_join_url': f'/workplaces/invite/{uuid4()}/'}
        self.assertEqual(pending_join_url(request), '')
        self.assertFalse(self.workspace.memberships.filter(user=self.target).exists())


class ManualMemberConcurrencyTests(TransactionTestCase):
    def setUp(self):
        users = get_user_model()
        self.owner = users.objects.create_user(username='@manual.race.owner', email='manual-race-owner@example.test')
        self.admin = users.objects.create_user(username='@manual.race.admin', email='manual-race-admin@example.test')
        self.target = users.objects.create_user(username='@manual.race.target', email='manual-race-target@example.test')
        self.workspace = create_workplace_for_user(self.owner, 'Równoczesne nadawanie dostępu')
        self.admin_membership = WorkplaceMembership.objects.create(workplace=self.workspace, user=self.admin, role='admin')

    def test_simultaneous_manual_adds_create_one_membership_without_overwriting_its_role(self):
        barrier = Barrier(2)
        url = reverse('workplaces:team', args=[self.workspace.pk])

        def add(actor_id, role):
            close_old_connections()
            try:
                client = Client()
                client.force_login(get_user_model().objects.get(pk=actor_id))
                barrier.wait(timeout=10)
                response = client.post(url, {'user_id': self.target.pk, 'role': role})
                return response.status_code, role
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            jobs = [executor.submit(add, self.owner.pk, 'guest'), executor.submit(add, self.admin.pk, 'member')]
            outcomes = [job.result(timeout=20) for job in jobs]
        self.assertEqual(sorted(status for status, _ in outcomes), [200, 302])
        self.assertEqual(self.workspace.memberships.filter(user=self.target).count(), 1)
        self.assertEqual(self.workspace.memberships.get(user=self.target).role,
                         next(role for status, role in outcomes if status == 302))

    @contextmanager
    def revoke_admin_before_workspace_lock(self, action):
        original = QuerySet.select_for_update
        changed = False

        def revoke():
            close_old_connections()
            try:
                membership = WorkplaceMembership.objects.get(pk=self.admin_membership.pk)
                if action == 'remove':
                    membership.delete()
                else:
                    if action == 'deactivate':
                        membership.is_active = False
                    else:
                        membership.role = 'member'
                    membership.save()
            finally:
                close_old_connections()

        def lock(queryset, *args, **kwargs):
            nonlocal changed
            if not changed and queryset.model is Workplace:
                changed = True
                with ThreadPoolExecutor(max_workers=1) as executor:
                    executor.submit(revoke).result(timeout=10)
            return original(queryset, *args, **kwargs)

        with patch.object(QuerySet, 'select_for_update', lock):
            yield

    def test_manual_add_rechecks_admin_role_after_revocation_before_lock(self):
        for action in ('demote', 'deactivate', 'remove'):
            with self.subTest(action=action):
                WorkplaceMembership.objects.filter(pk=self.admin_membership.pk).update(role='admin', is_active=True)
                request = RequestFactory().post('/workplaces/team/', {'user_id': self.target.pk, 'role': 'member'})
                request.user, request.workplace = self.admin, self.workspace
                with self.revoke_admin_before_workspace_lock(action), self.assertRaises(PermissionDenied):
                    team_views.team(request, workplace_id=self.workspace.pk)
                self.assertFalse(self.workspace.memberships.filter(user=self.target).exists())
