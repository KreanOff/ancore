from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from tasks.models import TaskProject
from .models import WorkplaceMembership, create_workplace_for_user
from .services import scoped_workplace_app_path
from .templatetags.workplace_avatar import workplace_avatar


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
        self.assertContains(response, 'workplaces-page workplaces-settings-page')
        self.assertContains(response, 'tasks-topbar workplaces-task-topbar')
        self.assertContains(response, 'tasks-titlebar-search tasks-search-actions')
        self.assertContains(response, 'tasks-filterbar workplaces-task-filterbar')
        self.assertContains(response, 'data-workplace-create-open')
        self.assertContains(response, 'id="workplace-create-modal"')
        self.assertContains(response, 'Nawigacja ustawień')
        self.assertContains(response, 'Miejsca pracy')
        self.assertContains(response, reverse('settings'))
        self.assertNotContains(response, 'workplaces-shell-header')
        self.assertNotContains(response, 'workplaces-console__toolbar')
        self.assertNotContains(response, 'dashboard-header workplaces-settings-header')
        self.assertNotContains(response, 'workplace-inspector')
        self.assertNotContains(response, 'data-workplace-inspector')
        self.assertNotContains(response, 'data-workplace-inspector-status')
        self.assertNotContains(response, 'is-inspected')
        self.assertContains(response, 'data-workplaces-select-all')
        self.assertContains(response, 'data-workplace-id=', count=2)
        self.assertNotContains(response, 'data-column="logo"')
        self.assertContains(response, 'workplace-row__avatar', count=2)
        self.assertContains(response, 'Pierwszy Workplace')
        self.assertContains(response, 'Drugi Workplace')
        self.assertNotContains(response, 'Nie moj Workplace')

    def test_workplace_create_renders_in_tasks_project_modal_shell(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('workplaces:workplaces'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-workplace-create-open')
        self.assertContains(response, 'tasks-modal tasks-project-modal tasks-project-create-modal tasks-issue-modal workplace-create-modal')
        self.assertContains(response, 'tasks-modal__form tasks-project-modal__form tasks-project-create-modal__form tasks-issue-modal__form workplace-create-modal__form')
        self.assertContains(response, 'Nowe miejsce pracy')
        self.assertContains(response, 'Utwórz miejsce pracy')
        self.assertNotContains(response, 'workplaces-create-form--filterbar')

    def test_workplace_avatar_uses_workplace_specific_background_color(self):
        first_avatar = workplace_avatar(self.first_workplace)
        second_avatar = workplace_avatar(self.second_workplace)

        self.assertEqual(first_avatar['background_color'], workplace_avatar(self.first_workplace)['background_color'])
        self.assertNotEqual(first_avatar['background_color'], second_avatar['background_color'])

        self.client.force_login(self.user)
        response = self.client.get(reverse('workplaces:workplaces'))

        self.assertContains(response, first_avatar['color_style'])
        self.assertContains(response, second_avatar['color_style'])
        self.assertContains(
            response,
            'class="profile-avatar-icon" data-lucide="briefcase"',
            count=5,
        )
        self.assertNotContains(response, 'data-lucide="landmark"')

    def test_workplace_edit_renders_in_tasks_modal_shell(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('workplaces:workplaces'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-workplace-edit-modal>', count=2)
        self.assertContains(response, 'data-workplace-edit-open="workplace-edit-modal-')
        self.assertContains(response, 'tasks-modal tasks-project-modal tasks-project-edit-modal tasks-issue-modal workplace-edit-modal')
        self.assertContains(response, 'tasks-modal__form tasks-project-modal__form tasks-project-rename-modal__form tasks-project-edit-modal__form tasks-issue-modal__form workplace-edit-modal__form')
        self.assertContains(response, 'Edytuj miejsce pracy')
        self.assertNotContains(response, 'class="workplace-settings workplace-settings--inspector"')
        self.assertNotContains(response, 'class="workplace-settings__form"')

    def test_sidebar_workplace_button_is_fixed_when_workplace_has_photo(self):
        self.first_workplace.workplace_photo = 'workplace_photos/moje-miejsce.webp'
        self.first_workplace.save(update_fields=['workplace_photo'])
        self.client.force_login(self.user)
        self._activate(self.first_workplace)

        response = self.client.get(reverse('tasks:tasks'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="nav-link nav-link--workplace ')
        self.assertContains(response, 'data-lucide="briefcase"')
        self.assertNotContains(response, 'sidebar-workplace__avatar')
        self.assertNotContains(response, '/media/workplace_photos/moje-miejsce.webp')

    def test_sidebar_displays_workplace_between_toggle_and_tasks_without_separator(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('tasks:tasks'))
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="sidebar-header"')
        self.assertContains(response, 'href="/" class="logo" aria-label="Ancore"')
        self.assertContains(response, '/static/img/logo-ancore.png')
        self.assertNotContains(response, 'class="nav-separator"')
        self.assertLess(content.index('class="sidebar-header"'), content.index('class="nav-link nav-link--workplace '))
        self.assertLess(content.index('id="secondary-menu-toggle"'), content.index('class="nav-link nav-link--workplace '))
        self.assertLess(content.index('class="nav-link nav-link--workplace '), content.index('aria-label="Zadania"'))

    def test_sidebar_workplace_button_uses_standard_nav_link_without_photo(self):
        self.client.force_login(self.user)
        self._activate(self.first_workplace)

        response = self.client.get(reverse('tasks:tasks'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="nav-link nav-link--workplace ')
        self.assertContains(
            response,
            '<i class="nav-icon nav-icon--workplace" data-lucide="briefcase" aria-hidden="true"></i>',
            html=True,
        )

    def test_topbar_displays_active_workplace_name(self):
        self.client.force_login(self.user)
        self._activate(self.second_workplace)

        response = self.client.get(reverse('tasks:tasks'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="app-topbar"')
        self.assertContains(response, 'Miejsce pracy:')
        self.assertContains(response, '<strong>Drugi Workplace</strong>', html=True)
        self.assertContains(response, 'title="Bieżące miejsce pracy: Drugi Workplace"')

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

    def test_duplicate_create_reopens_workplace_create_modal(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('workplaces:workplaces'), {'name': self.first_workplace.name})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'workplace-create-modal is-open')
        self.assertContains(response, 'aria-hidden="false" data-workplace-create-modal')
        self.assertContains(response, 'Masz już miejsce pracy o takiej nazwie.')

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
