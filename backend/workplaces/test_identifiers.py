from importlib import import_module
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, TransactionTestCase
from django.urls import reverse

from .forms import WorkplaceForm
from .middleware import ActiveWorkplaceMiddleware
from .models import Workplace, WorkplaceMembership, create_workplace_for_user
from .services import SCOPED_WORKPLACE_APPS, scoped_workplace_app_path


class WorkspaceIdentifierTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='identifier-owner', email='id-owner@example.test')
        cls.member = get_user_model().objects.create_user(username='identifier-member', email='id-member@example.test')
        cls.other = get_user_model().objects.create_user(username='identifier-other', email='id-other@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Dowolna nazwa')
        cls.workspace.legacy_slug = 'stary-workspace'
        cls.workspace.save(update_fields=['legacy_slug'])
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member, role='member')

    def test_same_name_is_allowed_for_same_and_different_owners(self):
        same = create_workplace_for_user(self.owner, self.workspace.name)
        other = create_workplace_for_user(self.other, self.workspace.name)
        self.assertEqual(len({workspace.code for workspace in [same, other, self.workspace]}), 3)
        for workspace in [same, other, self.workspace]:
            self.assertRegex(workspace.code, r'^w_[a-z0-9]{26}$')
            self.assertEqual(workspace.slug, workspace.code)
            self.assertEqual(reverse('workplaces:workplace-home', args=[workspace.code]), f'/workplaces/{workspace.code}/')

    def test_non_latin_names_do_not_affect_identifier(self):
        form = WorkplaceForm({'name': '工作区 🧭 / #'}, user=self.owner)
        self.assertTrue(form.is_valid(), form.errors)
        workspace = create_workplace_for_user(self.owner, form.cleaned_data['name'])
        self.assertRegex(workspace.code, r'^w_[a-z0-9]{26}$')

    def test_database_enforces_global_code_uniqueness(self):
        other = create_workplace_for_user(self.other, 'Inny właściciel')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Workplace.objects.filter(pk=other.pk).update(code=self.workspace.code)

    def test_database_collision_retries_without_breaking_creation_transaction(self):
        replacement = 'w_' + 'z' * 26
        workspace = Workplace(owner=self.other, name='Kolizja', code=self.workspace.code)
        with patch('workplaces.models.generate_workplace_code', return_value=replacement) as generate:
            with transaction.atomic():
                workspace.save()
                workspace.ensure_owner_membership()
        generate.assert_called_once()
        self.assertEqual(workspace.code, replacement)
        self.assertEqual(workspace.slug, replacement)
        self.assertTrue(workspace.memberships.filter(user=self.other, role='owner').exists())

    def test_random_code_cannot_reuse_legacy_url(self):
        replacement = 'w_' + 'x' * 26
        workspace = Workplace(owner=self.other, name='Kolizja starego adresu', code=self.workspace.legacy_slug)
        with patch('workplaces.models.generate_workplace_code', return_value=replacement):
            workspace.save()
        self.assertEqual(workspace.slug, replacement)

    def test_identifier_and_url_survive_partial_save_and_forged_form_fields(self):
        original = self.workspace.code
        form = WorkplaceForm({
            'name': 'Nowa nazwa', 'code': 'zmieniony', 'slug': 'zmieniony', 'legacy_slug': 'zmieniony',
        }, instance=self.workspace, user=self.owner)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        self.workspace.description = 'Opis'
        self.workspace.save(update_fields=['description'])
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.code, original)
        self.assertEqual(self.workspace.slug, original)
        self.assertEqual(self.workspace.legacy_slug, 'stary-workspace')

    def test_old_get_and_head_links_redirect_with_module_path_and_query(self):
        self.client.force_login(self.member)
        for method in [self.client.get, self.client.head]:
            for app in SCOPED_WORKPLACE_APPS:
                with self.subTest(method=method.__name__, app=app):
                    response = method(f'/workplaces/stary-workspace/{app}/nested/path/?q=abc&page=2')
                    self.assertEqual(response.status_code, 302)
                    self.assertEqual(response.url, scoped_workplace_app_path(self.workspace, app, 'nested/path/') + '?q=abc&page=2')
                    self.assertEqual(self.client.session['active_workplace_id'], self.workspace.pk)

    def test_old_post_keeps_body_and_workspace_context(self):
        request = RequestFactory().post('/workplaces/stary-workspace/tasks/', {'title': 'Zachowany POST'})
        request.user, request.session = self.member, SessionStore()
        received = []

        def handler(request):
            received.append((request.workplace.pk, request.POST['title']))
            return HttpResponse('OK')

        response = ActiveWorkplaceMiddleware(handler)(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(received, [(self.workspace.pk, 'Zachowany POST')])

    def test_old_and_new_home_links_lead_to_same_workspace(self):
        self.client.force_login(self.owner)
        for identifier in [self.workspace.slug, self.workspace.legacy_slug]:
            response = self.client.get(reverse('workplaces:workplace-home', args=[identifier]))
            self.assertRedirects(response, scoped_workplace_app_path(self.workspace), fetch_redirect_response=False)

    def test_alias_and_random_code_do_not_bypass_membership(self):
        self.client.force_login(self.other)
        for identifier in [self.workspace.slug, self.workspace.legacy_slug]:
            response = self.client.get(f'/workplaces/{identifier}/tasks/')
            self.assertRedirects(response, reverse('workplaces:workplaces'), fetch_redirect_response=False)
            self.assertEqual(self.client.get(f'/workplaces/{identifier}/').status_code, 404)
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.member).update(is_active=False)
        self.client.force_login(self.member)
        self.assertRedirects(self.client.get('/workplaces/stary-workspace/tasks/'), reverse('workplaces:workplaces'), fetch_redirect_response=False)


