from datetime import timedelta
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from kanban.models import Kanban, KanbanActivity, KanbanProject, KanbanSection
from tasks.models import Task, TaskActivity, TaskProject, TaskSection
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
        cls.project = TaskProject.objects.create(user=cls.owner, workplace=cls.workspace, name='Projekt zespołu')
        cls.section = TaskSection.objects.create(project=cls.project, title='Grupa zespołu')
        cls.hidden_project = TaskProject.objects.create(
            user=cls.owner, workplace=cls.workspace, name='Ukryty projekt', visibility='private', private_owner=cls.owner,
        )
        cls.hidden_section = TaskSection.objects.create(project=cls.hidden_project, title='Ukryta grupa')
        cls.url = scoped_workplace_app_path(cls.workspace, 'for-you')

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session[ACTIVE_WORKPLACE_SESSION_KEY] = self.workspace.pk
        session.save()

    def task(self, title='Moje zadanie', **kwargs):
        values = dict(user=self.owner, workplace=self.workspace, section=self.section, assignee=self.member)
        values.update(kwargs)
        return Task.objects.create(title=title, **values)

    def page(self, tab='assigned', **params):
        response = self.client.get(self.url, {'tab': tab, **params})
        self.assertEqual(response.status_code, 200)
        return response

    def objects(self, response):
        return [row['object'] for row in response.context['for_you_rows']]

    def visit(self, obj):
        url = scoped_workplace_app_path(self.workspace, obj._meta.app_label, f'view-task/{obj.task_id}/', f'task_pk={obj.pk}')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_authentication_base_scoped_context_search_and_cache(self):
        response = self.client.get(reverse('for_you'))
        self.assertContains(response, 'Dla ciebie | ancore')
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertContains(self.page('unknown'), 'aria-current="page">Polecane')
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
        hidden_group = TaskSection.objects.create(project=self.project, title='Prywatna grupa', visibility='private', private_owner=self.owner)
        hidden = [self.task('Inny Workspace', workplace=self.other_workspace, section=None),
                  self.task('Obcy właściciel', user=self.outsider, section=None),
                  self.task('Prywatny projekt', section=self.hidden_section),
                  self.task('Prywatna grupa', section=hidden_group),
                  hidden_parent, self.task('Ukryty potomek', parent=hidden_parent)]
        for task in [visible, *hidden]:
            task.favorited_by.add(self.member)
            TaskActivity.objects.create(task=task, actor=self.member)
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
        self.assertEqual(self.objects(self.page('recommended')), [overdue, soon, urgent])
        self.assertContains(self.page('recommended'), 'Po terminie')

    def test_worked_uses_personal_activity_and_deduplicates_both_modules(self):
        task = self.task()
        someone_elses = self.task('Czyjaś praca')
        TaskActivity.objects.create(task=someone_elses, actor=self.owner)
        TaskActivity.objects.create(task=task, actor=self.member)
        TaskActivity.objects.create(task=task, actor=self.member, kind='comment')
        card = Kanban.objects.create(user=self.owner, workplace=self.workspace, title='Moja karta')
        KanbanActivity.objects.create(task=card, actor=self.member)
        TaskActivity.objects.create(task=task, actor=self.owner)
        self.assertEqual(self.objects(self.page('worked')), [card, task])

    def test_starred_is_personal_and_includes_existing_favorite_kinds(self):
        task = self.task()
        other = self.task('Cudze ulubione')
        other.favorited_by.add(self.owner)
        project = KanbanProject.objects.create(user=self.owner, workplace=self.workspace, name='Kanban')
        board = KanbanSection.objects.create(project=project, title='Tablica')
        favorites = [task, self.project, self.section, project, board]
        for obj in favorites:
            obj.favorited_by.add(self.member)
        self.assertEqual(set(self.objects(self.page('starred'))), set(favorites))
        self.assertEqual([row['object'] for row in self.page().context['for_you_projects']], [self.project])

    def test_viewed_records_successful_views_deduplicates_and_rechecks_access(self):
        task = self.task()
        card = Kanban.objects.create(user=self.owner, workplace=self.workspace, title='Oglądana karta')
        self.visit(task)
        self.visit(card)
        self.visit(task)
        self.assertEqual(self.objects(self.page('viewed')), [task, card])
        self.assertEqual(len(self.client.session[RECENT_SESSION_KEY]), 2)
        task.visibility, task.private_owner = 'private', self.owner
        task.save()
        self.assertEqual(self.objects(self.page('viewed')), [card])
        card.delete()
        self.assertEqual(self.objects(self.page('viewed')), [])

    def test_viewed_projects_groups_and_session_user_scope(self):
        self.client.get(scoped_workplace_app_path(self.workspace, 'tasks', query_string=f'project={self.project.pk}'))
        self.client.get(scoped_workplace_app_path(self.workspace, 'tasks', f'groups/{self.section.pk}/'))
        self.assertEqual(self.objects(self.page('viewed')), [self.section, self.project])
        session = self.client.session
        entries = session[RECENT_SESSION_KEY]
        for entry in entries:
            entry['identity'][0] = self.owner.pk
        session[RECENT_SESSION_KEY] = entries
        session.save()
        self.assertEqual(self.objects(self.page('viewed')), [])

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

    def test_assignment_and_merged_favorites_pagination_and_invalid_page(self):
        tasks = [self.task(f'Zadanie {i:02d}') for i in range(29)]
        for task in tasks:
            task.favorited_by.add(self.member)
        self.project.favorited_by.add(self.member)
        for tab, expected in [('assigned', set(tasks)), ('starred', {*tasks, self.project})]:
            page1 = self.page(tab)
            page2 = self.page(tab, page=2)
            self.assertEqual(len(self.objects(page1)), 25)
            self.assertEqual(set(self.objects(page1)) | set(self.objects(page2)), expected)
            self.assertFalse(set(self.objects(page1)) & set(self.objects(page2)))
            self.assertEqual(self.objects(self.page(tab, page='bad')), self.objects(page1))
            self.assertEqual(self.objects(self.page(tab, page=99999)), self.objects(page2))

    def test_personal_project_shortcuts_ignore_hidden_task_activity(self):
        hidden = self.task(visibility='private', private_owner=self.owner)
        TaskActivity.objects.create(task=hidden, actor=self.member)
        self.assertEqual(self.page().context['for_you_projects'], [])

    def test_legacy_foreign_group_metadata_is_not_exposed(self):
        foreign = TaskProject.objects.create(user=self.outsider, workplace=self.workspace, name='Obcy projekt')
        section = TaskSection.objects.create(project=foreign, title='Obca grupa')
        task = self.task(section=section)
        response = self.page()
        self.assertEqual(self.objects(response), [task])
        self.assertNotContains(response, 'Obcy projekt')
        self.assertNotContains(response, 'Obca grupa')

    def test_kanban_history_and_favorites_disappear_when_access_is_revoked(self):
        project = KanbanProject.objects.create(user=self.owner, workplace=self.workspace, name='Prywatny Kanban', visibility='private', private_owner=self.owner)
        project.shared_with.add(self.member)
        board = KanbanSection.objects.create(project=project, title='Tablica')
        card = Kanban.objects.create(user=self.owner, workplace=self.workspace, section=board, title='Karta')
        project.favorited_by.add(self.member)
        board.favorited_by.add(self.member)
        KanbanActivity.objects.create(task=card, actor=self.member)
        self.visit(card)
        self.assertEqual(self.objects(self.page('worked')), [card])
        self.assertEqual(self.objects(self.page('viewed')), [card])
        project.shared_with.remove(self.member)
        for tab in ('worked', 'viewed', 'starred'):
            self.assertEqual(self.objects(self.page(tab)), [])

    def test_sidebar_favorite_uses_scoped_for_you_url(self):
        response = self.client.post(reverse('workplaces:toggle-sidebar-favorite', args=[self.workspace.pk]),
                                    {'item_key': 'for-you', 'favorite_action': 'add'},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.url, response.json()['html'])
        self.assertContains(self.page(), 'data-sidebar-favorite-item="for-you"')
