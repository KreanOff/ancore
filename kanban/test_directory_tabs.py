from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from workplaces.models import WorkplaceMembership, create_workplace_for_user

from .models import KanbanProject, KanbanSection


class KanbanDirectoryTabsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='kanban-tabs-owner', email='owner@kanban-tabs.example.test')
        cls.member = get_user_model().objects.create_user(username='kanban-tabs-member', email='member@kanban-tabs.example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Zakładki Kanban')
        cls.other = create_workplace_for_user(cls.owner, 'Inny Workspace')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.project = KanbanProject.objects.create(user=cls.owner, workplace=cls.workspace, name='Marketing')
        cls.section = KanbanSection.objects.create(project=cls.project, title='Kampanie')
        cls.foreign = KanbanProject.objects.create(user=cls.owner, workplace=cls.other, name='Obca przestrzeń')
        cls.foreign_section = KanbanSection.objects.create(project=cls.foreign, title='Obca tablica')

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def bases(self):
        return ('/kanban/', f'/workplaces/{self.workspace.slug}/kanban/')

    def items(self, response, view):
        window, key = ('project_window', 'projects') if view == 'projects' else ('section_window', 'sections')
        return response.context[window][key]

    def test_categories_preserve_workspace_audience_on_both_routes(self):
        for base in self.bases():
            for view, expected in (('projects', self.project), ('all-groups', self.section)):
                for tab in ('private', 'shared', 'public', 'favorites', 'unknown'):
                    with self.subTest(base=base, view=view, tab=tab):
                        response = self.client.get(base, {'view': view, 'tab': tab}, follow=True)
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual([item.pk for item in self.items(response, view)],
                                         [expected.pk] if tab == 'public' else [])
                        self.assertEqual([item['label'] for item in response.context['directory_tabs']],
                                         ['Prywatne', 'Udostępnione', 'Publiczne', 'Ulubione'])
                        if tab in ('private', 'shared'):
                            self.assertContains(response, 'Brak prywatnych' if tab == 'private' else 'Brak udostępnionych')

    def test_plain_board_entry_and_tab_links_keep_boards(self):
        response = self.client.get('/kanban/')
        self.assertEqual(response.context['directory_tab'], 'private')
        for tab in response.context['directory_tabs']:
            result = self.client.get(tab['url'], follow=True)
            self.assertEqual(result.context['active_view'], 'all_groups')
            self.assertEqual(result.context['directory_tab'], tab['value'])
        result = self.client.get('/kanban/?tab=favorites', follow=True)
        self.assertEqual(result.context['active_view'], 'all_groups')

    def test_favorites_are_personal_idempotent_and_independent(self):
        for base in self.bases():
            for kind, item, view in (('project', self.project, 'projects'), ('section', self.section, 'all-groups')):
                url = f'{base}favorites/{kind}/{item.pk}/'
                for _ in range(2):
                    self.assertJSONEqual(self.client.post(url, {'favorite_action': 'add'}).content, {'is_favorite': True})
                self.assertEqual(list(item.favorited_by.all()), [self.member])
                response = self.client.get(base, {'view': view, 'tab': 'favorites'}, follow=True)
                self.assertEqual([obj.pk for obj in self.items(response, view)], [item.pk])
                self.assertTrue(self.items(response, view)[0].is_favorite)
                self.client.force_login(self.owner)
                response = self.client.get(f'/workplaces/{self.workspace.slug}/kanban/', {'view': view, 'tab': 'favorites'})
                self.assertEqual(self.items(response, view), [])
                self.client.force_login(self.member)
                for _ in range(2):
                    self.assertJSONEqual(self.client.post(url, {'favorite_action': 'remove'}).content, {'is_favorite': False})
                self.assertFalse(item.favorited_by.exists())

    def test_favorite_access_validation_and_csrf(self):
        for base in self.bases():
            for kind, item, foreign in (('project', self.project, self.foreign), ('section', self.section, self.foreign_section)):
                url = f'{base}favorites/{kind}/{item.pk}/'
                self.assertEqual(self.client.get(url, follow=True).status_code, 405)
                self.assertEqual(self.client.post(url, {'favorite_action': 'invalid'}).status_code, 400)
                self.assertEqual(self.client.post(f'{base}favorites/{kind}/{foreign.pk}/', {'favorite_action': 'add'}).status_code, 404)
                csrf_client = Client(enforce_csrf_checks=True)
                csrf_client.force_login(self.member)
                self.assertEqual(csrf_client.post(url, {'favorite_action': 'add'}).status_code, 403)
            self.assertEqual(self.client.post(f'{base}favorites/unknown/1/', {'favorite_action': 'add'}).status_code, 404)
        self.project.favorited_by.add(self.member)
        self.section.favorited_by.add(self.member)
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.member).delete()
        base = f'/workplaces/{self.workspace.slug}/kanban/'
        self.assertEqual(self.client.get(base, {'tab': 'favorites'}).status_code, 302)
        self.assertEqual(self.client.post(f'{base}favorites/project/{self.project.pk}/', {'favorite_action': 'add'}).status_code, 302)

    def test_filters_pagination_and_tab_links_preserve_category(self):
        for index in range(12):
            project = KanbanProject.objects.create(user=self.owner, workplace=self.workspace, name=f'Filtr {index:02d}')
            project.favorited_by.add(self.member)
            section = KanbanSection.objects.create(project=project, title=f'Filtr {index:02d}')
            section.favorited_by.add(self.member)
        for base in self.bases():
            for view, window, total in (('projects', 'project_window', 'total_projects'), ('all-groups', 'section_window', 'total_sections')):
                response = self.client.get(base, {'view': view, 'tab': 'favorites', 'q': 'Filtr', 'sort': 'name_desc', 'page_size': 10}, follow=True)
                self.assertEqual(response.context[window][total], 12)
                self.assertEqual(len(self.items(response, view)), 10)
                next_url = response.context[window]['next_url']
                self.assertEqual(parse_qs(urlsplit(next_url).query)['tab'], ['favorites'])
                second = self.client.get(next_url, follow=True)
                self.assertEqual(len(self.items(second, view)), 2)
                for tab in second.context['directory_tabs']:
                    params = parse_qs(urlsplit(tab['url']).query)
                    self.assertNotIn('page', params)
                    self.assertEqual(params['q'], ['Filtr'])
                    self.assertEqual(params['sort'], ['name_desc'])
                empty = self.client.get(base, {'view': view, 'tab': 'favorites', 'q': 'Brak wyniku'}, follow=True)
                self.assertContains(empty, 'Nie znaleziono')

    def test_detail_and_card_views_do_not_apply_directory_tabs(self):
        base = f'/workplaces/{self.workspace.slug}/kanban/'
        for suffix in (f'?project={self.project.pk}&tab=private', f'groups/{self.section.pk}/?tab=private', '?view=all-tasks&tab=private'):
            response = self.client.get(base + suffix)
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('directory_tabs', response.context)
