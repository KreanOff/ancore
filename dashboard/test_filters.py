from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from spaces.models import SpaceMembership, SpaceTask, Team
from spaces.services import visible_items
from spaces.testing import make_space
from tasks.models import TaskTag
from workplaces.models import SidebarFavorite, WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .filter_forms import BasicTaskSearchForm
from .filter_search import Compiler, QueryError, apply_query, basic_query, parse_query, quote
from .models import SavedTaskFilter
from .recent import RECENT_SESSION_KEY


class TaskFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(username='filters-owner', email='filters-owner@example.test')
        cls.member = User.objects.create_user(username='filters-member', email='filters-member@example.test')
        cls.other = User.objects.create_user(username='filters-other', email='filters-other@example.test')
        cls.workplace = create_workplace_for_user(cls.owner, 'Filtry')
        cls.foreign = create_workplace_for_user(cls.other, 'Inny')
        WorkplaceMembership.objects.create(workplace=cls.workplace, user=cls.member, role='member')
        cls.space = make_space(user=cls.owner, workplace=cls.workplace, name='Produkt', key='PRO')
        cls.private = make_space(user=cls.owner, workplace=cls.workplace, name='Tajna przestrzeń', key='SEC',
                                 visibility='private', private_owner=cls.owner)
        cls.foreign_space = make_space(user=cls.other, workplace=cls.foreign, name='Obca', key='OTH')
        cls.high = SpaceTask.objects.create(space=cls.space, title='Napraw logowanie', priority='high',
                                            assignee=cls.owner, created_by=cls.owner)
        cls.urgent = SpaceTask.objects.create(space=cls.space, title='Błąd płatności', priority='urgent',
                                              assignee=cls.member, created_by=cls.member)
        cls.free = SpaceTask.objects.create(space=cls.space, title='Dokumentacja', priority='low', created_by=cls.owner)
        cls.hidden = SpaceTask.objects.create(space=cls.private, title='Poufne zadanie', assignee=cls.member)
        cls.hidden_task = SpaceTask.objects.create(space=cls.space, title='Prywatne zadanie',
                                                  visibility='private', private_owner=cls.owner, assignee=cls.member)
        cls.child = SpaceTask.objects.create(space=cls.space, parent=cls.hidden_task, title='Poufne podzadanie')
        cls.foreign_task = SpaceTask.objects.create(space=cls.foreign_space, title='Obce zadanie')
        cls.tag1 = TaskTag.objects.create(user=cls.owner, workplace=cls.workplace, space=cls.space, name='Frontend')
        cls.tag2 = TaskTag.objects.create(user=cls.owner, workplace=cls.workplace, space=cls.space, name='Pilne')
        cls.high.tags.add(cls.tag1, cls.tag2)
        cls.team = Team.objects.create(owner=cls.owner, workplace=cls.workplace, name='Produkt')
        cls.saved = SavedTaskFilter.objects.create(owner=cls.owner, workplace=cls.workplace, created_by=cls.owner,
                                                  name='Moje otwarte', query='assignee = currentUser()')

    def setUp(self):
        self.login(self.owner)

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session['active_workplace_id'] = self.workplace.pk
        session['workspace_url_scope_enabled'] = False
        session.save()

    def url(self, suffix=''):
        return scoped_workplace_app_path(self.workplace, 'filters', suffix)

    def request(self, user=None):
        request = RequestFactory().get('/filters/search/')
        request.user = user or self.owner
        request.workplace = self.workplace
        return request

    def found(self, source, user=None):
        request = self.request(user)
        return list(apply_query(request, visible_items(request), source)[0].values_list('task_id', flat=True))

    def test_plain_and_scoped_pages_render_without_assignee(self):
        for url in ['/filters/', '/filters/search/', '/filters/new/', self.url(), self.url('search/'), self.url('new/')]:
            with self.subTest(url=url):
                response = self.client.get(url, follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, 'Filtry')
        self.assertContains(self.client.get(self.url('search/')), 'Nieprzypisane')

    def test_retired_all_items_redirects_to_search_preserving_criteria_and_acl(self):
        for task in (self.hidden, self.hidden_task):
            task.title = 'Poufny błąd płatności'
            task.save()
        old_urls = ['/spaces/items/', scoped_workplace_app_path(self.workplace, 'spaces', 'items/')]
        for user in (self.owner, self.member):
            for old_url in old_urls:
                with self.subTest(user=user.pk, url=old_url):
                    self.login(user)
                    self.assertRedirects(self.client.get(old_url), self.url('search/'))
                    response = self.client.get(old_url, {'q': ' płatności ', 'work_type': 'task',
                                                        'assignee': 'me', 'page': '1', 'jql': 'priority = low'}, follow=True)
                    target = urlsplit(response.redirect_chain[-1][0])
                    self.assertEqual(target.path, self.url('search/'))
                    self.assertEqual(parse_qs(target.query), {
                        'basic': ['1'], 'mode': ['basic'], 'sort': ['created_desc'],
                        'q': ['płatności'], 'type': ['task'], 'assignee': ['me'], 'page': ['1'],
                    })
                    page = response
                    self.assertEqual(page.status_code, 200)
                    self.assertEqual(page.context['search_error'], '')
                    self.assertEqual([item.task_id for item in page.context['items']],
                                     [self.urgent.pk] if user == self.member else [])
                    self.assertNotContains(page, 'Wszystkie zadania')
                    self.assertEqual(self.client.post(old_urls[1]).status_code, 405)

    def test_retired_all_items_favorite_is_hidden_and_cannot_be_added(self):
        favorite = SidebarFavorite.objects.create(user=self.owner, workplace=self.workplace, item_key='tasks-all')
        for url in (self.url('search/'), scoped_workplace_app_path(self.workplace, 'spaces')):
            response = self.client.get(url)
            self.assertNotContains(response, 'data-sidebar-source-item="tasks-all"')
            self.assertNotContains(response, 'data-sidebar-favorite-item="tasks-all"')
            self.assertNotContains(response, 'Wszystkie zadania')
            self.assertNotIn('tasks-all', [item['key'] for item in response.context['sidebar_favorites']])
        endpoint = reverse('workplaces:toggle-sidebar-favorite', args=[self.workplace.pk])
        self.assertEqual(self.client.post(endpoint, {'item_key': 'tasks-all', 'favorite_action': 'add'},
                                         HTTP_X_REQUESTED_WITH='XMLHttpRequest').status_code, 400)
        self.assertTrue(SidebarFavorite.objects.filter(pk=favorite.pk).exists())

    def test_global_navigation_uses_search_including_current_user_criteria(self):
        for user, expected in ((self.owner, self.high), (self.member, self.urgent)):
            self.login(user)
            payload = self.client.get(reverse('global_search'), {'q': 'zadania'}).json()
            navigation = next(group['results'] for group in payload['groups'] if group['key'] == 'navigation')
            rows = {row['title']: row for row in navigation}
            self.assertNotIn('Wszystkie zadania', rows)
            self.assertEqual(rows['Wyszukaj zadania']['url'], self.url('search/'))
            response = self.client.get(rows['Moje zadania']['url'])
            self.assertEqual(response.context['search_error'], '')
            self.assertEqual([item.task_id for item in response.context['items']], [expected.pk])

    def test_sidebar_recents_stars_and_navigation_recheck_scope(self):
        first = SavedTaskFilter.objects.create(owner=self.owner, workplace=self.workplace, created_by=self.owner,
                                               name='Pierwszy')
        second = SavedTaskFilter.objects.create(owner=self.owner, workplace=self.workplace, created_by=self.owner,
                                                name='Drugi')
        self.client.get(self.url(f'{first.pk}/'))
        response = self.client.get(self.url(f'{second.pk}/'))
        self.assertEqual([item.pk for item in response.context['navigation_recent_filters']][:2], [second.pk, first.pk])
        self.assertContains(response, 'data-sidebar-picker-toggle="filters"')
        self.assertContains(response, 'aria-label="Opcje filtrów"')
        response = self.client.post(self.url(f'{first.pk}/favorite/'), HTTP_X_FILTER_NAVIGATION='true')
        self.assertEqual(response.json(), {'saved': True})
        page = self.client.get(self.url())
        self.assertEqual([item.pk for item in page.context['navigation_starred_filters']], [first.pk])
        self.assertNotIn(first.pk, [item.pk for item in page.context['navigation_recent_filters']])
        self.login(self.member)
        session = self.client.session
        session[RECENT_SESSION_KEY] = [
            {'identity': [self.member.pk, self.workplace.pk, 'dashboard.savedtaskfilter', first.pk], 'at': ''},
        ]
        session.save()
        first.favorited_by.add(self.member)
        page = self.client.get(self.url())
        self.assertEqual(page.context['navigation_starred_filters'], [])
        self.assertEqual(page.context['navigation_recent_filters'], [])
        self.assertEqual(self.client.post(self.url(f'{first.pk}/favorite/'), HTTP_X_FILTER_NAVIGATION='true').status_code, 404)

    def test_sidebar_lookup_obeys_visibility_scope_limits_and_escaping(self):
        self.saved.visibility = 'selected'
        self.saved.name = '<img src=x onerror=alert(1)>'
        self.saved.save()
        self.saved.shared_with.add(self.member)
        self.login(self.member)
        response = self.client.get(self.url('lookup/'), {'q': '<img'})
        self.assertEqual(response['Cache-Control'], 'private, no-store')
        self.assertEqual(response.json()['count'], 1)
        self.assertIn('&lt;img', response.json()['html'])
        self.assertNotIn('<img src=x', response.json()['html'])
        self.saved.shared_with.clear()
        self.assertEqual(self.client.get(self.url('lookup/'), {'q': '<img'}).json()['count'], 0)
        self.login(self.owner)
        for number in range(22):
            SavedTaskFilter.objects.create(owner=self.owner, workplace=self.workplace, created_by=self.owner,
                                           name=f'Wyszukiwany {number}')
        SavedTaskFilter.objects.create(owner=self.other, workplace=self.foreign, created_by=self.other,
                                       name='Wyszukiwany obcy', visibility='workspace')
        found = self.client.get('/filters/lookup/', {'q': 'Wyszukiwany'}).json()
        self.assertEqual(found['count'], 20)
        self.assertIn('Więcej wyników', found['html'])
        self.assertNotIn('Wyszukiwany obcy', found['html'])
        self.assertEqual(self.client.get(self.url('lookup/')).json()['count'], 0)
        self.assertEqual(self.client.post(self.url('lookup/')).status_code, 405)

    def test_saved_visibility_and_workspace_are_separate_from_task_acl(self):
        self.saved.visibility = 'workspace'
        self.saved.query = ''
        self.saved.save()
        self.login(self.member)
        response = self.client.get(self.url(f'{self.saved.pk}/'))
        self.assertEqual({row.task_id for row in response.context['items']}, {self.high.pk, self.urgent.pk, self.free.pk})
        self.assertNotContains(response, 'Tajna przestrzeń')
        self.assertNotContains(response, 'Poufne zadanie')
        for query in ['space = SEC OR space = OTH', 'NOT space = PRO', 'text ~ "Poufne"']:
            self.assertEqual(self.found(query, self.member), [])
        self.assertEqual(self.client.get(scoped_workplace_app_path(self.foreign, 'filters', f'{self.saved.pk}/')).status_code, 302)

    def test_private_selected_and_revoked_filter_access(self):
        self.login(self.member)
        self.assertEqual(self.client.get(self.url(f'{self.saved.pk}/')).status_code, 404)
        self.saved.visibility = 'selected'
        self.saved.save()
        self.saved.shared_with.add(self.member)
        self.assertEqual(self.client.get(self.url(f'{self.saved.pk}/')).status_code, 200)
        self.client.post(self.url(f'{self.saved.pk}/favorite/'))
        self.saved.shared_with.clear()
        response = self.client.get(self.url('?tab=favorites'))
        self.assertNotContains(response, 'Moje otwarte')
        self.assertEqual(self.client.post(self.url(f'{self.saved.pk}/favorite/')).status_code, 404)

    def test_current_user_is_the_viewer_and_results_are_live(self):
        self.saved.visibility = 'workspace'
        self.saved.save()
        self.login(self.member)
        response = self.client.get(self.url(f'{self.saved.pk}/'))
        self.assertEqual([item.task_id for item in response.context['items']], [self.urgent.pk])
        created = SpaceTask.objects.create(space=self.space, title='Nowe dla mnie', assignee=self.member)
        response = self.client.get(self.url(f'{self.saved.pk}/'))
        self.assertEqual({item.task_id for item in response.context['items']}, {self.urgent.pk, created.pk})

    def test_member_can_create_own_filter_with_workspace_owner(self):
        self.login(self.member)
        response = self.client.post(self.url('new/'), {'name': 'Pilne', 'query': 'priority = urgent',
                                                      'visibility': 'private'}, HTTP_X_FILTER_MODAL='true')
        self.assertEqual(response.status_code, 200)
        item = SavedTaskFilter.objects.get(name='Pilne')
        self.assertEqual(item.owner, self.owner)
        self.assertEqual(item.created_by, self.member)
        self.assertEqual(item.workplace, self.workplace)
        self.assertTrue(item.favorited_by.filter(pk=self.member.pk).exists())
        self.assertEqual(response.json()['url'], self.url(f'{item.pk}/'))

    def test_edit_share_copy_save_delete_and_revisions(self):
        response = self.client.post(self.url(f'{self.saved.pk}/edit/'), {
            'name': 'Zespół', 'description': 'Wspólne', 'query': 'priority IN (high, urgent)',
            'visibility': 'selected', 'shared_with': [self.member.pk], 'revision': self.saved.revision,
        })
        self.assertEqual(response.status_code, 302)
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.revision, 1)
        self.assertEqual(list(self.saved.shared_with.all()), [self.member])
        self.assertEqual(self.client.post(self.url(f'{self.saved.pk}/save/'), {'jql': '', 'revision': 0}).status_code, 409)
        self.assertEqual(self.client.post(self.url(f'{self.saved.pk}/save/'), {'jql': 'status IS EMPTY', 'revision': 1}).status_code, 400)
        self.assertEqual(self.client.post(self.url(f'{self.saved.pk}/save/'), {'jql': '', 'revision': 1}).status_code, 302)
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.query, '')
        self.assertEqual(self.saved.revision, 2)
        response = self.client.post(self.url(f'{self.saved.pk}/edit/'), {
            'name': 'Nie nadpisuj', 'query': '', 'visibility': 'private', 'revision': 0,
        })
        self.assertEqual(response.status_code, 400)
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.name, 'Zespół')
        self.assertEqual(self.client.post(self.url('new/'), {'name': 'Kopia', 'query': '', 'visibility': 'private'}).status_code, 302)
        self.assertEqual(self.client.post(self.url(f'{self.saved.pk}/delete/')).status_code, 302)
        self.assertFalse(SavedTaskFilter.objects.filter(pk=self.saved.pk).exists())
        self.assertTrue(SavedTaskFilter.objects.filter(name='Kopia').exists())
        self.assertTrue(SpaceTask.objects.filter(pk=self.high.pk).exists())

    def test_recipients_names_query_and_csrf_are_validated(self):
        for data in [
            {'name': ' ', 'visibility': 'private'},
            {'name': 'Błąd', 'visibility': 'selected'},
            {'name': 'Błąd', 'visibility': 'selected', 'shared_with': [self.other.pk]},
            {'name': 'Błąd', 'visibility': 'private', 'query': 'task__space__user = 1'},
            {'name': 'Błąd', 'visibility': 'private', 'query': 'x' * 4001},
        ]:
            with self.subTest(data=data):
                self.assertEqual(self.client.post(self.url('new/'), data, HTTP_X_FILTER_MODAL='true').status_code, 400)
        protected = Client(enforce_csrf_checks=True)
        protected.force_login(self.owner)
        self.assertEqual(protected.post('/filters/new/', {'name': 'CSRF', 'visibility': 'private'}).status_code, 403)

    def test_only_creator_can_modify_even_workspace_owner(self):
        self.saved.visibility = 'workspace'
        self.saved.save()
        self.login(self.member)
        for suffix in ['edit/', 'save/', 'delete/']:
            with self.subTest(suffix=suffix):
                self.assertEqual(self.client.post(self.url(f'{self.saved.pk}/{suffix}'), {'jql': '', 'revision': 0}).status_code, 403)
        self.assertEqual(self.client.post(self.url(f'{self.saved.pk}/favorite/')).status_code, 302)
        self.assertTrue(self.saved.favorited_by.filter(pk=self.member.pk).exists())
        self.login(self.owner)
        self.assertFalse(self.saved.favorited_by.filter(pk=self.owner.pk).exists())

    def test_mutations_are_post_only_and_redirects_stay_local(self):
        for suffix in ['save/', 'delete/', 'favorite/']:
            self.assertEqual(self.client.get(self.url(f'{self.saved.pk}/{suffix}')).status_code, 405)
        response = self.client.post(self.url(f'{self.saved.pk}/favorite/'), {'return_to': 'https://evil.test/'})
        self.assertEqual(response.headers['Location'], self.url(f'{self.saved.pk}/'))
        response = self.client.post(self.url(f'{self.saved.pk}/favorite/'), {'return_to': 'http://['})
        self.assertEqual(response.headers['Location'], self.url(f'{self.saved.pk}/'))
        response = self.client.post(self.url(f'{self.saved.pk}/favorite/'), {'return_to': self.url('?tab=mine&q=moje')})
        self.assertEqual(response.headers['Location'], self.url('?tab=mine&q=moje'))

    def test_boolean_precedence_aliases_and_multivalue_filters(self):
        self.assertEqual(set(self.found('priority = high OR priority = urgent AND assignee = currentUser()')), {self.high.pk})
        self.assertEqual(set(self.found('(priority = high OR priority = urgent) AND NOT assignee = currentUser()')), {self.urgent.pk})
        self.assertEqual(self.found('project = PRO AND issuetype = task AND labels IN (Frontend, Pilne)'), [self.high.pk])
        self.assertEqual(self.found('tag = Frontend AND tag = Pilne'), [self.high.pk])
        self.assertEqual(self.found('summary ~ "płatności"'), [self.urgent.pk])
        self.assertEqual(self.found('priority = "Wysoki"'), [self.high.pk])
        self.assertEqual(set(self.found('assignee IS EMPTY', self.member)), {self.free.pk})
        self.assertEqual(self.found('tag != Frontend AND key = "' + self.high.work_item.key + '"'), [])

    def test_invalid_syntax_operators_and_limits_fail_closed(self):
        for source in ['priority > high', 'due ~ today', 'status = currentUser()', 'text = startOfDay()',
                       'status =', 'status = new AND', 'status IN ()', 'status NOT new', 'status = AND',
                       'ORDER BY task__title', 'text ~ "\\q"', '(' * 21 + 'status = new' + ')' * 21,
                       'due = "9999-12-31"', 'text ~ "' + 'x' * 4000 + '"']:
            with self.subTest(source=source[:80]):
                with self.assertRaises(QueryError):
                    Compiler(self.request()).expression(parse_query(source).expression)
        response = self.client.get(self.url('search/'), {'jql': 'status =', 'mode': 'advanced'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['items'], [])
        self.assertContains(response, 'Podaj wartość')
        self.assertFalse(response.context['can_save'])

    def test_date_day_bounds_relative_times_and_empty_values(self):
        day = timezone.make_aware(datetime(2026, 10, 10))
        self.high.due_at = day + timedelta(hours=23, minutes=59)
        self.high.save()
        self.urgent.due_at = day + timedelta(days=1)
        self.urgent.save()
        self.assertEqual(self.found('due = "2026-10-10"'), [self.high.pk])
        self.assertEqual(self.found('due > "2026-10-10"'), [self.urgent.pk])
        self.assertEqual(self.found('due <= "2026-10-10"'), [self.high.pk])
        self.assertEqual(self.found('due != "2026-10-10"'), [self.urgent.pk])
        self.assertEqual(set(self.found('due IS NOT EMPTY')), {self.high.pk, self.urgent.pk})
        query = parse_query('created >= -7d AND created <= startOfDay()')
        SpaceTask.objects.filter(pk=self.high.pk).update(created_at=day - timedelta(days=6))
        SpaceTask.objects.filter(pk=self.urgent.pk).update(created_at=day - timedelta(days=8))
        scope = visible_items(self.request()).filter(task_id__in=[self.high.pk, self.urgent.pk])
        self.assertEqual(list(scope.filter(Compiler(self.request(), now=day).expression(query.expression)).values_list('task_id', flat=True)), [self.high.pk])

    def test_priority_and_key_sort_are_semantic_and_stable(self):
        self.assertEqual(self.found('space = PRO ORDER BY priority DESC', self.member), [self.urgent.pk, self.high.pk, self.free.pk])
        for number in range(7):
            SpaceTask.objects.create(space=self.space, title=f'Kolejny {number}')
        items = self.found('space = PRO ORDER BY key ASC')
        self.assertEqual(items, list(self.space.items.order_by('number').values_list('task_id', flat=True)))

    def test_basic_controls_round_trip_and_preserve_complex_queries(self):
        source = basic_query({'space': [str(self.space.pk)], 'status': ['new'], 'assignee': ['me'],
                              'q': 'tekst "cytat" \\ znak', 'sort': 'priority_desc'})
        data = parse_query(source).basic()
        form = BasicTaskSearchForm(data, request=self.request())
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(basic_query(form.cleaned_data), source)
        mixed = basic_query({'assignee': ['me', 'unassigned'], 'sort': 'created_desc'})
        self.assertEqual(parse_query(mixed).basic()['assignee'], ['me', 'unassigned'])
        complex_query = 'priority = high OR assignee IS EMPTY'
        response = self.client.get(self.url('search/'), {'jql': complex_query, 'mode': 'basic'})
        self.assertEqual(response.context['mode'], 'advanced')
        self.assertEqual(response.context['jql'], complex_query)
        response = self.client.get(self.url('search/'), {'basic': '1', 'priority': ['high', 'urgent'],
                                                      'sort': 'priority_desc', 'mode': 'basic'})
        self.assertEqual([item.task_id for item in response.context['items']], [self.urgent.pk, self.high.pk])

    def test_clear_and_modal_close_preserve_saved_definition(self):
        response = self.client.get(self.url(f'{self.saved.pk}/'))
        cleared = self.client.get(response.context['clear_url'])
        self.assertEqual(cleared.context['jql'], '')
        self.assertTrue(cleared.context['changed'])
        self.saved.refresh_from_db()
        self.assertEqual(self.saved.query, 'assignee = currentUser()')
        modal = self.client.get(self.url('new/'), {'jql': 'priority = urgent', 'mode': 'advanced'})
        closed = self.client.get(modal.context['list_url'])
        self.assertEqual(closed.context['jql'], 'priority = urgent')
        self.assertEqual(closed.context['mode'], 'advanced')

    def test_pagination_preserves_query_and_escapes_names(self):
        for number in range(51):
            SpaceTask.objects.create(space=self.space, title=f'Strona {number}')
        source = 'text ~ Strona ORDER BY key ASC'
        first = self.client.get(self.url('search/'), {'jql': source, 'mode': 'advanced'})
        second = self.client.get(self.url('search/'), {'jql': source, 'mode': 'advanced', 'page': 2})
        self.assertEqual(first.context['page'].paginator.count, 51)
        self.assertEqual(len(first.context['items']), 50)
        self.assertEqual(len(second.context['items']), 1)
        self.assertContains(first, 'page=2')
        self.saved.name = '<script>alert(1)</script>'
        self.saved.favorited_by.add(self.owner)
        self.saved.save()
        response = self.client.get(self.url())
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert(1)</script>')
