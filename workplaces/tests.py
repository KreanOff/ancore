from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from tasks.models import TaskProject
from .models import WorkplaceMembership, create_workplace_for_user
from .services import scoped_workplace_app_path


class WorkplaceSelectionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='@workplace.user',
            email='workplace@example.com',
            password='secret',
            first_name='Work',
            last_name='Place',
        )
        self.first_workplace = create_workplace_for_user(self.user, 'Pierwszy Workplace')
        self.second_workplace = create_workplace_for_user(self.user, 'Drugi Workplace')

    def _activate(self, workplace):
        session = self.client.session
        session['active_workplace_id'] = workplace.pk
        session.save()

    def test_workplace_list_is_login_destination_surface(self):
        other_user = get_user_model().objects.create_user(
            username='@other.owner',
            email='other@example.com',
            password='secret',
            first_name='Other',
            last_name='Owner',
        )
        shared_workplace = create_workplace_for_user(other_user, 'Nie moj Workplace')
        WorkplaceMembership.objects.create(
            workplace=shared_workplace,
            user=self.user,
            role=WorkplaceMembership.Role.MEMBER,
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('workplaces:workplaces'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pierwszy Workplace')
        self.assertContains(response, 'Drugi Workplace')
        self.assertNotContains(response, 'Nie moj Workplace')

    def test_tasks_projects_are_scoped_to_active_workplace(self):
        self.client.force_login(self.user)
        self._activate(self.first_workplace)
        TaskProject.objects.create(
            name='Projekt w pierwszym',
            user=self.user,
            workplace=self.first_workplace,
        )
        TaskProject.objects.create(
            name='Projekt w drugim',
            user=self.user,
            workplace=self.second_workplace,
        )

        response = self.client.get(reverse('tasks:tasks'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Projekt w pierwszym')
        self.assertNotContains(response, 'Projekt w drugim')

    def test_switch_workplace_redirects_to_scoped_tasks_url(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('workplaces:switch', args=[self.second_workplace.pk]))

        self.assertRedirects(
            response,
            scoped_workplace_app_path(self.second_workplace, 'tasks'),
            fetch_redirect_response=False,
        )

    def test_create_workplace_redirects_to_scoped_tasks_url(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('workplaces:workplaces'), {'name': 'Nowy Workplace'})
        workplace = type(self.first_workplace).objects.get(owner=self.user, name='Nowy Workplace')

        self.assertRedirects(
            response,
            scoped_workplace_app_path(workplace, 'tasks'),
            fetch_redirect_response=False,
        )

    def test_scoped_tasks_url_sets_active_workplace_from_slug(self):
        self.client.force_login(self.user)
        TaskProject.objects.create(
            name='Projekt w pierwszym',
            user=self.user,
            workplace=self.first_workplace,
        )
        TaskProject.objects.create(
            name='Projekt w drugim',
            user=self.user,
            workplace=self.second_workplace,
        )

        response = self.client.get(scoped_workplace_app_path(self.second_workplace, 'tasks'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Projekt w drugim')
        self.assertNotContains(response, 'Projekt w pierwszym')
        self.assertEqual(self.client.session['active_workplace_id'], self.second_workplace.pk)

    def test_scoped_tasks_page_keeps_legacy_reverse_links_valid(self):
        self.client.force_login(self.user)
        project = TaskProject.objects.create(
            name='Projekt w drugim',
            user=self.user,
            workplace=self.second_workplace,
        )

        response = self.client.get(scoped_workplace_app_path(self.second_workplace, 'tasks'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/tasks/?view=my-tasks"')
        self.assertContains(response, f'data-view-url="/tasks/?project={project.pk}"')
        self.assertNotContains(response, '/workplaces/-/tasks/')

    def test_legacy_tasks_url_redirects_after_workplace_flow(self):
        self.client.force_login(self.user)
        self._activate(self.second_workplace)
        self.client.get(reverse('workplaces:workplaces'))

        response = self.client.get(reverse('tasks:tasks'))

        self.assertRedirects(
            response,
            scoped_workplace_app_path(self.second_workplace, 'tasks'),
            fetch_redirect_response=False,
        )

    def test_owner_can_rename_workplace_from_settings(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('workplaces:update', args=[self.first_workplace.pk]),
            {'name': 'Nowa nazwa'},
        )

        self.assertRedirects(response, reverse('workplaces:workplaces'))
        self.first_workplace.refresh_from_db()
        self.assertEqual(self.first_workplace.name, 'Nowa nazwa')

    def test_owner_cannot_rename_workplace_to_duplicate_name(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('workplaces:update', args=[self.first_workplace.pk]),
            {'name': self.second_workplace.name},
        )

        self.assertRedirects(response, reverse('workplaces:workplaces'))
        self.first_workplace.refresh_from_db()
        self.assertEqual(self.first_workplace.name, 'Pierwszy Workplace')

    def test_owner_can_delete_non_last_workplace(self):
        self.client.force_login(self.user)
        self._activate(self.first_workplace)

        response = self.client.post(reverse('workplaces:delete', args=[self.first_workplace.pk]))

        self.assertRedirects(response, reverse('workplaces:workplaces'))
        self.assertFalse(type(self.first_workplace).objects.filter(pk=self.first_workplace.pk).exists())
        self.assertEqual(self.client.session['active_workplace_id'], self.second_workplace.pk)

    def test_owner_cannot_delete_last_workplace(self):
        self.second_workplace.delete()
        self.client.force_login(self.user)

        response = self.client.post(reverse('workplaces:delete', args=[self.first_workplace.pk]))

        self.assertRedirects(response, reverse('workplaces:workplaces'))
        self.assertTrue(type(self.first_workplace).objects.filter(pk=self.first_workplace.pk).exists())
