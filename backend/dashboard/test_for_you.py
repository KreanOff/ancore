from datetime import timedelta
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from tasks.models import TaskTag
from spaces.models import SpaceTask, SpaceTaskActivity, SpaceTaskFile, Space, WorkItem
from spaces.testing import make_space
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import ACTIVE_WORKPLACE_SESSION_KEY, scoped_workplace_app_path

from .recent import RECENT_SESSION_KEY


class ForYouTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='fy-owner', email='owner@fy.example.test')
        cls.member = get_user_model().objects.create_user(username='fy-member', email='member@fy.example.test')
        cls.outsider = get_user_model().objects.create_user(username='fy-outsider', email='outsider@fy.example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Dla ciebie')
        cls.other_workspace = create_workplace_for_user(cls.owner, 'Drugi Workspace')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.project = make_space(user=cls.owner, workplace=cls.workspace, name='Projekt zespołu')
        cls.section = make_space(user=cls.project.user, workplace=cls.project.workplace, name='Grupa zespołu')
        cls.hidden_project = make_space(
            user=cls.owner, workplace=cls.workspace, name='Ukryty projekt', visibility='private', private_owner=cls.owner,
        )
        cls.hidden_section = cls.hidden_project
        cls.url = scoped_workplace_app_path(cls.workspace, 'for-you')

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session[ACTIVE_WORKPLACE_SESSION_KEY] = self.workspace.pk
        session.save()

    def task(self, title='Moje zadanie', **kwargs):
        owner = kwargs.pop('user', self.owner)
        workplace = kwargs.pop('workplace', self.workspace)
        selected = kwargs.pop('section', self.project)
        if kwargs.get('parent'):
            selected = kwargs['parent'].space
        if selected is None or selected.user_id != owner.pk or selected.workplace_id != workplace.pk:
            selected = make_space(user=owner, workplace=workplace, name='Inny zakres')
        kwargs.setdefault('assignee', self.member)
        return SpaceTask.objects.create(title=title, space=selected, created_by=owner, **kwargs)

    def page(self, tab='assigned', **params):
        response = self.client.get(self.url, {'tab': tab, **params})
        self.assertEqual(response.status_code, 200)
        return response

    def objects(self, response):
        return [row['object'] for row in response.context['for_you_rows']]

    def visit(self, obj):
        url = scoped_workplace_app_path(self.workspace, 'space', f'{obj.space.slug}/tasks/{obj.work_item.key}/')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_authentication_base_scoped_context_search_and_cache(self):
        response = self.client.get(reverse('for_you'))
        self.assertContains(response, 'Dla ciebie | ancore')
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(self.page('unknown').context['for_you_tab'], 'recommended')
        result = self.client.get(reverse('global_search'), {'q': 'dla ciebie'}).json()
        self.assertTrue(any(item['url'] == self.url for group in result['groups'] for item in group['results']))
        self.client.logout()
        for url in [self.url, reverse('for_you')]:
            self.assertIn(reverse('login'), self.client.get(url).url)

    def test_assigned_uses_actual_viewer_includes_subtasks_excludes_closed(self):
        mine = self.task()
        child = self.task('Podzadanie', parent=mine)
        self.task('Właściciela', assignee=self.owner)
        self.task('Nieprzypisane', assignee=None)
        self.task('Zamknięte', status='closed')
        self.assertEqual(set(self.objects(self.page())), {mine, child})

    def test_assignment_favorites_and_activity_never_grant_access(self):
        visible = self.task()
        hidden_parent = self.task('Ukryty rodzic', visibility='private', private_owner=self.owner)
        hidden_group = make_space(user=self.project.user, workplace=self.project.workplace, name='Prywatna grupa', visibility='private', private_owner=self.owner)
        hidden = [self.task('Inny Workspace', workplace=self.other_workspace, section=None),
                  self.task('Obcy właściciel', user=self.outsider, section=None),
                  self.task('Prywatny projekt', section=self.hidden_section),
                  self.task('Prywatna grupa', section=hidden_group),
                  hidden_parent, self.task('Ukryty potomek', parent=hidden_parent)]
        for task in [visible, *hidden]:
            task.favorited_by.add(self.member)
            SpaceTaskActivity.objects.create(task=task, actor=self.member)
        for tab in ('assigned', 'starred', 'worked'):
            with self.subTest(tab=tab):
                self.assertEqual(self.objects(self.page(tab)), [visible])
        self.hidden_project.favorited_by.add(self.member)
        self.assertNotContains(self.page(), 'Ukryty projekt')

    def test_recommendations_use_real_dates_priority_and_viewer(self):
        now = timezone.now()
        overdue = self.task('Zaległe', due_at=now - timedelta(days=1))
        soon = self.task('Wkrótce', due_at=now + timedelta(days=6))
        urgent = self.task('Pilne', priority='urgent')
        self.task('Za tydzień', due_at=now + timedelta(days=8))
        self.task('Zamknięte pilne', status='closed', priority='urgent')
        self.task('Czyjeś pilne', assignee=self.owner, priority='urgent')
        self.assertEqual(self.objects(self.page('recommended')), [urgent, soon, overdue])
        self.assertContains(self.page('recommended'), 'Po terminie')

    def test_worked_uses_personal_activity(self):
        task = self.task()
        someone_elses = self.task('Czyjaś praca')
        SpaceTaskActivity.objects.create(task=someone_elses, actor=self.owner)
        SpaceTaskActivity.objects.create(task=task, actor=self.member)
        SpaceTaskActivity.objects.create(task=task, actor=self.member, kind='comment')
        SpaceTaskActivity.objects.create(task=task, actor=self.owner)
        self.assertEqual(self.objects(self.page('worked')), [task])

    def test_starred_is_personal_and_includes_existing_favorite_kinds(self):
        task = self.task()
        other = self.task('Cudze ulubione')
        other.favorited_by.add(self.owner)
        favorites = [task, self.project, self.section]
        for obj in favorites:
            obj.favorited_by.add(self.member)
        self.assertEqual(set(self.objects(self.page('starred'))), set([task, self.project, self.section]))
        self.assertEqual({row['object'] for row in self.page().context['for_you_projects']}, {self.project, self.section})

    def test_viewed_records_successful_views_deduplicates_and_rechecks_access(self):
        task = self.task()
        self.visit(task)
        self.visit(task)
        self.assertEqual(self.objects(self.page('viewed')), [task])
        self.assertEqual(len(self.client.session[RECENT_SESSION_KEY]), 1)
        task.visibility, task.private_owner = 'private', self.owner
        task.save()
        self.assertEqual(self.objects(self.page('viewed')), [])
        self.assertEqual(self.objects(self.page('viewed')), [])

    def test_viewed_projects_groups_and_session_user_scope(self):
        self.client.get(scoped_workplace_app_path(self.workspace, 'space', f'{self.project.slug}/'))
        self.client.get(scoped_workplace_app_path(self.workspace, 'space', f'{self.section.slug}/'))
        self.assertEqual(self.objects(self.page('viewed')), [self.section, self.project])
        session = self.client.session
        entries = session[RECENT_SESSION_KEY]
        for entry in entries:
            entry['identity'][0] = self.owner.pk
        session[RECENT_SESSION_KEY] = entries
        session.save()
        self.assertEqual(self.objects(self.page('viewed')), [])

    def test_viewed_only_includes_last_seven_days_for_all_kinds_and_urls(self):
        now = timezone.localtime().replace(hour=12, minute=0, second=0, microsecond=0)
        current = self.task('Oglądane dzisiaj')
        boundary = self.task('Dokładnie tydzień temu')
        expired = self.task('Starsze niż tydzień')
        future = self.task('Przyszły wpis')
        old_project = make_space(user=self.owner, workplace=self.workspace, name='Dawna przestrzeń')
        old_section = make_space(user=self.project.user, workplace=self.project.workplace, name='Dawna grupa')
        entries = [(current, now), (self.section, now - timedelta(days=1)),
                   (self.project, now - timedelta(days=3)), (boundary, now - timedelta(days=7)),
                   (expired, now - timedelta(days=7, microseconds=1)),
                   (old_project, now - timedelta(days=8)), (old_section, now - timedelta(days=10)),
                   (future, now + timedelta(seconds=1))]
        session = self.client.session
        session[RECENT_SESSION_KEY] = [
            {'identity': [self.member.pk, self.workspace.pk, obj._meta.label_lower, obj.pk], 'at': at.isoformat()}
            for obj, at in entries
        ]
        session.save()
        for url in (self.url, reverse('for_you')):
            with self.subTest(url=url), patch('dashboard.for_you.timezone.now', return_value=now):
                response = self.client.get(url, {'tab': 'viewed'}, follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.objects(response), [current, self.section, self.project, boundary])
                self.assertEqual(response.context['for_you_page'].paginator.count, 4)
                self.assertEqual([row['date_group'] for row in response.context['for_you_rows']],
                                 ['Dzisiaj', 'Wczoraj', 'Ostatnie 7 dni', 'Ostatnie 7 dni'])
        self.assertEqual(len(self.client.session[RECENT_SESSION_KEY]), len(entries))

    def test_viewed_week_limit_applies_before_pagination(self):
        now = timezone.now()
        tasks = [self.task(f'Oglądane {index:02d}') for index in range(30)]
        session = self.client.session
        session[RECENT_SESSION_KEY] = [
            {'identity': [self.member.pk, self.workspace.pk, task._meta.label_lower, task.pk],
             'at': (now - timedelta(minutes=index) if index < 27 else now - timedelta(days=8)).isoformat()}
            for index, task in enumerate(tasks)
        ]
        session.save()
        with patch('dashboard.for_you.timezone.now', return_value=now):
            first, second = self.page('viewed'), self.page('viewed', page=2)
            self.assertEqual(first.context['for_you_page'].paginator.count, 27)
            self.assertEqual(self.objects(first), tasks[:20])
            self.assertEqual(self.objects(second), tasks[:27])
            self.assertEqual(self.objects(self.page('viewed', page=99999)), tasks[:27])

    def test_viewed_expired_entry_returns_after_opening_again(self):
        task = self.task()
        activity = SpaceTaskActivity.objects.create(task=task, actor=self.member)
        old = timezone.now() - timedelta(days=8)
        SpaceTaskActivity.objects.filter(pk=activity.pk).update(created_at=old)
        session = self.client.session
        session[RECENT_SESSION_KEY] = [
            {'identity': [self.member.pk, self.workspace.pk, task._meta.label_lower, task.pk], 'at': old.isoformat()}
        ]
        session.save()
        response = self.page('viewed')
        self.assertEqual(self.objects(response), [])
        self.assertContains(response, 'w ostatnich 7 dniach')
        self.assertEqual(self.objects(self.page('worked')), [task])
        self.assertEqual(self.page('worked').context['for_you_groups'][0]['date_group'], 'Wcześniej')
        self.visit(task)
        self.assertEqual(self.objects(self.page('viewed')), [task])
        self.assertEqual(len(self.client.session[RECENT_SESSION_KEY]), 1)

    def test_links_keep_primary_key_after_number_changes(self):
        before = self.task('Do usunięcia')
        wanted = self.task('Otwórz to')
        self.visit(wanted)
        row = self.page('viewed').context['for_you_rows'][0]
        before.delete()
        response = self.client.get(row['url'])
        self.assertEqual(response.context['task'].pk, wanted.pk)

    def test_workspace_switch_and_membership_revocation(self):
        self.task()
        response = self.client.get(scoped_workplace_app_path(self.other_workspace, 'for-you'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('workplaces:workplaces'))
        WorkplaceMembership.objects.filter(workplace=self.workspace, user=self.member).delete()
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_four_tabs_show_twenty_latest_items_without_pagination(self):
        now = timezone.now()
        tasks = [self.task(f'Zadanie {i:02d}', priority='high', due_at=now + timedelta(days=29 - i))
                 for i in range(29)]
        for i, task in enumerate(tasks):
            task.created_at = now - timedelta(minutes=i)
            SpaceTask.objects.filter(pk=task.pk).update(created_at=task.created_at)
            task.favorited_by.add(self.member)
            SpaceTaskActivity.objects.create(task=task, actor=self.member)
            SpaceTaskActivity.objects.filter(task=task, actor=self.member).update(created_at=now - timedelta(minutes=29 - i))
        Space.objects.filter(pk=self.project.pk).update(created_at=now - timedelta(seconds=90))
        Space.objects.filter(pk=self.section.pk).update(created_at=now - timedelta(seconds=150))
        self.project.favorited_by.add(self.member)
        self.section.favorited_by.add(self.member)
        favorites = [tasks[0], tasks[1], self.project, tasks[2], self.section, *tasks[3:18]]
        for tab, expected in [('recommended', tasks[:20]), ('assigned', tasks[:20]),
                              ('starred', favorites), ('worked', list(reversed(tasks[-20:])))]:
            with self.subTest(tab=tab):
                response = self.page(tab)
                self.assertEqual(self.objects(response), expected)
                self.assertIsNone(response.context['for_you_page'])
                self.assertEqual(response.context['for_you_assigned_count'], 29)
                self.assertEqual(response.context['for_you_next'], '')
                self.assertEqual(response.context['for_you_previous'], '')
                self.assertNotContains(response, 'for-you-pagination')
                for page in (2, 'bad', 99999):
                    self.assertEqual(self.objects(self.page(tab, page=page)), expected)

    def test_personal_project_shortcuts_ignore_hidden_task_activity(self):
        hidden = self.task(visibility='private', private_owner=self.owner)
        SpaceTaskActivity.objects.create(task=hidden, actor=self.member)
        self.assertEqual(self.page().context['for_you_projects'], [])

    def test_foreign_space_metadata_is_not_exposed(self):
        foreign = make_space(user=self.outsider, workplace=self.workspace, name='Obca przestrzeń')
        self.task(section=foreign, user=self.outsider)
        response = self.page()
        self.assertEqual(self.objects(response), [])
        self.assertNotContains(response, foreign.name)


    def test_sidebar_favorite_uses_scoped_for_you_url(self):
        response = self.client.post(reverse('workplaces:toggle-sidebar-favorite', args=[self.workspace.pk]),
                                    {'item_key': 'for-you', 'favorite_action': 'add'},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.url, response.json()['html'])
        self.assertContains(self.page(), 'data-sidebar-favorite-item="for-you"')

    def test_search_and_space_filter_apply_before_limit_and_survive_navigation(self):
        other_project = make_space(user=self.owner, workplace=self.workspace, name='Druga przestrzeń')
        other_section = make_space(user=other_project.user, workplace=other_project.workplace, name='Inna grupa')
        wanted = [self.task(f'Wdrożenie {i:02d}') for i in range(27)]
        self.task('Wdrożenie w innej przestrzeni', section=other_section)
        self.task('Inna nazwa')
        self.task('Wdrożenie prywatne', section=self.hidden_section)
        params = {'q': 'Wdrożenie', 'space': str(self.project.pk)}
        first = self.page('assigned', **params)
        self.assertEqual(self.objects(first), list(reversed(wanted[-20:])))
        self.assertEqual(self.objects(self.page('assigned', page=2, **params)), self.objects(first))
        for url in [tab['url'] for tab in first.context['for_you_tabs']]:
            query = parse_qs(urlsplit(url).query)
            self.assertEqual(query['q'], [params['q']])
            self.assertEqual(query['space'], [params['space']])
        self.assertNotContains(first, self.hidden_project.name)
        self.assertEqual(self.objects(self.page(q=wanted[0].title)), [wanted[0]])
        self.assertEqual(self.objects(self.page(q=wanted[-1].work_item.key)), [wanted[-1]])
        response = self.client.get(reverse('for_you'), {'tab': 'assigned', **params}, follow=True)
        self.assertEqual(self.objects(response), self.objects(first))

    def test_filters_cover_merged_tabs_and_do_not_grant_access(self):
        task = self.task('Dopasowane zadanie', priority='high')
        other = self.task('Pozostałe zadanie', priority='high')
        for obj in (task, other):
            obj.favorited_by.add(self.member)
            SpaceTaskActivity.objects.create(task=obj, actor=self.member)
            self.visit(obj)
        for tab in ('recommended', 'assigned', 'starred', 'worked', 'viewed'):
            with self.subTest(tab=tab):
                self.assertEqual(self.objects(self.page(tab, q='Dopasowane', space=str(self.project.pk))), [task])
                for space in (str(self.hidden_project.pk), '999999', '9' * 40, 'bad', '²'):
                    response = self.page(tab, space=space)
                    self.assertEqual(self.objects(response), [])
                    self.assertContains(response, 'Wyczyść filtry')
                    self.assertContains(response, 'Brak pasujących wyników')
        self.assertEqual(self.objects(self.page('starred', q='<script>"&')), [])
        self.assertNotContains(self.page('starred', q='<script>"&'), '<script>"&')

    def test_recent_space_shortcuts_and_assignments_recheck_access(self):
        self.task()
        self.task('Zamknięte', status='closed')
        self.task('Właściciela', assignee=self.owner)
        self.task('Ukryte', visibility='private', private_owner=self.owner)
        self.assertEqual(self.page().context['for_you_projects'], [])
        space_url = scoped_workplace_app_path(self.workspace, 'space', f'{self.project.slug}/')
        self.assertEqual(self.client.get(space_url).status_code, 200)
        shortcuts = self.page().context['for_you_projects']
        self.assertEqual([item['object'] for item in shortcuts], [self.project])
        self.assertEqual(shortcuts[0]['url'], space_url)
        assignments = self.page(space=self.project.pk)
        self.assertEqual(assignments.context['for_you_assigned_count'], 1)
        self.assertEqual(len(assignments.context['for_you_rows']), 1)
        self.project.visibility, self.project.private_owner = 'private', self.owner
        self.project.save()
        self.assertEqual(self.page().context['for_you_projects'], [])
        self.assertEqual(self.objects(self.page('viewed')), [])

    def test_favorite_spaces_precede_recent_activity_without_duplicates(self):
        favorite = make_space(user=self.owner, workplace=self.workspace, name='Ulubiona')
        favorite.favorited_by.add(self.member)
        self.project.favorited_by.add(self.member, self.owner)
        SpaceTaskActivity.objects.create(task=self.task(), actor=self.member)
        shortcuts = self.page().context['for_you_projects']
        self.assertEqual([row['object'] for row in shortcuts], [self.project, favorite])
        self.assertTrue(all(row['object'].is_starred for row in shortcuts))

    def test_worked_groups_use_local_dates_and_custom_status_labels(self):
        tasks = [self.task(f'Historia {i}') for i in range(4)]
        now = timezone.localtime().replace(hour=12, minute=0, second=0, microsecond=0)
        for task, days in zip(tasks, [0, 1, 3, 10]):
            activity = SpaceTaskActivity.objects.create(task=task, actor=self.member)
            SpaceTaskActivity.objects.filter(pk=activity.pk).update(created_at=now - timedelta(days=days))
        config = self.project.configuration
        config.settings['statuses'][0]['label'] = 'Do analizy'
        config.save()
        response = self.page('worked')
        rows = response.context['for_you_rows']
        self.assertEqual([row['date_group'] for row in rows], ['Dzisiaj', 'Wczoraj', 'Ostatnie 7 dni', 'Wcześniej'])
        self.assertEqual(rows[0]['key'], tasks[0].work_item.key)
        self.assertEqual(rows[0]['status_label'], 'Do analizy')
        self.assertContains(response, 'Do analizy')
        self.assertContains(response, tasks[0].work_item.key)
        blocks = response.context['for_you_groups']
        self.assertEqual([block['date_group'] for block in blocks], [row['date_group'] for row in rows])
        self.assertEqual([block['task_groups'][0]['items'][0]['object'] for block in blocks], tasks)

    def test_task_rows_use_custom_types_and_distinct_counts_in_every_tab(self):
        task = self.task(priority='high')
        task.tags.set([
            TaskTag.objects.create(user=self.owner, workplace=self.workspace, space=self.project, name=f'Tag {i}')
            for i in range(2)
        ])
        SpaceTaskFile.objects.bulk_create([
            SpaceTaskFile(task=task, file=f'qa/{i}.txt', filename=f'{i}.txt') for i in range(3)
        ])
        item = task.work_item
        item.work_type = 'bug'
        item.save(update_fields=['work_type'])
        config = self.project.configuration
        config.settings['types'][1]['label'] = 'Usterka'
        config.save()
        task.favorited_by.add(self.member)
        SpaceTaskActivity.objects.create(task=task, actor=self.member)
        self.visit(task)
        for tab in ('recommended', 'assigned', 'starred', 'worked', 'viewed'):
            with self.subTest(tab=tab):
                response = self.page(tab)
                row = response.context['for_you_rows'][0]['task_row']
                self.assertEqual((row['tags_count'], row['attachments_count']), (2, 3))
                self.assertEqual(row['get_work_type_display'], 'Usterka')
                self.assertEqual(row['type_icon'], 'circle-alert')
                self.assertContains(response, 'Typ zgłoszenia: Usterka')
                self.assertContains(response, 'Tagi: 2')
                self.assertContains(response, 'Załączniki: 3')
                self.assertContains(response, f'href="{row["url"]}"')

    def test_task_row_does_not_expose_foreign_space_metadata(self):
        task = self.task()
        WorkItem.objects.filter(pk=task.work_item.pk).update(space=self.hidden_project, key='TAJNY-KLUCZ')
        response = self.page()
        self.assertEqual(self.objects(response), [])
        self.assertNotContains(response, 'TAJNY-KLUCZ')
        self.assertNotContains(response, self.hidden_project.name)

    def test_task_without_planning_metadata_is_hidden(self):
        parent = self.task(assignee=None)
        child = self.task(parent=parent)
        child.work_item.delete()
        self.assertEqual(self.objects(self.page()), [])

    def test_status_groups_cover_all_tabs_and_keep_non_task_favorites(self):
        tasks = [self.task(status=status, priority='high') for status, _ in SpaceTask.STATUS_CHOICES]
        hidden = self.task(section=self.hidden_section, priority='high')
        for task in [*tasks, hidden]:
            task.favorited_by.add(self.member)
            SpaceTaskActivity.objects.create(task=task, actor=self.member)
        for task in tasks:
            self.visit(task)
        self.project.favorited_by.add(self.member)
        self.section.favorited_by.add(self.member)
        for tab in ('recommended', 'assigned', 'starred', 'worked', 'viewed'):
            with self.subTest(tab=tab):
                response = self.page(tab)
                block, = response.context['for_you_groups']
                expected = [task for task in tasks if tab not in ('recommended', 'assigned') or task.status != 'closed']
                groups = block['task_groups']
                self.assertEqual([group['category'] for group in groups], [task.status for task in expected])
                self.assertEqual([group['items'][0]['object'] for group in groups], expected)
                self.assertEqual(sum(len(group['items']) for group in groups), len(expected))
                self.assertNotContains(response, hidden.title + ' · ' + self.hidden_project.name)
                if tab == 'starred':
                    self.assertEqual(block['other_rows'], [])
                    self.assertEqual({space.pk for space in block['spaces']}, {self.project.pk, self.section.pk})
                else:
                    self.assertEqual(block['other_rows'], [])
                    self.assertEqual(block['spaces'], [])

    def test_status_groups_keep_custom_names_and_configuration_order(self):
        analysis = self.task('Do analizy')
        in_progress = self.task('Rozpoczęte', status='in_progress')
        second = self.task('Drugie do analizy')
        other_project = make_space(user=self.owner, workplace=self.workspace, name='Inna przestrzeń')
        other_section = make_space(user=other_project.user, workplace=other_project.workplace, name='Inna grupa')
        other = self.task('Domyślne nowe', section=other_section)
        config = self.project.configuration
        statuses = config.settings['statuses']
        statuses[0]['label'] = 'Do analizy'
        config.settings['statuses'] = [statuses[1], statuses[0], *statuses[2:]]
        config.save()
        response = self.page()
        groups = response.context['for_you_groups'][0]['task_groups']
        by_label = {group['label']: group for group in groups}
        self.assertEqual(set(by_label), {'W toku', 'Do analizy', 'Do zrobienia'})
        self.assertEqual(by_label['Do analizy']['category'], by_label['Do zrobienia']['category'])
        self.assertEqual([row['object'] for row in by_label['Do analizy']['items']], [second, analysis])
        self.assertEqual(by_label['W toku']['items'][0]['object'], in_progress)
        self.assertEqual(by_label['Do zrobienia']['items'][0]['object'], other)
        self.assertLess(groups.index(by_label['W toku']), groups.index(by_label['Do analizy']))
        filtered = self.page(q='Domyślne')
        filtered_groups = filtered.context['for_you_groups'][0]['task_groups']
        self.assertEqual([(group['label'], len(group['items'])) for group in filtered_groups], [('Do zrobienia', 1)])

    def test_space_table_counts_only_visible_tasks_and_respects_management_roles(self):
        self.task('Widoczne')
        self.task('Zakończone widoczne', status='closed')
        parent = self.task('Prywatne', visibility='private', private_owner=self.owner)
        self.task('Ukryty potomek', parent=parent)
        self.task('Inny Workspace', workplace=self.other_workspace, section=None)
        self.project.description = '<p>Opis przestrzeni</p>'
        self.project.save()
        self.project.favorited_by.add(self.member)
        self.hidden_project.favorited_by.add(self.member)
        space_url = scoped_workplace_app_path(self.workspace, 'space', f'{self.project.slug}/')
        self.assertEqual(self.client.get(space_url).status_code, 200)
        for tab in ('starred', 'viewed'):
            with self.subTest(tab=tab):
                response = self.page(tab)
                spaces = [space for block in response.context['for_you_groups'] for space in block['spaces']]
                self.assertEqual([space.pk for space in spaces], [self.project.pk])
                space, = spaces
                self.assertEqual(space.item_count, 2)
                self.assertFalse(space.can_manage)
                self.assertTrue(space.favorite)
                self.assertEqual(space.url, space_url)
                self.assertContains(response, 'Opis przestrzeni')
                self.assertNotContains(response, f'id="directory-space-{space.pk}-actions"')
                self.assertNotContains(response, f'href="{space.edit_url}"')
                self.assertNotContains(response, self.hidden_project.name)
        self.project.responsible_user = self.member
        self.project.save()
        response = self.page('starred')
        space = response.context['for_you_groups'][0]['spaces'][0]
        self.assertTrue(space.can_manage)
        self.assertNotContains(response, f'id="directory-space-{space.pk}-actions"')
        result = self.client.post(space.favorite_url, {'next': self.url + '?tab=starred'}, HTTP_X_SPACE_NAVIGATION='true')
        self.assertEqual(result.json(), {'saved': True})
        self.assertFalse(self.project.favorited_by.filter(pk=self.member.pk).exists())
        self.assertEqual(self.page('starred').context['for_you_groups'], [])