class WorkspaceIdentifierMigrationTests(TransactionTestCase):
    def test_existing_data_and_old_links_are_preserved(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        previous = [node for node in latest if node[0] != 'workplaces'] + [('workplaces', '0009_workplace_avatar')]
        executor.migrate(previous)
        try:
            # Other apps' leaf nodes can depend on 0010. The rollback also
            # unapplies those dependants; build fixtures from the actual schema.
            loader = MigrationExecutor(connection).loader
            state = loader.project_state(list(loader.applied_migrations)).apps
            User = state.get_model('accounts', 'User')
            OldWorkplace = state.get_model('workplaces', 'Workplace')
            owner = User.objects.create(username='old-id-owner', email='old-id-owner@example.test')
            member = User.objects.create(username='old-id-member', email='old-id-member@example.test')
            reserved = 'w_' + 'a' * 26
            first = OldWorkplace.objects.create(owner=owner, name='Studio', code='STUDIO', slug=reserved, description='Zachowany opis', avatar='book')
            second = OldWorkplace.objects.create(owner=member, name='Studio', code='STUDIO', slug='studio-member')
            membership = state.get_model('workplaces', 'WorkplaceMembership').objects.create(workplace=first, user=member, role='admin')
            task = state.get_model('tasks', 'Task').objects.create(user=owner, workplace=first, title='Zachowane zadanie', task_id=1)
            # First candidate collides with an old URL; second Workspace then
            # collides with the identifier already assigned to the first.
            migration = import_module('workplaces.migrations.0010_random_workspace_identifiers')
            with patch.object(migration.secrets, 'choice', side_effect=list('a' * 26 + 'b' * 26 + 'b' * 26 + 'c' * 26)):
                MigrationExecutor(connection).migrate(latest)
            first = Workplace.objects.get(pk=first.pk)
            second = Workplace.objects.get(pk=second.pk)
            self.assertEqual(first.code, 'w_' + 'b' * 26)
            self.assertEqual(second.code, 'w_' + 'c' * 26)
            self.assertEqual(first.slug, first.code)
            self.assertEqual(first.legacy_slug, reserved)
            self.assertEqual(second.legacy_slug, 'studio-member')
            self.assertEqual((first.name, first.description, first.avatar, first.owner_id), ('Studio', 'Zachowany opis', 'book', owner.pk))
            self.assertTrue(WorkplaceMembership.objects.filter(pk=membership.pk, workplace=first, user_id=member.pk, role='admin', is_active=True).exists())
            from tasks.models import Task
            self.assertEqual(Task.objects.get(pk=task.pk).workplace_id, first.pk)
            create_workplace_for_user(get_user_model().objects.get(pk=owner.pk), 'Studio')
        finally:
            MigrationExecutor(connection).migrate(latest)
