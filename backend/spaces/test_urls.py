from .testing import make_space
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.db import IntegrityError, close_old_connections, transaction
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from tasks.models import TaskTag
from .models import SpaceTask, Space, SpaceMembership
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import ACTIVE_WORKPLACE_SESSION_KEY, scoped_workplace_app_path
from .models import Space, Team


class SpaceUrlTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='space-slug-owner', email='space-slug-owner@example.test')
        cls.member = get_user_model().objects.create_user(username='space-slug-member', email='space-slug-member@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Adresy przestrzeni')
        cls.other = create_workplace_for_user(cls.owner, 'Inny Workspace')
        cls.membership = WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.project = make_space(user=cls.owner, workplace=cls.workspace, name='Scrum szablon / Żółć')
        cls.space = cls.project
        cls.section = cls.project
        cls.task = SpaceTask.objects.create(created_by=cls.owner, space=cls.section, title='Test adresów')

    def setUp(self):
        self.login(self.owner)

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session[ACTIVE_WORKPLACE_SESSION_KEY] = self.workspace.pk
        session.save()

    def url(self, suffix=''):
        return scoped_workplace_app_path(self.workspace, 'space', f'{self.space.slug}/{suffix}')

    def test_slug_and_old_redirect_preserve_query_and_accessible_navigation(self):
        self.assertEqual(self.space.slug, 'scrum-szablon-zolc')
        self.assertEqual(reverse('spaces:detail', kwargs={'pk': self.space.slug}), f'/space/{self.space.slug}/')
        self.assertEqual(reverse('spaces:detail', kwargs={'pk': self.space.pk}), f'/spaces/{self.space.pk}/')
        for prefix in ['/spaces/', scoped_workplace_app_path(self.workspace, 'spaces')]:
            for method in ['get', 'head']:
                response = getattr(self.client, method)(f'{prefix}{self.space.pk}/?view=list&q=a%20b&page=2', follow=True)
                self.assertEqual(response.status_code, 200)
                target = urlsplit(response.redirect_chain[-1][0])
                self.assertEqual(target.path, self.url())
                self.assertEqual(parse_qs(target.query), {'view': ['list'], 'q': ['a b'], 'page': ['2']})
        for prefix in ['/space/', scoped_workplace_app_path(self.workspace, 'space')]:
            response = self.client.get(f'{prefix}{self.space.slug}/?view=list', follow=True)
            self.assertEqual(response.context['space'].pk, self.space.pk)
            self.assertContains(response, self.url('items/create/'))
            self.assertContains(response, self.url('?view=backlog') if self.space.template == 'scrum' else self.url('?view=board'))
            self.assertTrue(any(s.pk == self.space.pk for s in response.context['navigation_spaces']))

    def test_all_views_and_configuration_use_named_links(self):
        for view in ['overview', 'list', 'board', 'timeline', 'reports', 'tags', 'settings']:
            response = self.client.get(self.url(f'?view={view}'))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context['space_url'], self.url())
            self.assertNotContains(response, f'/spaces/{self.space.pk}/')
        response = self.client.get(self.url('configuration/'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['space_url'], self.url())

    def test_catalog_search_team_and_personal_links_use_names(self):
        self.project.favorited_by.add(self.owner)
        team = Team.objects.create(owner=self.owner, workplace=self.workspace, name='Zespół')
        team.spaces.add(self.space)
        for path in [scoped_workplace_app_path(self.workspace, 'spaces'),
                     scoped_workplace_app_path(self.workspace, 'spaces', 'manage/'),
                     scoped_workplace_app_path(self.workspace, 'teams', f'{team.pk}/'),
                     scoped_workplace_app_path(self.workspace, 'for-you', '?tab=starred')]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, self.url())
        response = self.client.get(scoped_workplace_app_path(self.workspace, 'spaces', 'search/?q=Scrum'))
        self.assertIn(self.url(), response.json()['html'])
        tag = TaskTag.objects.create(user=self.owner, workplace=self.workspace, space=self.space, name='Scrum tag')
        response = self.client.get('/global-search/', {'q': 'Scrum'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.url(), response.content.decode())
        self.assertIn(self.url('?view=tags'), str(response.json()))

    def test_duplicate_names_are_unique_per_workspace_and_constraint_is_enforced(self):
        duplicate = make_space(user=self.owner, workplace=self.workspace, name=self.project.name)
        other = make_space(user=self.owner, workplace=self.other, name=self.project.name)
        self.assertEqual(duplicate.slug, self.space.slug + '-2')
        self.assertEqual(other.slug, self.space.slug)
        self.assertEqual(self.client.get(self.url().replace(self.space.slug, duplicate.slug)).context['space'].pk, duplicate.pk)
        with transaction.atomic(), self.assertRaises(IntegrityError):
            Space.objects.filter(pk=duplicate.pk).update(slug=self.space.slug)

    def test_numeric_empty_long_and_route_names_have_usable_urls(self):
        names = ['15', '😀', '😀', 'create', 'manage', 'items', 'A' * 120, 'A' * 120]
        expected = ['przestrzen-15', 'przestrzen', 'przestrzen-2', 'create', 'manage', 'items', 'a' * 120, 'a' * 120 + '-2']
        for name, slug in zip(names, expected):
            space = make_space(user=self.owner, workplace=self.workspace, name=name)
            self.assertEqual(space.slug, slug)
            path = scoped_workplace_app_path(self.workspace, 'space', f'{slug}/')
            self.assertEqual(self.client.get(path).context['space'].pk, space.pk)
            response = self.client.get(scoped_workplace_app_path(self.workspace, 'spaces', f'manage/{slug}/edit/'))
            self.assertEqual(response.status_code, 200)

    def test_rename_partial_saves_and_legacy_post_keep_address(self):
        original = self.space.slug
        for path in [self.url('edit/'), scoped_workplace_app_path(self.workspace, 'spaces', f'{self.space.pk}/edit/')]:
            response = self.client.post(path, {'name': 'Nowa nazwa', 'description': 'Nowy opis', 'visibility': 'public'})
            self.assertRedirects(response, self.url())
        self.space.refresh_from_db()
        self.space.next_number += 1
        self.space.save(update_fields=['next_number'])
        self.space.refresh_from_db()
        self.assertEqual(self.space.slug, original)
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, 'Nowa nazwa')
        self.assertContains(self.client.get(self.url()), 'Nowa nazwa')

    def test_named_forms_and_save_returns_keep_workspace(self):
        for suffix in ['edit/', 'avatar/', 'items/create/']:
            response = self.client.get(self.url(suffix))
            self.assertEqual(response.status_code, 200)
            self.assertIn(self.url(), response.context['modal']['return_url'])
        self.assertRedirects(self.client.post(self.url('avatar/'), {'avatar': 'rocket'}), self.url())
        response = self.client.post(self.url('items/create/'), {'title': 'Nowe zadanie', 'priority': 'medium', 'work_type': 'task'})
        self.assertRedirects(response, self.url('?view=list'))
        self.assertTrue(SpaceTask.objects.filter(title='Nowe zadanie', space=self.project).exists())

    def test_slug_and_numeric_urls_enforce_privacy_revocation_and_workspace_scope(self):
        self.project.visibility, self.project.private_owner = 'private', self.owner
        self.project.save()
        membership = SpaceMembership.objects.create(space=self.project, user=self.member, role='observer')
        self.login(self.member)
        legacy = scoped_workplace_app_path(self.workspace, 'spaces', f'{self.space.pk}/')
        for path in [self.url(), legacy]:
            self.assertEqual(self.client.get(path, follow=True).status_code, 200)
            self.assertEqual(self.client.post(path + 'edit/', {'name': 'Zmiana'}).status_code, 403)
        membership.delete()
        for path in [self.url(), legacy]:
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404)
            self.assertNotIn('Location', response)
        self.login(self.owner)
        foreign = make_space(user=self.owner, workplace=self.other, name='Obca przestrzeń')
        self.assertEqual(self.client.get(self.url().replace(self.space.slug, foreign.slug)).status_code, 404)
        self.login(self.member)
        self.membership.delete()
        self.assertRedirects(self.client.get(self.url()), '/workplaces/', fetch_redirect_response=False)


class ConcurrentSpaceSlugTests(TransactionTestCase):
    def test_two_creators_with_same_name_get_distinct_slugs(self):
        owner = get_user_model().objects.create_user(username='space-concurrent', email='space-concurrent@example.test')
        workspace = create_workplace_for_user(owner, 'Równoczesne adresy')
        barrier = Barrier(2)

        def create():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return make_space(user_id=owner.pk, workplace_id=workspace.pk, name='Wspólna nazwa').slug
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            slugs = list(pool.map(lambda _: create(), range(2)))
        self.assertEqual(set(slugs), {'wspolna-nazwa', 'wspolna-nazwa-2'})
