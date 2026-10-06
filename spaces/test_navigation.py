from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from tasks.models import TaskProject, TaskProjectMembership
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class SpaceNavigationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='space-nav-owner', email='space-nav-owner@example.test')
        cls.member = get_user_model().objects.create_user(username='space-nav-member', email='space-nav-member@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Nawigacja')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.first = TaskProject.objects.create(user=cls.owner, workplace=cls.workspace, name='Pierwsza')
        cls.second = TaskProject.objects.create(user=cls.owner, workplace=cls.workspace, name='Druga')
        cls.private = TaskProject.objects.create(user=cls.owner, workplace=cls.workspace, name='Prywatna', visibility='private', private_owner=cls.owner)
        cls.other_workspace = create_workplace_for_user(cls.owner, 'Inny Workspace')
        cls.foreign = TaskProject.objects.create(user=cls.owner, workplace=cls.other_workspace, name='Obca')

    def setUp(self):
        self.login(self.owner)

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, project=None, suffix=''):
        return scoped_workplace_app_path(self.workspace, 'spaces', f'{project.space.pk}/{suffix}' if project else suffix)

    def project_ids(self, response, group):
        return [space.project_id for space in response.context[f'navigation_{group}_spaces']]

    def test_visits_move_space_to_top_immediately_in_plain_and_scoped_routes(self):
        for url in [f'/spaces/{self.first.space.pk}/', self.url(self.second), self.url(self.first, '?view=list')]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(self.project_ids(response, 'recent')[0], response.context['space'].project_id)
        response = self.client.get(self.url())
        self.assertEqual(self.project_ids(response, 'recent')[:2], [self.first.pk, self.second.pk])

    def test_personal_starred_group_and_limit_have_no_duplicates(self):
        self.first.favorited_by.add(self.owner)
        for number in range(8):
            TaskProject.objects.create(user=self.owner, workplace=self.workspace, name=f'Dodatkowa {number}')
        self.client.get(self.url(self.first))
        response = self.client.get(self.url())
        self.assertEqual(self.project_ids(response, 'starred'), [self.first.pk])
        self.assertNotIn(self.first.pk, self.project_ids(response, 'recent'))
        self.assertEqual(len(response.context['navigation_spaces']), 6)
        self.login(self.member)
        self.assertEqual(self.project_ids(self.client.get(self.url()), 'starred'), [])

    def test_history_and_favorites_recheck_access_and_workspace(self):
        self.login(self.member)
        self.first.favorited_by.add(self.member)
        self.client.get(self.url(self.second))
        self.second.visibility, self.second.private_owner = 'private', self.owner
        self.second.save()
        self.first.visibility, self.first.private_owner = 'private', self.owner
        self.first.save()
        self.foreign.favorited_by.add(self.member)
        response = self.client.get(self.url())
        self.assertEqual(response.context['navigation_spaces'], [])
        self.assertNotContains(response, 'id="sidebar-spaces-recent-title"')
        self.assertNotContains(response, 'id="sidebar-spaces-starred-title"')
        self.assertContains(response, 'Więcej przestrzeni')
        self.assertEqual(self.client.post(self.url(self.first, 'favorite/'), HTTP_X_SPACE_NAVIGATION='true').status_code, 404)

    def test_menu_actions_follow_project_management_roles(self):
        TaskProjectMembership.objects.create(project=self.private, user=self.member, role='observer')
        self.login(self.member)
        response = self.client.get(self.url())
        self.assertNotContains(response, '>Dodaj osoby</span>')
        self.assertContains(response, 'Ustawienia przestrzeni</span>')
        self.assertEqual(self.client.get(self.url(self.private, 'members/')).status_code, 403)
        self.assertEqual(self.client.get(self.url(self.private, '?view=settings')).status_code, 200)
        TaskProjectMembership.objects.filter(project=self.private, user=self.member).update(role='admin')
        self.assertContains(self.client.get(self.url()), '>Dodaj osoby</span>')
        self.assertEqual(self.client.get(self.url(self.private, 'members/')).status_code, 200)
        TaskProjectMembership.objects.filter(project=self.private, user=self.member).delete()
        self.assertNotContains(self.client.get(self.url()), 'Prywatna')

    def test_favorite_ajax_updates_same_personal_relation_and_groups(self):
        self.login(self.member)
        url = self.url(self.first, 'favorite/')
        response = self.client.post(url, HTTP_X_SPACE_NAVIGATION='true')
        self.assertEqual(response.json(), {'saved': True})
        self.assertTrue(self.first.favorited_by.filter(pk=self.member.pk).exists())
        self.assertFalse(self.first.favorited_by.filter(pk=self.owner.pk).exists())
        self.assertEqual(self.project_ids(self.client.get(self.url()), 'starred'), [self.first.pk])
        self.client.post(url, HTTP_X_SPACE_NAVIGATION='true')
        self.assertEqual(self.project_ids(self.client.get(self.url()), 'starred'), [])
        self.assertEqual(self.client.get(url).status_code, 405)

    def test_favorite_csrf_and_safe_return_without_javascript(self):
        secure = Client(enforce_csrf_checks=True)
        secure.force_login(self.owner)
        session = secure.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()
        self.assertEqual(secure.post(self.url(self.first, 'favorite/'), HTTP_X_SPACE_NAVIGATION='true').status_code, 403)
        target = self.url(self.first, '?view=board')
        response = self.client.post(self.url(self.first, 'favorite/'), {'next': target})
        self.assertRedirects(response, target, fetch_redirect_response=False)
        for target in ['https://example.com/', '//example.com/']:
            response = self.client.post(self.url(self.first, 'favorite/'), {'next': target})
            self.assertRedirects(response, self.url(), fetch_redirect_response=False)
