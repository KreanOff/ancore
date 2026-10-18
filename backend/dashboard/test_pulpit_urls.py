from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.contrib.auth import get_user_model
from django.db import IntegrityError, close_old_connections, transaction
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import ACTIVE_WORKPLACE_SESSION_KEY, scoped_workplace_app_path
from .models import Dashboard, DashboardGadget


class PulpitUrlTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='slug-owner', email='slug-owner@example.test')
        cls.member = get_user_model().objects.create_user(username='slug-member', email='slug-member@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Adresy pulpitów')
        cls.other = create_workplace_for_user(cls.owner, 'Inny Workspace')
        cls.membership = WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.dashboard = Dashboard.objects.create(owner=cls.owner, workplace=cls.workspace, created_by=cls.owner,
                                                 name='Plan zespołu / Żółć', visibility='workspace')

    def setUp(self):
        self.login(self.owner)

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session[ACTIVE_WORKPLACE_SESSION_KEY] = self.workspace.pk
        session.save()

    def prefixes(self):
        return ['/dashboards/', scoped_workplace_app_path(self.workspace, 'dashboards')]

    def test_name_based_detail_and_legacy_redirect_preserve_filters_and_sidebar(self):
        self.assertEqual(self.dashboard.slug, 'plan-zespolu-zolc')
        self.dashboard.favorited_by.add(self.owner)
        canonical = self.prefixes()[1] + self.dashboard.slug + '/'
        self.assertEqual(reverse('pulpits:detail', kwargs={'pk': self.dashboard.slug}), self.prefixes()[0] + self.dashboard.slug + '/')
        self.assertEqual(reverse('pulpits:detail', kwargs={'pk': self.dashboard.pk}), self.prefixes()[0] + str(self.dashboard.pk) + '/')
        for prefix in self.prefixes():
            response = self.client.get(prefix + str(self.dashboard.pk) + '/?q=Plan&page=2')
            self.assertRedirects(response, canonical + '?q=Plan&page=2')
            response = self.client.get(prefix + self.dashboard.slug + '/', follow=True)
            self.assertEqual(response.context['dashboard'].pk, self.dashboard.pk)
            self.assertTrue(response.context['navigation_starred_dashboards'][0].is_current)
            self.assertContains(response, canonical + 'gadgets/')

    def test_duplicate_names_are_unique_across_creators_within_workspace(self):
        duplicate = Dashboard.objects.create(owner=self.owner, workplace=self.workspace, created_by=self.member,
                                              name=self.dashboard.name, visibility='workspace')
        self.assertEqual(duplicate.slug, self.dashboard.slug + '-2')
        other = Dashboard.objects.create(owner=self.owner, workplace=self.other, created_by=self.owner, name=self.dashboard.name)
        self.assertEqual(other.slug, self.dashboard.slug)
        response = self.client.get(scoped_workplace_app_path(self.other, 'dashboards', other.slug + '/'))
        self.assertEqual(response.context['dashboard'].pk, other.pk)
        self.assertEqual(self.client.get(self.prefixes()[1] + duplicate.slug + '/').context['dashboard'].pk, duplicate.pk)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Dashboard.objects.create(owner=self.owner, workplace=self.workspace, created_by=self.owner,
                                     name='Inna nazwa', slug=self.dashboard.slug)

    def test_reserved_numeric_empty_and_long_names_have_usable_urls(self):
        names = ['default', 'manage', 'create', 'search', 'groups', '15', '😀', '😀', 'A' * 150, 'A' * 150]
        slugs = ['pulpit-default', 'pulpit-manage', 'pulpit-create', 'pulpit-search', 'pulpit-groups',
                 'pulpit-15', 'pulpit', 'pulpit-2', 'a' * 150, 'a' * 150 + '-2']
        for name, slug in zip(names, slugs):
            item = Dashboard.objects.create(owner=self.owner, workplace=self.workspace, created_by=self.owner, name=name)
            self.assertEqual(item.slug, slug)
            for prefix in self.prefixes():
                self.assertEqual(self.client.get(prefix + slug + '/', follow=True).context['dashboard'].pk, item.pk)
        for prefix in self.prefixes():
            for method in ['get', 'post']:
                self.assertEqual(getattr(self.client, method)(prefix + 'groups/', follow=True).status_code, 404)

    def test_rename_and_partial_saves_keep_existing_links(self):
        original_slug = self.dashboard.slug
        response = self.client.post(self.prefixes()[1] + original_slug + '/edit/', {'name': 'Nowy tytuł', 'description': 'Nowy opis'})
        self.assertRedirects(response, self.prefixes()[1] + original_slug + '/')
        self.dashboard.refresh_from_db()
        self.assertEqual((self.dashboard.name, self.dashboard.slug), ('Nowy tytuł', original_slug))
        self.dashboard.name = 'Jeszcze inny tytuł'
        self.dashboard.save(update_fields=['name'])
        self.dashboard.revision += 1
        self.dashboard.save(update_fields=['revision'])
        self.dashboard.refresh_from_db()
        self.assertEqual(self.dashboard.slug, original_slug)
        replacement = Dashboard.objects.create(owner=self.owner, workplace=self.workspace, created_by=self.owner,
                                                name='Plan zespołu / Żółć')
        self.assertEqual(replacement.slug, original_slug + '-2')

    def test_permissions_revocation_and_workspace_isolation_apply_to_both_identifiers(self):
        self.dashboard.visibility = 'selected'
        self.dashboard.save()
        self.dashboard.shared_with.add(self.member)
        self.login(self.member)
        for prefix in self.prefixes():
            self.assertEqual(self.client.get(prefix + self.dashboard.slug + '/').status_code, 200)
            for identifier in [self.dashboard.pk, self.dashboard.slug]:
                self.assertEqual(self.client.get(prefix + f'{identifier}/gadgets/').status_code, 403)
                self.assertEqual(self.client.post(prefix + f'{identifier}/delete/').status_code, 403)
        self.dashboard.shared_with.clear()
        for prefix in self.prefixes():
            for identifier in [self.dashboard.pk, self.dashboard.slug]:
                self.assertEqual(self.client.get(prefix + f'{identifier}/', follow=True).status_code, 404)
        self.login(self.owner)
        foreign = Dashboard.objects.create(owner=self.owner, workplace=self.other, created_by=self.owner, name='Obcy pulpit')
        for prefix in self.prefixes():
            self.assertEqual(self.client.get(prefix + foreign.slug + '/').status_code, 404)
        self.login(self.member)
        self.membership.delete()
        self.assertRedirects(self.client.get(self.prefixes()[1] + self.dashboard.slug + '/'), '/workplaces/', fetch_redirect_response=False)

    def test_numeric_post_endpoints_still_work_and_return_named_links(self):
        gadget = DashboardGadget.objects.create(dashboard=self.dashboard, kind='progress')
        target = self.prefixes()[1] + self.dashboard.slug + '/gadgets/'
        for prefix in self.prefixes():
            response = self.client.post(prefix + f'{self.dashboard.pk}/gadgets/{gadget.pk}/edit/',
                                        {'kind': 'progress', 'title': 'Moje zadania', 'assignee': 'me'})
            self.assertRedirects(response, target)
        self.assertEqual(Client().get(self.prefixes()[1] + self.dashboard.slug + '/').status_code, 302)
        self.assertEqual(self.client.get(self.prefixes()[1] + self.dashboard.slug + '/favorite/').status_code, 405)


class PulpitSlugConcurrencyTests(TransactionTestCase):
    def test_concurrent_creators_receive_different_slugs(self):
        owner = get_user_model().objects.create_user(username='slug-concurrent', email='slug-concurrent@example.test')
        workspace = create_workplace_for_user(owner, 'Równoczesne pulpity')
        barrier = Barrier(2)

        def create_dashboard():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return Dashboard.objects.create(owner_id=owner.pk, created_by_id=owner.pk,
                                                workplace_id=workspace.pk, name='Ten sam pulpit').slug
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(create_dashboard) for _ in range(2)]
            slugs = {future.result(timeout=20) for future in futures}
        self.assertEqual(slugs, {'ten-sam-pulpit', 'ten-sam-pulpit-2'})
