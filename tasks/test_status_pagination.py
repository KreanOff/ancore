from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from workplaces.models import create_workplace_for_user
from .models import Task, TaskProject, TaskSection, TaskTag


class TaskStatusPaginationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='status-pagination', email='pagination@example.test')
        cls.workplace = create_workplace_for_user(cls.user, 'Statusy')
        cls.project = TaskProject.objects.create(
            user=cls.user, workplace=cls.workplace, name='Projekt', code='PGN',
        )
        cls.section = TaskSection.objects.create(project=cls.project, title='Grupa')
        Task.objects.bulk_create([
            Task(
                user=cls.user, workplace=cls.workplace, section=cls.section,
                assignee=cls.user, task_id=status_index * 53 + index + 1,
                title=f'Zadanie {status} {index:03d}', status=status,
                is_completed=status == 'closed',
            )
            for status_index, (status, _label) in enumerate(Task.STATUS_CHOICES)
            for index in range(53)
        ])
        other_workplace = create_workplace_for_user(cls.user, 'Inna przestrzeń')
        other_user = get_user_model().objects.create_user(username='other-pagination', email='other-pagination@example.test')
        foreign_workplace = create_workplace_for_user(other_user, 'Obca przestrzeń')
        for owner, workplace in ((cls.user, other_workplace), (other_user, foreign_workplace)):
            Task.objects.create(
                user=owner, workplace=workplace, assignee=cls.user,
                title='Niedostępne zamknięte', status='closed',
            )

    def setUp(self):
        self.client.force_login(self.user)
        session = self.client.session
        session['active_workplace_id'] = self.workplace.pk
        session.save()

    def test_limit_and_pages_apply_to_every_status_in_both_views_and_url_scopes(self):
        urls = [reverse('tasks:tasks'), f'/workplaces/{self.workplace.slug}/tasks/']
        for url in urls:
            for view in ('all-tasks', 'my-tasks'):
                with self.subTest(url=url, view=view):
                    response = self.client.get(url, {'view': view, 'tab': 'public'})
                    self.assertEqual(response.status_code, 200)
                    window = response.context['task_window']
                    self.assertEqual(window['total_tasks'], 265)
                    self.assertEqual(window['total_pages'], 2)
                    self.assertContains(response, 'Pokazano 1-250 z 265 zadań')
                    self.assertContains(response, 'task-row tasks-issue-row', count=250)
                    self.assertNotContains(response, 'Niedostępne zamknięte')
                    self.assertEqual(
                        [group['count'] for group in response.context['all_status_groups']],
                        [50] * 5,
                    )
                    first_ids = {task.pk for task in window['queryset']}
                    self.assertIn(url, window['next_url'])
                    response = self.client.get(window['next_url'])
                    window = response.context['task_window']
                    self.assertContains(response, 'Pokazano 251-265 z 265 zadań')
                    self.assertEqual(
                        [group['count'] for group in response.context['all_status_groups']],
                        [3] * 5,
                    )
                    second_ids = {task.pk for task in window['queryset']}
                    self.assertFalse(first_ids & second_ids)
                    self.assertEqual(len(first_ids | second_ids), 265)
                    self.assertFalse(window['has_next'])
                    self.assertTrue(window['has_previous'])

    def test_page_size_validation_and_out_of_range_pages(self):
        for size, expected, pages in ((10, 50, 6), (25, 125, 3), (100, 265, 1), ('bad', 250, 2), (0, 250, 2)):
            with self.subTest(size=size):
                response = self.client.get(reverse('tasks:tasks'), {'view': 'all-tasks', 'tab': 'public', 'page_size': size})
                self.assertEqual(len(response.context['task_window']['queryset']), expected)
                self.assertEqual(response.context['task_window']['total_pages'], pages)
        response = self.client.get(reverse('tasks:tasks'), {'view': 'all-tasks', 'tab': 'public', 'page_size': 10, 'page': 999})
        self.assertEqual(response.context['task_window']['page'], 6)
        self.assertContains(response, 'Pokazano 251-265 z 265 zadań')
        response = self.client.get(reverse('tasks:tasks'), {'view': 'all-tasks', 'tab': 'public', 'page': -1})
        self.assertEqual(response.context['task_window']['page'], 1)

    def test_filters_and_sort_apply_before_each_status_is_paginated(self):
        response = self.client.get(reverse('tasks:tasks'), {
            'view': 'all-tasks', 'tab': 'public', 'q': 'Zadanie', 'status': 'closed',
            'task_project': self.project.pk, 'sort': 'title_desc', 'page_size': 25,
        })
        window = response.context['task_window']
        self.assertEqual(window['total_tasks'], 53)
        self.assertEqual(window['total_pages'], 3)
        self.assertEqual(window['queryset'][0].title, 'Zadanie closed 052')
        self.assertEqual(window['queryset'][-1].title, 'Zadanie closed 028')
        self.assertContains(response, 'id="all-tasks-closed"')
        self.assertNotContains(response, 'id="all-tasks-new"')
        response = self.client.get(window['next_url'])
        self.assertEqual(response.context['task_window']['queryset'][0].title, 'Zadanie closed 027')
        self.assertEqual(response.context['task_window']['status'], 'closed')
        self.assertEqual(response.context['task_window']['query'], 'Zadanie')
        self.assertEqual(response.context['task_window']['project_filter'], str(self.project.pk))

    def test_tag_search_does_not_duplicate_tasks_or_counts(self):
        task = Task.objects.get(user=self.user, workplace=self.workplace, title='Zadanie closed 000')
        for name in ('Znacznik pierwszy', 'Znacznik drugi'):
            task.tags.add(TaskTag.objects.create(user=self.user, workplace=self.workplace, name=name))
        response = self.client.get(reverse('tasks:tasks'), {
            'view': 'all-tasks', 'tab': 'public', 'q': 'Znacznik', 'sort': 'activity_desc',
        })
        self.assertEqual(response.context['task_window']['total_tasks'], 1)
        self.assertEqual(response.context['task_window']['queryset'], [task])

    def test_my_tasks_excludes_unassigned_tasks_and_subtasks(self):
        task = Task.objects.filter(user=self.user, workplace=self.workplace, status='closed').first()
        task.assignee = None
        task.save(update_fields=['assignee'])
        Task.objects.create(
            user=self.user, workplace=self.workplace, section=self.section,
            parent=task, assignee=self.user, title='Podzadanie poza katalogiem', status='closed',
        )
        response = self.client.get(reverse('tasks:tasks'), {'view': 'my-tasks', 'page_size': 100})
        self.assertEqual(response.context['task_window']['total_tasks'], 264)
        self.assertNotIn(task, response.context['task_window']['queryset'])
        self.assertNotContains(response, 'Podzadanie poza katalogiem')

    def test_empty_results_have_no_pages(self):
        response = self.client.get(reverse('tasks:tasks'), {'view': 'all-tasks', 'tab': 'public', 'q': 'Nieistniejące'})
        window = response.context['task_window']
        self.assertEqual(window['total_tasks'], 0)
        self.assertEqual(window['queryset'], [])
        self.assertFalse(window['has_previous'])
        self.assertFalse(window['has_next'])
        self.assertContains(response, '0 z 0')

    def test_unassigned_tasks_filter_search_sort_and_paginate_before_rendering(self):
        tasks = Task.objects.filter(user=self.user, workplace=self.workplace, status='new')
        tasks.update(section=None)
        params = {'view': 'unassigned-tasks', 'q': 'Zadanie new', 'status': 'new',
                  'task_project': self.project.pk, 'sort': 'title_desc', 'page_size': 25}
        url = f'/workplaces/{self.workplace.slug}/tasks/'
        response = self.client.get(url, params)
        window = response.context['task_window']
        self.assertEqual(window['total_tasks'], 53)
        self.assertEqual(len(window['queryset']), 25)
        self.assertEqual(window['queryset'][0].title, 'Zadanie new 052')
        self.assertIn('view=unassigned-tasks', window['next_url'])
        self.assertTrue(window['next_url'].startswith(url))
        response = self.client.get(window['next_url'])
        self.assertEqual(response.context['task_window']['queryset'][0].title, 'Zadanie new 027')
        self.assertEqual(response.context['task_window']['project_filter'], '')
        response = self.client.get(url, {**params, 'q': 'Brak dopasowania'})
        self.assertContains(response, 'Nie znaleziono zadań.')
