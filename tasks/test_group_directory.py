from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from workplaces.models import WorkplaceMembership, create_workplace_for_user

from .models import TaskProject, TaskSection


class ProjectGroupDirectoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='group-directory-owner', email='owner@groups.example.test')
        cls.member = get_user_model().objects.create_user(username='group-directory-member', email='member@groups.example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Grupy zespołu')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.project = TaskProject.objects.create(
            user=cls.owner, workplace=cls.workspace, name='Projekt grup',
        )
        cls.groups = [
            TaskSection.objects.create(
                project=cls.project, title=f'Etap {index:02}', status='ready',
                kind='milestones', priority='urgent', owner=cls.member, order=index,
            )
            for index in range(12)
        ]
        TaskSection.objects.create(project=cls.project, title='Poza filtrami')
        cls.other_project = TaskProject.objects.create(
            user=cls.owner, workplace=cls.workspace, name='Inny projekt',
        )
        TaskSection.objects.create(project=cls.other_project, title='Etap spoza projektu')
        other_workspace = create_workplace_for_user(cls.owner, 'Inny Workspace')
        cls.foreign_project = TaskProject.objects.create(
            user=cls.owner, workplace=other_workspace, name='Inny Workspace',
        )
        TaskSection.objects.create(project=cls.foreign_project, title='Etap innego Workspace')

    def setUp(self):
        self.client.force_login(self.member)
        self.url = f'/workplaces/{self.workspace.slug}/tasks/'

    def test_filters_sorting_and_pagination_keep_project_and_workspace(self):
        params = {
            'project': self.project.pk, 'q': 'Etap', 'priority': 'urgent',
            'status': 'ready', 'kind': 'milestones', 'owner': self.member.pk,
            'sort': 'title_desc', 'page_size': 10,
        }
        response = self.client.get(self.url, params)
        self.assertEqual(response.status_code, 200)
        window = response.context['project_section_window']
        self.assertEqual(window['total_groups'], 12)
        self.assertEqual([group.pk for group in window['sections']],
                         [group.pk for group in reversed(self.groups[2:])])
        next_url = window['next_url']
        self.assertEqual(urlsplit(next_url).path, self.url)
        self.assertEqual(parse_qs(urlsplit(next_url).query),
                         {**{key: [str(value)] for key, value in params.items()}, 'page': ['2']})
        response = self.client.get(next_url)
        self.assertEqual([group.pk for group in response.context['project_sections']],
                         [self.groups[1].pk, self.groups[0].pk])
        self.assertEqual(response.context['group_window']['compact_summary'], '11-12 z 12')

    def test_project_scope_survives_conflicting_filter_and_empty_results(self):
        response = self.client.get(self.url, {
            'project': self.project.pk, 'group_project': self.other_project.pk,
        })
        self.assertEqual(response.context['group_window']['total_groups'], 13)
        self.assertTrue(all(group.project_id == self.project.pk
                            for group in response.context['project_sections']))
        response = self.client.get(self.url, {'project': self.project.pk, 'q': 'Brak takiej grupy'})
        self.assertEqual(response.context['group_window']['compact_summary'], '0 z 0')
        self.assertContains(response, 'Brak grup pasujących do wyszukiwania lub filtrów.')
        self.assertFalse(response.context['group_window']['has_next'])
        self.assertFalse(response.context['group_window']['has_previous'])

    def test_regular_url_and_foreign_workspace_access(self):
        self.client.get(self.url)
        response = self.client.get(reverse('tasks:tasks'), {'project': self.project.pk}, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['group_window']['total_groups'], 13)
        response = self.client.get(self.url, {'project': self.foreign_project.pk})
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context['active_project'])
        self.assertEqual(response.context['project_sections'], [])
        self.assertNotContains(response, 'Etap innego Workspace')
        outsider = get_user_model().objects.create_user(username='group-directory-outsider', email='outsider@groups.example.test')
        self.client.force_login(outsider)
        response = self.client.get(self.url, {'project': self.project.pk})
        self.assertRedirects(response, reverse('workplaces:workplaces'), fetch_redirect_response=False)
