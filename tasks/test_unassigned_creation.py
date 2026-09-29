from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from workplaces.models import WorkplaceMembership, create_workplace_for_user

from .models import Task, TaskProject, TaskSection


class UnassignedTaskCreationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='unassigned-owner', email='owner@unassigned.test')
        cls.member = get_user_model().objects.create_user(username='unassigned-member', email='member@unassigned.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Zadania bez grupy')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.project = TaskProject.objects.create(user=cls.owner, workplace=cls.workspace, name='Projekt')
        cls.section = TaskSection.objects.create(project=cls.project, title='Grupa')
        cls.url = f'/workplaces/{cls.workspace.slug}/tasks/'

    def setUp(self):
        self.client.force_login(self.member)

    def payload(self, **changes):
        return {'action': 'create_task_modal', 'title': 'Nowe zadanie bez grupy',
                'project_id': '', 'section': '', 'status': 'new', 'priority': 'medium', **changes}

    def test_new_modal_has_no_group_even_on_project_and_group_pages(self):
        for url in (self.url, self.url + '?view=all-tasks',
                    self.url + f'?project={self.project.pk}', self.url + f'groups/{self.section.pk}/'):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertFalse(response.context['task_modal_form']['section'].value())
                self.assertFalse(response.context['issue_project_id'])
                self.assertFalse(response.context['task_modal_form'].fields['section'].required)

    def test_create_without_group_keeps_workspace_privacy_actor_and_completion(self):
        for url in ('/tasks/', self.url):
            with self.subTest(url=url):
                client = Client()
                client.force_login(self.member)
                session = client.session
                session['active_workplace_id'] = self.workspace.pk
                session.save()
                response = client.post(url, self.payload(assignee=self.member.pk, status='closed'))
                self.assertRedirects(response, url + '?view=unassigned-tasks')
                task = Task.objects.latest('pk')
                self.assertIsNone(task.section_id)
                self.assertEqual(task.user, self.owner)
                self.assertEqual(task.workplace, self.workspace)
                self.assertEqual(task.private_owner, self.member)
                self.assertEqual(task.assignee, self.member)
                self.assertEqual(task.visibility, 'private')
                self.assertTrue(task.is_completed)
                self.assertIsNotNone(task.completion_date)
                self.assertEqual(task.activities.get(action='created').actor, self.member)
                listing = client.get(response.url)
                self.assertIn(task, listing.context['task_window']['queryset'])

    def test_empty_workspace_allows_creation(self):
        empty = create_workplace_for_user(self.member, 'Pusty Workspace')
        url = f'/workplaces/{empty.slug}/tasks/'
        response = self.client.get(url)
        self.assertTrue(response.context['can_create_issue'])
        response = self.client.post(url, self.payload())
        self.assertRedirects(response, url + '?view=unassigned-tasks')
        self.assertTrue(Task.objects.filter(user=self.member, workplace=empty, section=None).exists())

    def test_create_from_group_page_does_not_inherit_its_group(self):
        response = self.client.post(self.url + f'groups/{self.section.pk}/', self.payload())
        self.assertRedirects(response, self.url + '?view=unassigned-tasks')
        self.assertIsNone(Task.objects.latest('pk').section_id)

    def test_explicit_group_is_saved_and_absent_from_unassigned(self):
        response = self.client.post(self.url, self.payload(project_id=self.project.pk, section=self.section.pk))
        self.assertEqual(response.status_code, 302)
        task = Task.objects.latest('pk')
        self.assertEqual(task.section, self.section)
        response = self.client.get(self.url, {'view': 'unassigned-tasks'})
        self.assertNotIn(task, response.context['task_window']['queryset'])

    def test_project_without_group_has_recoverable_validation_error(self):
        response = self.client.post(self.url, self.payload(project_id=self.project.pk))
        self.assertEqual(response.status_code, 200)
        self.assertIn('section', response.context['task_modal_form'].errors)
        self.assertTrue(response.context['task_modal_open'])
        self.assertEqual(response.context['issue_project_id'], str(self.project.pk))
        self.assertEqual(response.context['task_modal_form']['title'].value(), self.payload()['title'])
        self.assertFalse(Task.objects.exists())

    def test_invalid_private_foreign_or_mismatched_group_is_not_silently_dropped(self):
        other = create_workplace_for_user(self.owner, 'Inny Workspace')
        foreign_project = TaskProject.objects.create(user=self.owner, workplace=other, name='Obcy')
        foreign = TaskSection.objects.create(project=foreign_project, title='Obca grupa')
        private = TaskSection.objects.create(project=self.project, title='Prywatna',
                                             visibility='private', private_owner=self.owner)
        another_project = TaskProject.objects.create(user=self.owner, workplace=self.workspace, name='Drugi')
        mismatch = TaskSection.objects.create(project=another_project, title='Inna grupa')
        for section_id in (foreign.pk, private.pk, mismatch.pk, 999999):
            with self.subTest(section=section_id):
                response = self.client.post(self.url, self.payload(project_id=self.project.pk, section=section_id))
                self.assertEqual(response.status_code, 200)
                self.assertIn('section', response.context['task_modal_form'].errors)
                self.assertFalse(Task.objects.exists())

    def test_edit_unassigned_task_and_later_assign_group(self):
        self.client.post(self.url, self.payload())
        task = Task.objects.latest('pk')
        url = self.url + f'view-task/{task.task_id}/?task_pk={task.pk}'
        data = self.payload(title='Po edycji')
        data.pop('action')
        data.pop('project_id')
        response = self.client.post(url, {**data, 'project': ''})
        self.assertEqual(response.status_code, 302)
        task.refresh_from_db()
        self.assertEqual(task.title, 'Po edycji')
        self.assertIsNone(task.section_id)
        response = self.client.post(url, {**data, 'project': self.project.pk, 'section': self.section.pk})
        self.assertEqual(response.status_code, 302)
        task.refresh_from_db()
        self.assertEqual(task.section, self.section)
        listing = self.client.get(self.url, {'view': 'unassigned-tasks'})
        self.assertNotIn(task, listing.context['task_window']['queryset'])
