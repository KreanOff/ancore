"""Team workflows, per-viewer counts, permissions and ordinary/scoped API parity."""
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import timedelta
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection
from django.test import Client, RequestFactory, TestCase, TransactionTestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import SpaceMembership, SpaceTask, Team, TeamMembership
from .team_queries import directory_context
from .testing import make_space


class TeamSystemTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='team-owner', email='owner@teams.test', first_name='Anna')
        cls.admin = users.objects.create_user(username='team-admin', email='admin@teams.test', first_name='Jan')
        cls.member = users.objects.create_user(username='team-member', email='member@teams.test', first_name='Ola')
        cls.guest = users.objects.create_user(username='team-guest', email='guest@teams.test')
        cls.other = users.objects.create_user(username='team-other', email='other@teams.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Zespoły QA')
        cls.foreign = create_workplace_for_user(cls.other, 'Obce')
        for user, role in [(cls.admin, 'member'), (cls.member, 'member'), (cls.guest, 'guest')]:
            WorkplaceMembership.objects.create(workplace=cls.workspace, user=user, role=role)
        cls.team = Team.objects.create(owner=cls.owner, workplace=cls.workspace, created_by=cls.owner, name='Produkt', description='Wspólna praca nad aplikacją')
        cls.owner_grant = TeamMembership.objects.create(team=cls.team, user=cls.owner, role='admin')
        cls.admin_grant = TeamMembership.objects.create(team=cls.team, user=cls.admin, role='admin')
        cls.member_grant = TeamMembership.objects.create(team=cls.team, user=cls.member)
        cls.empty = Team.objects.create(owner=cls.owner, workplace=cls.workspace, name='Archiwum')
        cls.foreign_team = Team.objects.create(owner=cls.other, workplace=cls.foreign, name='Obcy zespół')
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Rozwój', key='DEV')
        cls.private = make_space(user=cls.owner, workplace=cls.workspace, name='Tajna przestrzeń', visibility='private', private_owner=cls.owner)
        cls.team.spaces.add(cls.space, cls.private)
        now = timezone.now()
        cls.overdue = SpaceTask.objects.create(space=cls.space, created_by=cls.owner, title='Zaległe zadanie', assignee=cls.member, due_at=now - timedelta(days=1))
        cls.soon = SpaceTask.objects.create(space=cls.space, created_by=cls.owner, title='Nadchodzące zadanie', due_at=now + timedelta(days=2))
        cls.closed = SpaceTask.objects.create(space=cls.space, created_by=cls.owner, title='Zakończone zadanie', status='closed', due_at=now - timedelta(days=2))
        cls.hidden = SpaceTask.objects.create(space=cls.private, created_by=cls.owner, title='Tajne zadanie', due_at=now - timedelta(days=2))
        cls.hidden_task = SpaceTask.objects.create(space=cls.space, created_by=cls.owner, title='Tajne w publicznej', visibility='private', private_owner=cls.owner)
        for task in (cls.overdue, cls.soon, cls.closed, cls.hidden, cls.hidden_task):
            item = task.work_item
            item.team = cls.team
            item.save(update_fields=['team'])

    def setUp(self):
        self.login(self.admin)

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def path(self, suffix='', scoped=True):
        return scoped_workplace_app_path(self.workspace, 'teams', suffix) if scoped else '/teams/' + suffix

    def api(self, target, data=None, client=None):
        url = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') + '?' + urlencode({'url': target})
        client = client or self.client
        return client.get(url) if data is None else client.post(url, data)

    def detail(self, query='', scoped=True):
        response = self.api(self.path(f'{self.team.pk}/' + query, scoped))
        self.assertEqual(response.status_code, 200, response.content[:1000])
        return response.json()['data']

    def test_directory_search_tabs_sort_counts_and_scoped_parity(self):
        for scoped in (True, False):
            for query in ('?q=aplikacją', '?tab=mine', '?tab=managed'):
                data = self.api(self.path(query, scoped)).json()['data']
                self.assertEqual([row['id'] for row in data['teams']], [self.team.pk])
                row = data['teams'][0]
                self.assertEqual((row['member_count'], row['open_count'], row['space_count']), (3, 2, 1))
                self.assertTrue(row['is_admin'])
            data = self.api(self.path('?sort=members', scoped)).json()['data']
            self.assertEqual(data['teams'][0]['id'], self.team.pk)
            self.assertEqual(len(data['teams']), 2)
            self.assertTrue(all(row['url'].startswith(self.path()) for row in data['teams']))

    def test_summary_does_not_leak_private_work_even_in_counts(self):
        for scoped in (True, False):
            data = self.detail(scoped=scoped)
            self.assertEqual(data['counts'], {'total': 3, 'open': 2, 'closed': 1, 'overdue': 1, 'due': 1, 'blocked': 0, 'unassigned': 1})
            self.assertEqual(data['progress'], 33)
            self.assertEqual(sum(row['count'] for row in data['workload']), 2)
            self.assertNotIn('Tajne', json.dumps(data))
            self.assertEqual(data['space_count'], 1)

    def test_filters_search_key_assignee_and_date_exclude_closed_overdue(self):
        cases = [('overdue', [self.overdue.pk]), ('due', [self.soon.pk]), ('closed', [self.closed.pk]), ('unassigned', [self.soon.pk]), ('blocked', [])]
        for scope, ids in cases:
            data = self.detail('?view=work&scope=' + scope)
            self.assertEqual([row['task_id'] for row in data['items']], ids)
        key = self.overdue.work_item.key
        self.assertEqual(self.detail('?view=work&q=' + key)['pagination']['count'], 1)
        self.assertEqual(self.detail(f'?view=work&assignee={self.member.pk}')['pagination']['count'], 1)
        self.assertEqual(self.detail('?view=work&assignee=me')['pagination']['count'], 0)
        self.assertEqual(self.detail('?view=work&q=Tajne')['pagination']['count'], 0)
        self.assertEqual(self.detail('?view=work&scope=invalid&assignee=9999999999999999999999')['pagination']['count'], 3)

    def test_members_filtered_and_spaces_visible_only(self):
        data = self.detail('?view=members&q=Ola')
        self.assertEqual([row['id'] for row in data['members']], [self.member_grant.pk])
        self.assertEqual(self.detail('?view=members&role=admin')['pagination']['count'], 2)
        data = self.detail('?view=spaces')
        self.assertEqual([row['id'] for row in data['spaces']], [self.space.pk])
        self.assertEqual(self.detail('?view=spaces&q=Tajna')['pagination']['count'], 0)

    def test_create_validates_duplicate_and_keeps_actor(self):
        self.login(self.member)
        response = self.api(self.path('create/'), {'name': 'Wsparcie', 'description': 'Pomoc', 'spaces': [self.space.pk]})
        self.assertEqual(response.status_code, 200)
        team = Team.objects.get(name='Wsparcie')
        self.assertEqual((team.owner, team.created_by), (self.owner, self.member))
        self.assertEqual(team.memberships.get(user=self.member).role, 'admin')
        self.assertEqual(self.api(self.path('create/'), {'name': 'wSpArCiE'}).status_code, 400)
        self.assertEqual(self.api(self.path('create/'), {'name': '  '}).status_code, 400)
        self.assertEqual(self.api(self.path('create/'), {'name': 'Nie', 'spaces': [self.private.pk]}).status_code, 400)

    def test_edit_preserves_hidden_space_links_without_disclosing_initial_values(self):
        target = self.path(f'{self.team.pk}/edit/')
        data = self.api(target).json()['data']['form']
        field = next(field for field in data['fields'] if field['name'] == 'spaces')
        self.assertNotIn(str(self.private.pk), field['value'])
        self.assertEqual(self.api(target, {'name': 'Nowa nazwa', 'spaces': []}).status_code, 200)
        self.assertEqual(list(self.team.spaces.all()), [self.private])

    def test_add_member_role_edit_remove_and_scope_tampering(self):
        target = self.path(f'{self.team.pk}/members/')
        self.assertEqual(self.api(target, {'person': self.other.pk, 'role': 'member'}).status_code, 400)
        self.assertEqual(self.api(target, {'person': self.guest.pk, 'role': 'member'}).status_code, 200)
        grant = self.team.memberships.get(user=self.guest)
        self.assertEqual(self.api(target, {'person': self.guest.pk, 'role': 'member'}).status_code, 400)
        self.assertEqual(self.api(self.path(f'{self.team.pk}/members/{grant.pk}/edit/'), {'person': self.other.pk, 'role': 'admin'}).status_code, 400)
        self.assertFalse(self.team.memberships.filter(user=self.other).exists())
        edit = self.path(f'{self.team.pk}/members/{self.member_grant.pk}/edit/')
        self.assertEqual(self.api(edit, {'person': self.other.pk, 'role': 'admin'}).status_code, 200)
        self.member_grant.refresh_from_db()
        self.assertEqual(self.member_grant.role, 'admin')
        remove = self.path(f'{self.team.pk}/members/{grant.pk}/remove/')
        self.assertEqual(self.api(remove).status_code, 405)
        self.assertEqual(self.api(remove, {}).status_code, 200)
        self.assertFalse(self.team.memberships.filter(pk=grant.pk).exists())

    def test_last_admin_is_protected_in_ui_and_both_write_paths(self):
        self.owner_grant.delete()
        member = next(row for row in self.detail('?view=members')['members'] if row['id'] == self.admin_grant.pk)
        self.assertFalse(member['can_change'])
        self.assertEqual(self.api(self.path(f'{self.team.pk}/members/{self.admin_grant.pk}/edit/'), {'role': 'member'}).status_code, 400)
        self.assertEqual(self.api(self.path(f'{self.team.pk}/members/{self.admin_grant.pk}/remove/'), {}).status_code, 400)
        self.assertEqual(self.team.memberships.get(pk=self.admin_grant.pk).role, 'admin')

    def test_guest_with_stale_admin_role_cannot_manage_or_replace_last_admin(self):
        TeamMembership.objects.create(team=self.team, user=self.guest, role='admin')
        self.owner_grant.delete()
        self.assertEqual(self.api(self.path(f'{self.team.pk}/members/{self.admin_grant.pk}/remove/'), {}).status_code, 400)
        self.login(self.guest)
        self.assertFalse(self.detail()['can_manage'])
        self.assertFalse(self.api(self.path()).json()['data']['create_url'])
        self.assertEqual(self.api(self.path('?tab=managed')).json()['data']['teams'], [])
        for suffix in ('edit/', 'delete/', 'members/'):
            self.assertEqual(self.api(self.path(f'{self.team.pk}/' + suffix)).status_code, 403)
            self.assertEqual(self.api(self.path(f'{self.team.pk}/' + suffix), {}).status_code, 403)

    def test_regular_member_cannot_manage_and_revocation_is_immediate(self):
        self.login(self.member)
        self.assertFalse(self.detail()['can_manage'])
        for suffix in ('edit/', 'delete/', 'members/', f'members/{self.admin_grant.pk}/edit/', f'members/{self.admin_grant.pk}/remove/'):
            self.assertEqual(self.api(self.path(f'{self.team.pk}/' + suffix), {}).status_code, 403)
        self.login(self.admin)
        self.admin_grant.role = 'member'
        self.admin_grant.save()
        self.assertEqual(self.api(self.path(f'{self.team.pk}/edit/'), {'name': 'Nie'}).status_code, 403)
        self.assertEqual(self.api(self.path(f'{self.foreign_team.pk}/')).status_code, 404)

    def test_delete_requires_matching_name_and_preserves_tasks_and_space_access(self):
        target = self.path(f'{self.team.pk}/delete/')
        self.assertEqual(self.api(target).status_code, 200)
        self.assertTrue(Team.objects.filter(pk=self.team.pk).exists())
        self.assertEqual(self.api(target, {'name': 'Błąd'}).status_code, 400)
        grant = SpaceMembership.objects.create(space=self.private, user=self.admin, role='member')
        before = {task.pk: (task.status, task.work_item.key, task.activities.count()) for task in (self.overdue, self.soon, self.hidden)}
        self.assertEqual(self.api(target, {'name': self.team.name}).status_code, 200)
        self.assertFalse(Team.objects.filter(pk=self.team.pk).exists())
        self.assertTrue(SpaceMembership.objects.filter(pk=grant.pk).exists())
        for pk, values in before.items():
            task = SpaceTask.objects.get(pk=pk)
            self.assertEqual((task.status, task.work_item.key, task.activities.count()), values)
            self.assertIsNone(task.work_item.team_id)

    def test_member_removal_preserves_task_assignment_and_space_access(self):
        grant = SpaceMembership.objects.create(space=self.private, user=self.member)
        self.assertEqual(self.api(self.path(f'{self.team.pk}/members/{self.member_grant.pk}/remove/'), {}).status_code, 200)
        self.overdue.refresh_from_db()
        self.assertEqual(self.overdue.assignee, self.member)
        self.assertTrue(SpaceMembership.objects.filter(pk=grant.pk).exists())
        self.assertTrue(WorkplaceMembership.objects.filter(user=self.member, workplace=self.workspace).exists())

    def test_disabled_team_module_revoked_workspace_and_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.admin)
        target = self.path(f'{self.team.pk}/delete/')
        self.assertEqual(self.api(target, {'name': self.team.name}, csrf_client).status_code, 403)
        self.workspace.disabled_modules = ['teams']
        self.workspace.save()
        self.assertEqual(self.api(self.path()).status_code, 404)
        self.assertEqual(self.client.get(self.path()).status_code, 404)
        self.workspace.disabled_modules = []
        self.workspace.save()
        WorkplaceMembership.objects.get(user=self.admin, workplace=self.workspace).delete()
        self.assertFalse(self.team.memberships.filter(user=self.admin).exists())
        self.assertEqual(self.api(self.path()).status_code, 403)

    def test_pagination_preserves_filters_and_directory_queries_do_not_grow_per_team(self):
        def query_count():
            request = RequestFactory().get('/teams/')
            request.user, request.workplace = self.admin, self.workspace
            with CaptureQueriesContext(connection) as queries:
                directory_context(request)
            return len(queries)
        initial = query_count()
        Team.objects.bulk_create([Team(owner=self.owner, workplace=self.workspace, name=f'Zespół {number:02}', description='szukany') for number in range(28)])
        self.assertLessEqual(query_count(), initial + 1)
        data = self.api(self.path('?q=szukany&sort=members')).json()['data']
        self.assertEqual((len(data['teams']), data['pagination']['count']), (20, 28))
        self.assertIn('q=szukany', data['pagination']['next'])
        self.assertIn('sort=members', data['pagination']['next'])
        final = self.api(data['pagination']['next']).json()['data']
        self.assertEqual(len(final['teams']), 28)
        self.assertEqual(final['teams'][:20], data['teams'])
        self.assertEqual(final['pagination']['next'], '')

    def test_html_templates_render_all_views_with_native_forms(self):
        for suffix in ('', f'{self.team.pk}/', f'{self.team.pk}/?view=work', f'{self.team.pk}/?view=members', f'{self.team.pk}/?view=spaces'):
            response = self.client.get(self.path(suffix))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'data-react-root="page"')
            self.assertNotContains(response, 'Tajne zadanie')

    def test_photo_removal_is_validated_and_deferred_until_commit(self):
        from core.test_comment_images import photo
        target = self.path(f'{self.team.pk}/edit/')
        self.assertEqual(self.api(target, {'name': self.team.name, 'photo': photo()}).status_code, 200)
        self.team.refresh_from_db()
        name, storage = self.team.photo.name, self.team.photo.storage
        self.assertTrue(storage.exists(name))
        conflict = self.api(target, {'name': self.team.name, 'photo': photo(), 'remove_photo': 'on'})
        self.assertEqual(conflict.status_code, 400)
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(self.api(target, {'name': self.team.name, 'remove_photo': 'on'}).status_code, 200)
            self.assertTrue(storage.exists(name))
        self.team.refresh_from_db()
        self.assertFalse(self.team.photo)
        self.assertFalse(storage.exists(name))
        self.assertEqual(self.client.get(self.path(f'{self.team.pk}/photo/')).status_code, 404)

    def test_lost_space_access_rejects_entire_profile_save(self):
        from unittest.mock import patch
        from .models import Space
        with patch('spaces.teams.visible_spaces', return_value=Space.objects.none()):
            response = self.api(self.path(f'{self.team.pk}/edit/'), {'name': 'Nie zapisz', 'spaces': [self.space.pk]})
        self.assertEqual(response.status_code, 400)
        self.team.refresh_from_db()
        self.assertEqual(self.team.name, 'Produkt')
        self.assertEqual(self.team.spaces.count(), 2)

    def test_guest_membership_elsewhere_does_not_disable_current_admin(self):
        WorkplaceMembership.objects.create(workplace=self.foreign, user=self.admin, role='guest')
        self.owner_grant.delete()
        self.assertEqual(self.api(self.path(f'{self.team.pk}/members/{self.admin_grant.pk}/remove/'), {}).status_code, 400)
        self.assertTrue(self.team.memberships.filter(pk=self.admin_grant.pk).exists())

    def test_api_loads_member_table_styles_for_initial_navigation_and_reentry(self):
        for target in [self.path(), self.path(f'{self.team.pk}/?view=members')]:
            payload = self.api(target).json()
            self.assertTrue(any('workplace-team.css' in url for url in payload['styles']))

    def test_member_search_accepts_full_names_and_account_handles(self):
        self.member.middle_name, self.member.last_name = 'Maria', 'Nowak'
        self.member.save()
        for query in ('Ola Maria Nowak', '@team-member'):
            data = self.detail('?' + urlencode({'view': 'members', 'q': query}))
            self.assertEqual([row['id'] for row in data['members']], [self.member_grant.pk])
        self.assertIn('Ola Maria Nowak', [row['name'] for row in self.detail()['workload']])


