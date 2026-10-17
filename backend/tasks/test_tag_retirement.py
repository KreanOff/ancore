from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from spaces.testing import make_space
from tasks.models import Task, TaskProject, TaskSection, TaskTag, TaskTagNote
from workplaces.models import SidebarFavorite, WorkplaceMembership, create_workplace_for_user
from workplaces.services import ACTIVE_WORKPLACE_SESSION_KEY, scoped_workplace_app_path


class LegacyTagRetirementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='tag-retirement-owner', email='tag-retirement@example.test')
        cls.member = get_user_model().objects.create_user(username='tag-retirement-member', email='tag-member@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Bez starego katalogu tagów')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.project = TaskProject.objects.create(user=cls.owner, workplace=cls.workspace, name='Produkt')
        cls.section = TaskSection.objects.create(project=cls.project, title='Praca')
        cls.task = Task.objects.create(user=cls.owner, workplace=cls.workspace, title='Zadanie bez przestrzeni')
        cls.legacy = TaskTag.objects.create(user=cls.owner, workplace=cls.workspace, name='LegacyTagProbe')
        cls.note = TaskTagNote.objects.create(tag=cls.legacy, author=cls.owner, message='LegacyNoteProbe')
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Produkt')
        cls.local = TaskTag.objects.create(user=cls.owner, workplace=cls.workspace, space=cls.space, name='Tag produktu')
        cls.task.tags.add(cls.legacy)

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session[ACTIVE_WORKPLACE_SESSION_KEY] = self.workspace.pk
        session.save()

    def prefixes(self):
        return ['/tasks/', scoped_workplace_app_path(self.workspace, 'tasks')]

    def test_old_directory_and_all_actions_return_404_without_changing_data(self):
        actions = ['create_tag', 'edit_tag', 'delete_tag', 'add_tag_note', 'update_tag_notes', 'edit_tag_note', 'delete_tag_note']
        for user in [self.owner, self.member]:
            self.login(user)
            for prefix in self.prefixes():
                for suffix in ['', f'groups/{self.section.pk}/']:
                    url = prefix + suffix
                    self.assertEqual(self.client.get(url + '?view=tags').status_code, 404)
                    for action in actions:
                        with self.subTest(user=user.pk, url=url, action=action):
                            payload = {'action': action, 'tag_id': self.legacy.pk, 'note_id': self.note.pk,
                                       'name': 'Nowy tag', 'message': 'Zmiana'}
                            self.assertEqual(self.client.post(url, payload).status_code, 404)
                            self.assertEqual(self.client.post(url + '?view=tags', payload).status_code, 404)
        self.legacy.refresh_from_db()
        self.note.refresh_from_db()
        self.assertEqual(self.legacy.name, 'LegacyTagProbe')
        self.assertEqual(self.note.message, 'LegacyNoteProbe')
        self.assertEqual(TaskTag.objects.count(), 2)

    def test_task_pages_have_no_legacy_directory_links_modals_or_tag_metadata(self):
        self.login(self.owner)
        SidebarFavorite.objects.create(user=self.owner, workplace=self.workspace, item_key='tags')
        for prefix in self.prefixes():
            for suffix in ['', '?view=unassigned-tasks', f'groups/{self.section.pk}/',
                           f'view-task/{self.task.task_id}/?task_pk={self.task.pk}']:
                response = self.client.get(prefix + suffix, follow=True)
                if suffix.startswith(('groups/', 'view-task/')):
                    self.assertEqual(response.status_code, 404)
                    continue
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, self.task.title)
                for marker in ['?view=tags', 'data-open-tag', 'id="tag-modal"', 'id="tag-notes-modal"',
                               'data-sidebar-favorite-item="tags"', 'LegacyTagProbe']:
                    self.assertNotContains(response, marker)

    def test_search_excludes_legacy_tags_and_the_old_navigation_entry(self):
        self.login(self.member)
        for query in ['LegacyTagProbe', self.legacy.code, 'LegacyNoteProbe', 'Tagi']:
            payload = self.client.get(reverse('global_search'), {'q': query}).json()
            self.assertNotIn('/tasks/?view=tags', str(payload))
            self.assertNotIn('LegacyTagProbe', str(payload['groups']))
            self.assertNotIn('LegacyNoteProbe', str(payload['groups']))
            if query != 'Tagi':
                self.assertEqual(payload['total'], 0)

    def test_retired_creation_cannot_assign_legacy_tags(self):
        self.login(self.owner)
        response = self.client.post('/tasks/', {'action': 'create_task_modal', 'title': 'Nie zapisuj',
                                               'priority': 'medium', 'status': 'new', 'tags': [self.legacy.pk]})
        self.assertEqual(response.status_code, 409)
        self.assertFalse(Task.objects.filter(title='Nie zapisuj').exists())

    def test_retired_favorite_cannot_be_added(self):
        self.login(self.owner)
        response = self.client.post(reverse('workplaces:toggle-sidebar-favorite', args=[self.workspace.pk]),
                                    {'item_key': 'tags', 'favorite_action': 'add'},
                                    HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(SidebarFavorite.objects.filter(item_key='tags').exists())

    def test_opening_workspace_does_not_backfill_historical_tags(self):
        old = TaskTag.objects.create(user=self.owner, name='Tag sprzed Workspace')
        self.login(self.owner)
        self.assertEqual(self.client.get(self.prefixes()[1]).status_code, 302)
        old.refresh_from_db()
        self.assertIsNone(old.workplace_id)
        self.assertIsNone(old.space_id)

    def test_space_tags_remain_available_in_both_url_variants(self):
        self.login(self.owner)
        for prefix in ['/space/', scoped_workplace_app_path(self.workspace, 'space')]:
            url = f'{prefix}{self.space.slug}/?view=tags'
            response = self.client.get(url)
            self.assertContains(response, self.local.name)
            self.assertNotContains(response, self.legacy.name)
            self.assertContains(response, 'data-open-tag')
            self.assertEqual(self.client.post(url, {'action': 'create_tag', 'name': 'Wydanie'}).status_code, 302)
            TaskTag.objects.filter(space=self.space, name='Wydanie').delete()

    def test_old_tag_and_task_admin_directories_remain_removed(self):
        self.owner.is_staff = self.owner.is_superuser = True
        self.owner.save(update_fields=['is_staff', 'is_superuser'])
        self.login(self.owner)
        for suffix in ['', 'add/', f'{self.legacy.pk}/change/', f'{self.legacy.pk}/delete/']:
            self.assertEqual(self.client.get('/admin/tasks/tasktag/' + suffix).status_code, 404)
        response = self.client.get(f'/admin/tasks/task/{self.task.pk}/change/')
        self.assertEqual(response.status_code, 404)
