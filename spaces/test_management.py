from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from tasks.models import Task, TaskActivity, TaskProject, TaskProjectMembership, TaskSection
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.navigation import sidebar_favorite_is_active
from workplaces.services import scoped_workplace_app_path
from .services import manageable_spaces, manage_space


class SpaceManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(username='manage-owner', email='owner@example.test')
        cls.admin = User.objects.create_user(username='manage-admin', email='admin@example.test')
        cls.member = User.objects.create_user(username='manage-member', email='member@example.test')
        cls.other = User.objects.create_user(username='manage-other', email='other@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Zarządzanie')
        cls.foreign = create_workplace_for_user(cls.other, 'Obcy')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.admin, role='admin')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member, role='member')
        cls.private = TaskProject.objects.create(user=cls.owner, workplace=cls.workspace, name='Prywatny produkt', visibility='private', private_owner=cls.owner)
        TaskProjectMembership.objects.create(project=cls.private, user=cls.admin, role='admin')
        TaskProjectMembership.objects.create(project=cls.private, user=cls.member, role='member')
        cls.hidden = TaskProject.objects.create(user=cls.owner, workplace=cls.workspace, name='Poufny projekt', visibility='private', private_owner=cls.owner)
        cls.public = TaskProject.objects.create(user=cls.owner, workplace=cls.workspace, name='Publiczny produkt', visibility='public')
        cls.foreign_project = TaskProject.objects.create(user=cls.other, workplace=cls.foreign, name='Obcy projekt')

    def setUp(self):
        self.client.force_login(self.owner)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, suffix='manage/'):
        return scoped_workplace_app_path(self.workspace, 'spaces', suffix)

    def test_catalog_and_management_have_distinct_destinations(self):
        for url in ['/spaces/manage/', self.url()]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertTemplateUsed(response, 'spaces/manage.html')
            self.assertContains(response, 'Zarządzaj przestrzeniami')
            self.assertTrue(response.context['spaces_management_mode'])
            self.assertContains(response, 'data-sidebar-mode="administration"')
            self.assertContains(response, 'data-sidebar-navigation="workspace" hidden')
            self.assertNotContains(response, 'data-sidebar-navigation="administration" hidden')
            self.assertContains(response, 'data-sidebar-navigation="workplaces" hidden')
            menu = response.content.decode().split('data-sidebar-navigation="administration"', 1)[1].split('</nav>', 1)[0]
            self.assertNotIn('Workspace', menu)
            self.assertNotIn('Ustawienia Ancore', menu)
            self.assertNotContains(response, 'work-management-navigation')
            self.assertNotContains(response, 'Obcy projekt')
            self.assertFalse(sidebar_favorite_is_active('spaces', response.wsgi_request))
        daily = self.client.get(self.url(''))
        self.assertTemplateUsed(daily, 'spaces/index.html')
        self.assertFalse(daily.context['spaces_management_mode'])
        self.assertContains(daily, 'data-sidebar-mode="workspace"')
        self.assertContains(daily, 'data-sidebar-navigation="administration" hidden')
        self.assertNotContains(daily, 'data-sidebar-navigation="workspace" hidden')
        self.assertContains(daily, f'href="{self.url()}"')
        self.assertTrue(sidebar_favorite_is_active('spaces', daily.wsgi_request))
        self.assertContains(self.client.get('/settings/'), f'href="{self.url()}"')

    def test_management_respects_workspace_and_private_access(self):
        self.client.force_login(self.admin)
        response = self.client.get(self.url())
        self.assertContains(response, 'Prywatny produkt')
        self.assertContains(response, 'Publiczny produkt')
        self.assertNotContains(response, 'Poufny projekt')
        self.assertNotContains(response, 'Obcy projekt')
        TaskProjectMembership.objects.filter(project=self.private, user=self.admin).delete()
        self.assertNotContains(self.client.get(self.url()), 'Prywatny produkt')

    def test_members_and_observers_keep_daily_access_without_management(self):
        section = TaskSection.objects.create(project=self.public, title='Przypisane zadania')
        Task.objects.create(user=self.owner, workplace=self.workspace, section=section, title='Przydział bez zarządzania', assignee=self.member)
        self.client.force_login(self.member)
        for role in ['member', 'observer']:
            TaskProjectMembership.objects.filter(project=self.private, user=self.member).update(role=role)
            self.assertContains(self.client.get(self.url('')), 'Prywatny produkt')
            for suffix in ['manage/', 'manage/create/', f'manage/{self.private.space.pk}/edit/']:
                self.assertEqual(self.client.get(self.url(suffix)).status_code, 403)
            settings = self.client.get('/settings/')
            self.assertNotContains(settings, 'Ustawienia, konfiguracje i dostęp do przestrzeni')

    def test_project_admin_and_public_leader_manage_only_their_spaces(self):
        self.client.force_login(self.member)
        TaskProjectMembership.objects.filter(project=self.private, user=self.member).update(role='admin')
        response = self.client.get(self.url())
        self.assertEqual([space.project_id for space in response.context['page']], [self.private.pk])
        self.public.responsible_user = self.member
        self.public.save()
        response = self.client.get(self.url())
        self.assertEqual(set(manageable_spaces(response.wsgi_request).values_list('project_id', flat=True)), {self.private.pk, self.public.pk})
        self.assertTrue(all(manage_space(response.wsgi_request, space) for space in response.context['page']))

    def test_filters_and_pagination_apply_to_manageable_subset(self):
        self.client.force_login(self.admin)
        space = self.public.space
        space.kind = 'software'
        space.management = 'company'
        space.save()
        response = self.client.get(self.url(), {'q': space.key.lower(), 'kind': 'software', 'management': 'company'})
        self.assertEqual([space.project_id for space in response.context['page']], [self.public.pk])
        response = self.client.get(self.url(), {'q': space.key, 'management': 'team'})
        self.assertContains(response, 'Brak pasujących przestrzeni')
        for number in range(31):
            TaskProject.objects.create(user=self.owner, workplace=self.workspace, name=f'Filtrowany {number:02}')
        response = self.client.get(self.url(), {'q': 'Filtrowany', 'page': '2', 'kind': 'business'})
        self.assertEqual(response.context['page'].paginator.count, 31)
        self.assertEqual(len(response.context['page']), 1)
        self.assertContains(response, 'q=Filtrowany')
        self.assertContains(response, 'kind=business')

    def test_last_activity_does_not_reveal_hidden_tasks(self):
        section = TaskSection.objects.create(project=self.private, title='Zadania')
        visible = Task.objects.create(user=self.owner, workplace=self.workspace, section=section, title='Dostępne')
        hidden = Task.objects.create(user=self.owner, workplace=self.workspace, section=section, title='Ukryte', visibility='private', private_owner=self.member)
        visible_at = timezone.now() - timedelta(days=3)
        TaskActivity.objects.filter(task=visible).update(created_at=visible_at)
        TaskActivity.objects.filter(task=hidden).update(created_at=timezone.now())
        response = self.client.get(self.url(), {'q': self.private.space.key})
        row = response.context['page'][0]
        self.assertEqual(row.last_activity, visible_at)
        self.assertEqual(row.item_count, 1)

    def test_create_and_edit_return_to_management(self):
        create_url = self.url('manage/create/')
        response = self.client.get(create_url)
        self.assertTemplateUsed(response, 'spaces/manage.html')
        self.assertTrue(response.context['spaces_management_mode'])
        self.assertEqual(response.context['modal']['directory_url'], self.url())
        payload = {'name': 'Nowa przestrzeń', 'key': 'NOWA', 'kind': 'business', 'template': 'tasks', 'management': 'team', 'visibility': 'private'}
        invalid = self.client.post(create_url, {**payload, 'key': '!'})
        self.assertEqual(invalid.status_code, 400)
        self.assertTemplateUsed(invalid, 'spaces/manage.html')
        self.assertTrue(invalid.context['spaces_management_mode'])
        response = self.client.post(create_url, payload, HTTP_X_WORK_MODAL='true')
        self.assertEqual(response.json(), {'saved': True, 'url': self.url()})
        space = TaskProject.objects.get(name='Nowa przestrzeń').space
        response = self.client.post(self.url(f'manage/{space.pk}/edit/'), {**payload, 'name': 'Zmieniona przestrzeń'}, HTTP_X_WORK_MODAL='true')
        self.assertEqual(response.json(), {'saved': True, 'url': self.url()})
        self.assertContains(self.client.get(self.url()), 'Zmieniona przestrzeń')
        self.assertRedirects(self.client.post(self.url(f'{space.pk}/favorite/'), {'directory': 'manage'}), self.url())

    def test_management_edit_still_checks_each_space(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(self.url(f'manage/{self.hidden.space.pk}/edit/'), {}).status_code, 404)
        self.client.force_login(self.member)
        self.public.responsible_user = self.member
        self.public.save()
        self.assertEqual(self.client.post(self.url(f'manage/{self.private.space.pk}/edit/'), {}).status_code, 403)

    def test_empty_workspace_and_method_guards(self):
        empty = create_workplace_for_user(self.owner, 'Pusty')
        response = self.client.get(scoped_workplace_app_path(empty, 'spaces', 'manage/'))
        self.assertContains(response, 'Brak przestrzeni do zarządzania')
        self.assertEqual(self.client.post(self.url()).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.get(self.url()).status_code, 302)