class TeamAdminConcurrencyTests(TransactionTestCase):
    def test_concurrent_removals_keep_one_active_administrator(self):
        users = get_user_model()
        owner = users.objects.create_user(username='concurrent-team-owner', email='owner@concurrent.test')
        second = users.objects.create_user(username='concurrent-team-admin', email='admin@concurrent.test')
        workspace = create_workplace_for_user(owner, 'Concurrent teams')
        WorkplaceMembership.objects.create(workplace=workspace, user=second)
        team = Team.objects.create(owner=owner, workplace=workspace, name='Dwie osoby')
        grants = [TeamMembership.objects.create(team=team, user=user, role='admin') for user in (owner, second)]
        clients = [Client(), Client()]
        for client in clients:
            client.force_login(owner)
        barrier = Barrier(2)

        def remove(index):
            close_old_connections()
            try:
                target = scoped_workplace_app_path(workspace, 'teams', f'{team.pk}/members/{grants[index].pk}/remove/')
                api = scoped_workplace_app_path(workspace, 'api', 'v1/page/') + '?' + urlencode({'url': target})
                barrier.wait(timeout=10)
                return clients[index].post(api).status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(remove, index) for index in range(2)]
            statuses = [future.result(timeout=20) for future in futures]
        self.assertEqual(sorted(statuses), [200, 400])
        self.assertEqual(team.memberships.filter(role='admin').count(), 1)
