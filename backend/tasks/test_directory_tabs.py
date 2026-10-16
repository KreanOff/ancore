from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from workplaces.models import WorkplaceMembership, create_workplace_for_user

from .models import Task, TaskMembership, TaskProject, TaskProjectMembership, TaskSection


class DirectoryTabsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='tabs-owner', email='owner@tabs.example.test')
        cls.member = get_user_model().objects.create_user(username='tabs-member', email='member@tabs.example.test')
        cls.outsider = get_user_model().objects.create_user(username='tabs-outsider', email='outsider@tabs.example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Zakładki')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.other_workspace = create_workplace_for_user(cls.owner, 'Inny Workspace')

        def project(name, private_owner=None, workplace=None):
            return TaskProject.objects.create(
                user=cls.owner, workplace=workplace or cls.workspace, name=name,
                visibility='private' if private_owner else 'public', private_owner=private_owner,
            )

        cls.public = project('Publiczny')
        cls.own = project('Mój prywatny', cls.member)
        cls.own.shared_with.add(cls.owner)
        cls.received = project('Udostępniony mi', cls.owner)
        TaskProjectMembership.objects.create(project=cls.received, user=cls.member, role='observer')
        cls.hidden = project('Niedostępny', cls.owner)
        cls.foreign = project('Obcy Workspace', workplace=cls.other_workspace)
        cls.public_group = TaskSection.objects.create(project=cls.public, title='Publiczna')
        cls.own_group = TaskSection.objects.create(
            project=cls.public, title='Moja prywatna', visibility='private', private_owner=cls.member,
        )
        cls.own_group.shared_with.add(cls.owner)
        cls.inherited_own = TaskSection.objects.create(project=cls.own, title='Dziedziczy moją prywatność')
        cls.inherited_shared = TaskSection.objects.create(project=cls.received, title='Dziedziczy udostępnienie')
        cls.shared_group = TaskSection.objects.create(
            project=cls.public, title='Udostępniona grupa', visibility='private', private_owner=cls.owner,
        )
        cls.shared_group.shared_with.add(cls.member)
        cls.hidden_group = TaskSection.objects.create(
            project=cls.public, title='Ukryta grupa', visibility='private', private_owner=cls.owner,
        )
        cls.hidden_parent_group = TaskSection.objects.create(project=cls.hidden, title='Ukryty projekt')
        cls.foreign_group = TaskSection.objects.create(project=cls.foreign, title='Obca grupa')

        def task(name, section=None, private_owner=None, **kwargs):
            return Task.objects.create(
                user=cls.owner, workplace=section.project.workplace if section else cls.workspace,
                section=section, title=name, assignee=cls.member,
                visibility='private' if private_owner else 'public', private_owner=private_owner,
                **kwargs,
            )

        cls.public_task = task('Publiczne zadanie', cls.public_group)
        cls.orphan_task = task('Bez grupy')
        cls.own_task = task('Moje prywatne zadanie', cls.public_group, cls.member)
        cls.own_task.shared_with.add(cls.owner)
        cls.shared_task = task('Otrzymane zadanie', cls.public_group, cls.owner)
        TaskMembership.objects.create(task=cls.shared_task, user=cls.member, role='observer')
        cls.inherited_own_task = task('W moim projekcie', cls.inherited_own)
        cls.inherited_shared_task = task('W otrzymanym projekcie', cls.inherited_shared)
        cls.own_group_task = task('W mojej grupie', cls.own_group)
        cls.shared_group_task = task('W otrzymanej grupie', cls.shared_group)
        cls.own_in_shared_task = task('Własne w otrzymanym projekcie', cls.inherited_shared, cls.member)
        cls.hidden_task = task('Ukryte zadanie', cls.public_group, cls.owner)
        cls.hidden_group_task = task('Ukryte przez grupę', cls.hidden_group)
        cls.hidden_project_task = task('Ukryte przez projekt', cls.hidden_parent_group)
        cls.foreign_task = task('Zadanie z innego Workspace', cls.foreign_group)
        cls.child_task = task('Podzadanie poza katalogiem', cls.public_group, parent=cls.public_task)

    def setUp(self):
        self.client.force_login(self.member)
        self.url = f'/workplaces/{self.workspace.slug}/tasks/'

    def ids(self, response, kind):
        self.assertEqual(response.status_code, 200)
        return {item.pk for item in response.context['projects' if kind == 'project' else 'all_sections']}

    def favorite_url(self, kind, item, scoped=True):
        return f'{self.url if scoped else "/tasks/"}favorites/{kind}/{item.pk}/'

    def test_projects_partition_own_received_public_and_empty_favorites(self):
        expected = {'private': {self.own.pk}, 'shared': {self.received.pk},
                    'public': {self.public.pk}, 'favorites': set()}
        for tab, ids in expected.items():
            with self.subTest(tab=tab):
                response = self.client.get(self.url, {'tab': tab})
                self.assertEqual(self.ids(response, 'project'), ids)
                self.assertEqual(response.context['directory_tab'], tab)
                self.assertContains(response, f'data-directory-tabs="{tab}"')

    def test_groups_partition_uses_project_audience_and_group_restrictions(self):
        expected = {'private': {self.own_group.pk, self.inherited_own.pk},
                    'shared': {self.shared_group.pk, self.inherited_shared.pk},
                    'public': {self.public_group.pk}, 'favorites': set()}
        for tab, ids in expected.items():
            with self.subTest(tab=tab):
                response = self.client.get(self.url, {'view': 'all-groups', 'tab': tab})
                self.assertEqual(self.ids(response, 'section'), ids)

    def test_private_group_owner_takes_precedence_over_shared_project(self):
        group = TaskSection.objects.create(project=self.received, title='Własna w udostępnionym',
                                           visibility='private', private_owner=self.member)
        private = self.client.get(self.url, {'view': 'all-groups', 'tab': 'private'})
        shared = self.client.get(self.url, {'view': 'all-groups', 'tab': 'shared'})
        self.assertIn(group.pk, self.ids(private, 'section'))
        self.assertNotIn(group.pk, self.ids(shared, 'section'))

    def test_default_and_invalid_tab_are_private_on_regular_and_scoped_urls(self):
        self.client.get(self.url)
        for url in (self.url, '/tasks/'):
            for params in ({}, {'tab': 'unknown'}):
                with self.subTest(url=url, params=params):
                    response = self.client.get(url, params, follow=True)
                    self.assertEqual(self.ids(response, 'project'), {self.own.pk})
                    self.assertEqual(response.context['directory_tab'], 'private')

    def test_public_tabs_on_regular_urls(self):
        self.client.get(self.url)
        for kind, params, expected in (
            ('project', {'tab': 'public'}, {self.public.pk}),
            ('section', {'view': 'all-groups', 'tab': 'public'}, {self.public_group.pk}),
        ):
            response = self.client.get('/tasks/', params, follow=True)
            self.assertEqual(self.ids(response, kind), expected)

    def test_project_contents_do_not_apply_directory_tabs(self):
        response = self.client.get(self.url, {'project': self.public.pk, 'tab': 'favorites'})
        self.assertNotContains(response, 'data-directory-tabs=')
        self.assertEqual({group.pk for group in response.context['project_sections']},
                         {self.public_group.pk, self.own_group.pk, self.shared_group.pk})

    def test_pagination_search_sort_and_tab_links_keep_scope(self):
        for kind in ('project', 'section'):
            objects = []
            for index in range(12):
                name = f'Próba {index:02}'
                objects.append(TaskProject.objects.create(user=self.owner, workplace=self.workspace, name=name)
                               if kind == 'project' else TaskSection.objects.create(project=self.public, title=name))
            params = {'tab': 'public', 'q': 'Próba', 'page_size': 10,
                      'sort': 'name_desc' if kind == 'project' else 'title_desc'}
            if kind == 'section':
                params['view'] = 'all-groups'
            response = self.client.get(self.url, params)
            window_key = 'project_window' if kind == 'project' else 'group_window'
            window = response.context[window_key]
            self.assertEqual(self.ids(response, kind), {item.pk for item in objects[2:]})
            next_url = window['next_url']
            self.assertEqual(urlsplit(next_url).path, self.url)
            self.assertEqual(parse_qs(urlsplit(next_url).query),
                             {**{key: [str(value)] for key, value in params.items()}, 'page': ['2']})
            response = self.client.get(next_url)
            self.assertEqual(self.ids(response, kind), {item.pk for item in objects[:2]})
            for tab in response.context['directory_tabs']:
                values = parse_qs(urlsplit(tab['url']).query)
                self.assertNotIn('page', values)
                self.assertEqual(values['q'], ['Próba'])
                self.assertEqual(values['tab'], [tab['value']])

    def test_personal_favorites_allow_observers_and_are_idempotent(self):
        for kind, item in (('project', self.received), ('section', self.inherited_shared)):
            url = self.favorite_url(kind, item)
            for _ in range(2):
                self.assertEqual(self.client.post(url, {'favorite_action': 'add'}).json(), {'is_favorite': True})
            self.assertEqual(list(item.favorited_by.all()), [self.member])
            params = {'tab': 'favorites', **({'view': 'all-groups'} if kind == 'section' else {})}
            response = self.client.get(self.url, params)
            self.assertEqual(self.ids(response, kind), {item.pk})
            self.assertContains(response, 'Usuń z ulubionych')
            self.client.force_login(self.owner)
            self.assertEqual(self.ids(self.client.get(self.url, params), kind), set())
            self.client.force_login(self.member)
            for _ in range(2):
                self.assertEqual(self.client.post(url, {'favorite_action': 'remove'}).json(), {'is_favorite': False})
            self.assertFalse(item.favorited_by.exists())

    def test_favorites_do_not_grant_access_and_honor_revocation(self):
        self.received.favorited_by.add(self.member)
        self.inherited_shared.favorited_by.add(self.member)
        self.received.shared_with.remove(self.member)
        for kind, item in (('project', self.received), ('section', self.inherited_shared)):
            params = {'tab': 'favorites', **({'view': 'all-groups'} if kind == 'section' else {})}
            self.assertEqual(self.ids(self.client.get(self.url, params), kind), set())
            self.assertEqual(self.client.post(self.favorite_url(kind, item), {'favorite_action': 'add'}).status_code, 404)

    def test_favorite_endpoint_rejects_hidden_and_foreign_objects_and_invalid_requests(self):
        for kind, item in (('project', self.hidden), ('project', self.foreign),
                           ('section', self.hidden_group), ('section', self.hidden_parent_group),
                           ('section', self.foreign_group)):
            self.assertEqual(self.client.post(self.favorite_url(kind, item), {'favorite_action': 'add'}).status_code, 404)
            self.assertFalse(item.favorited_by.exists())
        url = self.favorite_url('project', self.public)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url, {'favorite_action': 'toggle'}).status_code, 400)
        self.assertEqual(self.client.post(self.favorite_url('unsupported', self.public), {'favorite_action': 'add'}).status_code, 404)
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.post(url, {'favorite_action': 'add'}).status_code, 302)
        self.assertFalse(self.public.favorited_by.exists())

    def test_regular_favorite_url_and_csrf(self):
        self.client.get(self.url)
        response = self.client.post(self.favorite_url('project', self.public, scoped=False), {'favorite_action': 'add'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.public.favorited_by.filter(pk=self.member.pk).exists())
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.member)
        client.get(self.url)
        url = self.favorite_url('section', self.public_group)
        self.assertEqual(client.post(url, {'favorite_action': 'add'}).status_code, 403)
        response = client.post(url, {'favorite_action': 'add'}, HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value)
        self.assertEqual(response.status_code, 200)

    def test_empty_favorites_and_filtered_state_explain_next_action(self):
        response = self.client.get(self.url, {'tab': 'favorites'})
        self.assertContains(response, 'Brak ulubionych projektów.')
        self.assertContains(response, 'Dodaj do ulubionych')
        response = self.client.get(self.url, {'view': 'all-groups', 'tab': 'shared', 'q': 'nie istnieje'})
        self.assertContains(response, 'Nie znaleziono grup.')
        self.assertContains(response, 'inne wyniki w tej zakładce')

    def task_ids(self, response):
        self.assertEqual(response.status_code, 200)
        return {task.pk for task in response.context['task_window']['queryset']}

    def test_unassigned_directory_shows_only_visible_roots_without_a_group(self):
        visible = {self.own_task.pk, self.shared_task.pk, self.public_task.pk, self.orphan_task.pk}
        Task.objects.filter(pk__in=visible | {self.hidden_task.pk, self.foreign_task.pk, self.child_task.pk}).update(section=None)
        self.client.get(self.url)
        for url in (self.url, '/tasks/'):
            response = self.client.get(url, {'view': 'unassigned-tasks', 'tab': 'favorites',
                                             'task_project': self.public.pk, 'task_section': self.public_group.pk}, follow=True)
            self.assertEqual(self.task_ids(response), visible)
            self.assertEqual(response.context['active_view'], 'unassigned_tasks')
            self.assertContains(response, 'data-directory-tabs="unassigned"')
            self.assertContains(response, 'aria-current="page">Nieprzydzielone</a>')
            self.assertContains(response, 'data-project-filter-menu="task_assignee"')
            self.assertNotContains(response, 'data-project-filter-menu="task_project"')
            self.assertNotContains(response, 'data-project-filter-menu="task_section"')
            self.assertContains(response, '<span>Zadania</span>')
            self.assertNotContains(response, 'data-sidebar-source-item="tasks-my"')
        response = self.client.get(self.url, {'view': 'unassigned-tasks', 'task_assignee': self.owner.pk})
        self.assertEqual(self.task_ids(response), set())
        self.shared_task.section = self.public_group
        self.shared_task.save(update_fields=['section'])
        response = self.client.get(self.url, {'view': 'unassigned-tasks'})
        self.assertNotIn(self.shared_task.pk, self.task_ids(response))

    def test_unassigned_empty_state_and_saved_sidebar_shortcut(self):
        from workplaces.navigation import sidebar_favorite_catalog, sidebar_favorite_is_active

        self.orphan_task.section = self.public_group
        self.orphan_task.save(update_fields=['section'])
        response = self.client.get(self.url, {'view': 'unassigned-tasks'})
        self.assertContains(response, 'Brak zadań nieprzydzielonych.')
        self.assertContains(response, 'Tutaj pojawią się zadania bez projektu i grupy.')
        item = sidebar_favorite_catalog(self.workspace)['tasks-my']
        self.assertEqual(item['label'], 'Zadania nieprzydzielone')
        self.assertEqual(item['url'], self.url + '?view=unassigned-tasks')
        self.assertTrue(sidebar_favorite_is_active('tasks-my', response.wsgi_request, 'unassigned_tasks'))
        self.assertTrue(sidebar_favorite_is_active('tasks-all', response.wsgi_request, 'unassigned_tasks'))

    def test_unassigned_tab_navigation_preserves_filters_and_resets_page(self):
        response = self.client.get(self.url, {
            'view': 'all-tasks', 'tab': 'public', 'page': 2, 'page_size': 25,
            'q': 'Bez grupy', 'sort': 'title_desc', 'task_assignee': self.member.pk,
            'task_project': self.public.pk, 'task_section': self.public_group.pk,
        })
        tab = response.context['directory_tabs'][-1]
        self.assertEqual(tab['label'], 'Nieprzydzielone')
        params = parse_qs(urlsplit(tab['url']).query)
        self.assertEqual(params, {
            'view': ['unassigned-tasks'], 'page_size': ['25'], 'q': ['Bez grupy'],
            'sort': ['title_desc'], 'task_assignee': [str(self.member.pk)],
        })
        response = self.client.get(tab['url'])
        self.assertEqual(self.task_ids(response), {self.orphan_task.pk})
        self.assertTrue(response.context['directory_tabs'][-1]['active'])
        for tab in response.context['directory_tabs'][:-1]:
            params = parse_qs(urlsplit(tab['url']).query)
            self.assertEqual(params['view'], ['all-tasks'])
            self.assertEqual(params['tab'], [tab['value']])
            self.assertEqual(params['q'], ['Bez grupy'])
        for params in ({}, {'view': 'all-groups'}):
            response = self.client.get(self.url, params)
            self.assertNotIn('unassigned', [tab['value'] for tab in response.context['directory_tabs']])

    def test_tasks_partition_respects_inherited_access_and_excludes_children(self):
        expected = {
            'private': {self.own_task.pk, self.inherited_own_task.pk, self.own_group_task.pk, self.own_in_shared_task.pk},
            'shared': {self.shared_task.pk, self.inherited_shared_task.pk, self.shared_group_task.pk},
            'public': {self.public_task.pk, self.orphan_task.pk},
            'favorites': set(),
        }
        self.client.get(self.url)
        for url in (self.url, '/tasks/'):
            for tab, ids in expected.items():
                with self.subTest(url=url, tab=tab):
                    response = self.client.get(url, {'view': 'all-tasks', 'tab': tab}, follow=True)
                    self.assertEqual(self.task_ids(response), ids)
                    self.assertEqual(response.context['total_task_count'], len(ids))
                    self.assertContains(response, 'aria-label="Widok zadań"')

    def test_task_default_tab_is_private_and_other_task_views_keep_their_scope(self):
        for tab in (None, 'invalid'):
            params = {'view': 'all-tasks', **({'tab': tab} if tab else {})}
            response = self.client.get(self.url, params)
            self.assertEqual(response.context['directory_tab'], 'private')
            self.assertIn(self.own_task.pk, self.task_ids(response))
            self.assertNotIn(self.public_task.pk, self.task_ids(response))
        response = self.client.get(self.url, {'view': 'my-tasks', 'tab': 'favorites'})
        self.assertNotContains(response, 'data-directory-tabs=')
        self.assertTrue({self.own_task.pk, self.shared_task.pk, self.public_task.pk} <= self.task_ids(response))
        response = self.client.get(f'{self.url}groups/{self.public_group.pk}/', {'tab': 'favorites'})
        self.assertNotContains(response, 'data-directory-tabs=')
        self.assertContains(response, f'data-task-pk="{self.public_task.pk}"')

    def test_task_favorites_are_personal_persistent_and_available_to_observers(self):
        for task in (self.shared_task, self.inherited_shared_task, self.own_task, self.public_task):
            for _ in range(2):
                response = self.client.post(self.favorite_url('task', task), {'favorite_action': 'add'})
                self.assertEqual(response.json(), {'is_favorite': True})
            self.assertEqual(list(task.favorited_by.all()), [self.member])
        params = {'view': 'all-tasks', 'tab': 'favorites'}
        response = self.client.get(self.url, params)
        self.assertEqual(self.task_ids(response), {
            self.shared_task.pk, self.inherited_shared_task.pk, self.own_task.pk, self.public_task.pk,
        })
        self.assertContains(response, 'data-favorite-action="remove"', count=4)
        self.client.force_login(self.owner)
        self.assertEqual(self.task_ids(self.client.get(self.url, params)), set())
        self.client.force_login(self.member)
        for _ in range(2):
            self.assertEqual(self.client.post(self.favorite_url('task', self.shared_task),
                                             {'favorite_action': 'remove'}).json(), {'is_favorite': False})
        self.assertNotIn(self.shared_task.pk, self.task_ids(self.client.get(self.url, params)))

    def test_task_favorites_never_bypass_revoked_or_hidden_access(self):
        for task in (self.shared_task, self.inherited_shared_task, self.shared_group_task):
            task.favorited_by.add(self.member)
        self.shared_task.shared_with.remove(self.member)
        self.received.shared_with.remove(self.member)
        self.shared_group.shared_with.remove(self.member)
        response = self.client.get(self.url, {'view': 'all-tasks', 'tab': 'favorites'})
        self.assertEqual(self.task_ids(response), set())
        for task in (self.shared_task, self.inherited_shared_task, self.shared_group_task,
                     self.hidden_task, self.hidden_group_task, self.hidden_project_task,
                     self.foreign_task, self.child_task):
            self.assertEqual(self.client.post(self.favorite_url('task', task), {'favorite_action': 'add'}).status_code, 404)

    def test_task_favorite_endpoint_validates_actions_scope_and_csrf(self):
        self.client.get(self.url)
        url = self.favorite_url('task', self.public_task, scoped=False)
        self.assertEqual(self.client.get(url, follow=True).status_code, 405)
        self.assertEqual(self.client.post(url, {'favorite_action': 'toggle'}).status_code, 400)
        self.assertEqual(self.client.post(url, {'favorite_action': 'add'}).json(), {'is_favorite': True})
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.member)
        client.get(self.url)
        self.assertEqual(client.post(url, {'favorite_action': 'remove'}).status_code, 403)
        self.assertEqual(client.post(url, {'favorite_action': 'remove'},
                                    HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value).status_code, 200)
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.post(self.favorite_url('task', self.public_task),
                                         {'favorite_action': 'add'}).status_code, 302)
        self.assertFalse(self.public_task.favorited_by.exists())

    def test_task_tabs_preserve_search_sort_filters_and_paginate_each_status(self):
        for status, _ in Task.STATUS_CHOICES[:2]:
            for index in range(12):
                Task.objects.create(user=self.owner, workplace=self.workspace, section=self.public_group,
                                    title=f'Próba {status} {index:02}', priority='high', status=status)
        params = {'view': 'all-tasks', 'tab': 'public', 'q': 'Próba', 'priority': 'high',
                  'task_project': self.public.pk, 'sort': 'title_desc', 'page_size': 10}
        response = self.client.get(self.url, params)
        self.assertEqual(response.context['total_task_count'], 24)
        self.assertEqual([group['count'] for group in response.context['all_status_groups']][:2], [10, 10])
        self.assertTrue(all(task.title[-2:] >= '02' for task in response.context['task_window']['queryset']))
        next_url = response.context['task_window']['next_url']
        self.assertEqual(urlsplit(next_url).path, self.url)
        self.assertEqual(parse_qs(urlsplit(next_url).query),
                         {**{key: [str(value)] for key, value in params.items()}, 'page': ['2']})
        response = self.client.get(next_url)
        self.assertEqual(len(self.task_ids(response)), 4)
        for tab in response.context['directory_tabs']:
            values = parse_qs(urlsplit(tab['url']).query)
            self.assertNotIn('page', values)
            self.assertEqual(values['q'], ['Próba'])
            self.assertEqual(values['view'], ['unassigned-tasks' if tab['value'] == 'unassigned' else 'all-tasks'])
        response = self.client.get(self.url, {**params, 'tab': 'favorites'})
        self.assertContains(response, 'Nie znaleziono zadań.')
        response = self.client.get(self.url, {'view': 'all-tasks', 'tab': 'favorites'})
        self.assertContains(response, 'Brak ulubionych zadań.')
        self.assertContains(response, 'Oznacz zadanie gwiazdką')
