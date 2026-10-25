"""Workspace capabilities are enforced on direct routes and delegated APIs."""
import json
from datetime import timedelta
from unittest.mock import patch
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from dashboard.models import Dashboard
from documents.models import WorkspaceDocument
from documents import office_service
from spaces.models import SpaceMembership
from spaces.testing import make_space, make_task
from .models import Workplace, WorkplaceInvitation, WorkplaceInviteLink, WorkplaceMembership, create_workplace_for_user
from .services import scoped_workplace_app_path


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class WorkspaceSystemTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='system-owner', email='owner@example.test')
        cls.guest = users.objects.create_user(username='system-guest', email='guest@example.test')
        cls.other = users.objects.create_user(username='system-other', email='other@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Zespół')
        cls.membership = WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.guest, role='guest')
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Publiczna')
        cls.private = make_space(user=cls.owner, workplace=cls.workspace, name='Prywatna', visibility='private', private_owner=cls.owner)
        cls.task = make_task(user=cls.owner, workplace=cls.workspace, space=cls.space, title='Zadanie')

    def setUp(self):
        self.client.force_login(self.owner)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, app='spaces', suffix=''):
        return scoped_workplace_app_path(self.workspace, app, suffix)

    def api(self, target, body=None, scoped=False):
        endpoint = self.url('api', 'v1/page/') if scoped else '/api/v1/page/'
        endpoint += '?' + urlencode({'url': target})
        return self.client.get(endpoint, follow=True) if body is None else self.client.post(endpoint, body)

    def test_creation_initializes_and_enters_independent_workspace(self):
        response = self.client.post(reverse('workplaces:workplaces'), {'name': 'Nowy'})
        workspace = Workplace.objects.get(name='Nowy')
        self.assertEqual(response.url, scoped_workplace_app_path(workspace, 'for-you'))
        self.assertEqual(self.client.session['active_workplace_id'], workspace.pk)
        self.assertEqual(workspace.memberships.count(), 1)
        from spaces.models import Space
        self.assertFalse(Space.objects.filter(workplace=workspace).exists())
        self.assertEqual(Dashboard.objects.get(workplace=workspace, is_default=True).gadgets.count(), 1)

    def test_disabled_module_hides_navigation_and_blocks_html_and_both_api_routes(self):
        self.client.get(self.url('space', self.space.slug + '/'))
        self.workspace.disabled_modules = ['spaces', 'resources']
        self.workspace.save(update_fields=['disabled_modules'])
        for path in (self.url(), '/spaces/', self.url('resources', 'api/v1/')):
            self.assertIn(self.client.get(path).status_code, (302, 404))
        for scoped in (False, True):
            self.assertEqual(self.api(self.url(), scoped=scoped).status_code, 404)
            self.assertEqual(self.api(self.url(), {'name': 'Nie'}, scoped=scoped).status_code, 404)
        data = self.api(self.url('for-you')).json()
        self.assertEqual(data['type'], 'for-you')
        response = self.client.get(self.url('for-you'))
        shell = self.client.get(self.url('api', 'v1/shell/') + '?' + urlencode({'url': self.url('for-you')})).json()
        self.assertNotIn('spaces', [item['key'] for item in shell['collections']])
        self.assertTrue(type(self.space).objects.filter(pk=self.space.pk).exists())
        self.assertEqual(self.client.get(reverse('global_search'), {'recent': '1'}).json()['total'], 0)

    def test_module_settings_are_owned_and_keep_data_on_reenable(self):
        url = reverse('workplaces:update', args=[self.workspace.pk])
        response = self.client.post(url, {'name': self.workspace.name, 'modules_submitted': '1', 'enabled_modules': ['office']})
        self.assertEqual(response.status_code, 302)
        self.workspace.refresh_from_db()
        self.assertIn('spaces', self.workspace.disabled_modules)
        self.assertNotIn('office', self.workspace.disabled_modules)
        self.client.force_login(self.guest)
        self.assertEqual(self.client.post(url, {'name': 'Nie'}).status_code, 403)
        self.client.force_login(self.owner)
        self.client.post(url, {'name': self.workspace.name, 'modules_submitted': '1', 'enabled_modules': ['spaces', 'office']})
        self.assertEqual(self.api(self.url()).status_code, 200)

    def test_guest_reads_shared_spaces_and_cannot_bypass_private_spaces(self):
        self.client.force_login(self.guest)
        self.assertEqual(self.client.get(self.url()).status_code, 200)
        private = self.url('space', self.private.slug + '/')
        self.assertEqual(self.client.get(private).status_code, 404)
        SpaceMembership.objects.create(space=self.private, user=self.guest, role='admin')
        response = self.api(private)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['read_only'])
        self.assertFalse(response.json()['data']['can_manage'])
        self.assertEqual(self.api(private, {'action': 'delete'}).status_code, 403)

    def test_guest_cannot_write_through_direct_base_scoped_or_delegated_routes(self):
        self.client.force_login(self.guest)
        targets = [self.url('space', self.space.slug + '/items/create/'), self.url('calendar', 'events/create/'),
                   self.url('resources', 'api/v1/'), self.url('office', 'create/')]
        for target in targets:
            with self.subTest(target=target):
                self.assertEqual(self.client.post(target, {'name': 'Nie', 'title': 'Nie'}).status_code, 403)
        for scoped in (False, True):
            self.assertEqual(self.api(self.url('space', self.space.slug + '/items/create/'), {'title': 'Nie'}, scoped).status_code, 403)
        self.assertEqual(self.client.post('/resources/api/v1/', '{}', content_type='application/json').status_code, 403)

    def test_old_office_callback_cannot_write_after_demotion_or_module_disable(self):
        document = WorkspaceDocument.objects.create(owner=self.owner, workplace=self.workspace, title='Plik', kind='file', filename='test.docx')
        self.membership.role = 'member'; self.membership.save()
        token = office_service.capability(document, 'callback', self.guest)
        self.assertTrue(office_service.check_capability(document, token, 'callback'))
        self.membership.role = 'guest'; self.membership.save()
        self.assertFalse(office_service.check_capability(document, token, 'callback'))
        config = office_service.editor_config(document, self.guest)
        self.assertFalse(config['document']['permissions']['edit'])
        self.assertEqual(config['editorConfig']['mode'], 'view')
        self.workspace.disabled_modules = ['office']; self.workspace.save()
        self.assertFalse(office_service.check_capability(document, office_service.capability(document, 'source', self.owner), 'source'))

    def test_external_email_invitation_is_delivered_and_bound_to_email(self):
        response = self.client.post(reverse('workplaces:team', args=[self.workspace.pk]), {'email': 'new@example.test', 'role': 'guest'})
        self.assertEqual(response.status_code, 302)
        invitation = WorkplaceInvitation.objects.get(email='new@example.test')
        self.assertIsNone(invitation.recipient)
        self.assertIsNotNone(invitation.email_sent_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(self.client.get(reverse('workplaces:workplaces'), {'workspace': self.workspace.pk, 'view': 'invitations'}).status_code, 200)
        url = reverse('workplaces:join-email', args=[invitation.token])
        self.assertIn(url, mail.outbox[0].body)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(url).status_code, 400)
        self.assertFalse(WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.other).exists())
        user = get_user_model().objects.create_user(username='external', email='NEW@example.test')
        self.client.force_login(user)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertFalse(WorkplaceMembership.objects.filter(user=user).exists())
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertEqual(WorkplaceMembership.objects.get(user=user).role, 'guest')
        invitation.refresh_from_db(); self.assertEqual(invitation.status, 'accepted')

    def test_failed_email_delivery_preserves_link_and_can_be_retried(self):
        with patch('workplaces.invitations.send_mail', side_effect=OSError('SMTP unavailable')):
            response = self.client.post(reverse('workplaces:team', args=[self.workspace.pk]), {'email': self.other.email, 'role': 'member'})
        self.assertEqual(response.status_code, 302)
        invitation = WorkplaceInvitation.objects.get(email=self.other.email)
        self.assertIsNone(invitation.email_sent_at)
        self.client.post(reverse('workplaces:invitation-resend', args=[self.workspace.pk, invitation.pk]))
        invitation.refresh_from_db(); self.assertIsNotNone(invitation.email_sent_at)

    def test_shareable_link_capacity_domain_and_revocation(self):
        link = WorkplaceInviteLink.objects.create(workplace=self.workspace, created_by=self.owner, role='guest', max_uses=1, email_domain='example.test')
        url = reverse('workplaces:join-link', args=[link.token])
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertFalse(WorkplaceMembership.objects.filter(user=self.other).exists())
        self.assertEqual(self.client.post(url).status_code, 302)
        link.refresh_from_db(); self.assertEqual(link.uses, 1)
        self.assertEqual(WorkplaceMembership.objects.get(user=self.other).role, 'guest')
        self.assertEqual(self.client.post(url).status_code, 400)
        fresh = WorkplaceInviteLink.objects.create(workplace=self.workspace, role='member', email_domain='company.test')
        self.assertEqual(self.client.post(reverse('workplaces:join-link', args=[fresh.token])).status_code, 400)
        fresh.revoked_at = timezone.now(); fresh.save()
        self.assertContains(self.client.get(reverse('workplaces:join-link', args=[fresh.token])), 'niedostępne')

    def test_removed_member_cannot_reuse_same_link_and_existing_role_is_never_elevated(self):
        link = WorkplaceInviteLink.objects.create(workplace=self.workspace, role='member')
        url = reverse('workplaces:join-link', args=[link.token])
        self.client.force_login(self.guest)
        self.client.post(url)
        self.membership.refresh_from_db(); self.assertEqual(self.membership.role, 'guest')
        self.client.force_login(self.other); self.client.post(url)
        WorkplaceMembership.objects.filter(user=self.other).delete()
        self.assertEqual(self.client.post(url).status_code, 403)
        self.assertFalse(WorkplaceMembership.objects.filter(user=self.other).exists())

    def test_only_managers_create_links_and_cannot_grant_owner_or_admin_by_link(self):
        url = reverse('workplaces:invite-link-create', args=[self.workspace.pk])
        self.assertEqual(self.client.post(url, {'role': 'owner', 'days': '7', 'max_uses': '10'}).status_code, 400)
        self.client.force_login(self.guest)
        self.assertEqual(self.client.post(url, {'role': 'member', 'days': '7', 'max_uses': '10'}).status_code, 403)
        self.assertFalse(WorkplaceInviteLink.objects.exists())

    def test_signup_from_invite_returns_to_confirmation_without_extra_workspace(self):
        link = WorkplaceInviteLink.objects.create(workplace=self.workspace, role='guest')
        url = reverse('workplaces:join-link', args=[link.token])
        client = Client(); client.get(url)
        response = client.post(reverse('register'), {'first_name': 'Anna', 'last_name': 'Nowak', 'email': 'signup@example.test',
            'password1': 'Invite-registration-83!', 'password2': 'Invite-registration-83!'})
        self.assertEqual(response.url, url)
        user = get_user_model().objects.get(email='signup@example.test')
        self.assertFalse(Workplace.objects.filter(owner=user).exists())
        self.assertFalse(WorkplaceMembership.objects.filter(user=user).exists())
        self.assertEqual(client.post(url).status_code, 302)
        self.assertEqual(WorkplaceMembership.objects.get(user=user).role, 'guest')

    def test_expired_invite_and_csrf_cannot_grant_access(self):
        link = WorkplaceInviteLink.objects.create(workplace=self.workspace, expires_at=timezone.now()-timedelta(seconds=1))
        url = reverse('workplaces:join-link', args=[link.token])
        client = Client(enforce_csrf_checks=True); client.force_login(self.other)
        self.assertEqual(client.post(url).status_code, 403)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(url).status_code, 400)
        self.assertFalse(WorkplaceMembership.objects.filter(user=self.other).exists())


from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import close_old_connections
from django.test import TransactionTestCase


class ConcurrentInviteLinkTests(TransactionTestCase):
    def test_last_available_use_can_be_redeemed_by_only_one_person(self):
        users = get_user_model()
        owner = users.objects.create_user(username='limit-owner', email='limit-owner@example.test')
        first = users.objects.create_user(username='limit-first', email='limit-first@example.test')
        second = users.objects.create_user(username='limit-second', email='limit-second@example.test')
        workplace = create_workplace_for_user(owner, 'Limit linku')
        link = WorkplaceInviteLink.objects.create(workplace=workplace, max_uses=1)
        url = reverse('workplaces:join-link', args=[link.token])
        barrier = Barrier(2)

        def join(user_id):
            close_old_connections()
            try:
                client = Client(); client.force_login(users.objects.get(pk=user_id))
                barrier.wait(timeout=10)
                return client.post(url).status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses = list(pool.map(join, [first.pk, second.pk]))
        self.assertEqual(sorted(statuses), [302, 400])
        link.refresh_from_db(); self.assertEqual(link.uses, 1)
        self.assertEqual(WorkplaceMembership.objects.filter(workplace=workplace).exclude(user=owner).count(), 1)
        self.assertEqual(link.redemptions.count(), 1)
