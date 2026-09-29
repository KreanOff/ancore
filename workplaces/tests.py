import base64
import json
import tempfile
from importlib import import_module

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from tasks.models import TaskProject
from .models import SidebarFavorite, WorkplaceMembership, create_workplace_for_user
from .services import scoped_workplace_app_path, workplace_management_url
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
        self.first_workplace = create_workplace_for_user(
            self.user,
            'Pierwszy Workplace',
            description='Miejsce pracy zespołu wdrożeniowego',
            code='first-01',
        )
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
        self.assertContains(response, 'tasks-topbar tasks-topbar--directory tasks-topbar--project-directory workplaces-task-topbar')
        self.assertContains(response, 'id="workplaces-search-input"')
        self.assertContains(response, 'tasks-filterbar tasks-filterbar--directory tasks-filterbar--project-directory workplaces-management__toolbar')
        self.assertContains(response, 'data-workplace-create-open')
        self.assertContains(response, 'id="workplace-create-modal"')
        self.assertNotContains(response, 'aria-label="Zarządzanie Workspace"')
        self.assertContains(response, '<title>Workspace | ancore</title>', html=True)
        self.assertContains(response, '<h1 id="workplaces-page-title" class="u-sr-only">Workspace</h1>', html=True)
        self.assertNotContains(response, 'workplaces-management__views')
        self.assertNotContains(response, 'Miejsca pracy')
        self.assertContains(response, reverse('settings'))
        self.assertNotContains(response, 'workplaces-shell-header')
        self.assertNotContains(response, 'workplaces-console__toolbar')
        self.assertNotContains(response, 'dashboard-header workplaces-settings-header')
        self.assertNotContains(response, 'workplace-inspector')
        self.assertNotContains(response, 'data-workplace-inspector')
        self.assertNotContains(response, 'data-workplace-inspector-status')
        self.assertNotContains(response, 'is-inspected')
        self.assertContains(response, 'data-workplaces-select-all')
        self.assertContains(response, 'data-workplace-id=', count=3)
        self.assertNotContains(response, 'data-column="logo"')
        self.assertContains(response, 'workplace-row__avatar', count=3)
        self.assertContains(response, 'Kod miejsca pracy')
        self.assertContains(response, 'Opis')
        self.assertContains(response, 'FIRST-01')
        self.assertContains(response, 'Miejsce pracy zespołu wdrożeniowego')
        self.assertContains(response, 'data-workplace-code="FIRST-01"')
        self.assertContains(response, 'data-workplace-description="Miejsce pracy zespołu wdrożeniowego"')
        self.assertContains(response, 'data-workplace-code="DRUGI-WORKPLACE"')
        self.assertContains(response, 'data-icon="briefcase-business"')
        self.assertContains(response, 'data-icon="hash"')
        self.assertContains(response, 'data-icon="align-left"')
        self.assertContains(response, 'data-workplaces-pagination')
        self.assertContains(response, 'data-workplaces-page-size-toggle')
        self.assertContains(response, 'data-workplaces-pagination-summary')
        self.assertContains(response, 'aria-label="Strony miejsc pracy"')
        self.assertNotContains(response, 'data-column="slug"')
        self.assertNotContains(response, 'data-workplace-slug=')
        self.assertContains(response, 'Pierwszy Workplace')
        self.assertContains(response, 'Drugi Workplace')
        self.assertContains(response, 'Nie moj Workplace')

    def test_workplace_create_renders_in_tasks_project_modal_shell(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('workplaces:workplaces'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-workplace-create-open')
        self.assertContains(response, 'tasks-modal tasks-project-modal tasks-project-create-modal tasks-issue-modal workplace-create-modal')
        self.assertContains(response, 'tasks-modal__form tasks-project-modal__form tasks-project-create-modal__form tasks-issue-modal__form workplace-create-modal__form')
        self.assertContains(response, 'Nowe miejsce pracy')
        self.assertContains(response, 'Utwórz miejsce pracy')
        self.assertContains(response, 'Nazwa miejsca pracy')
        self.assertContains(response, 'Kod miejsca pracy')
        self.assertContains(response, 'Zostaw puste, aby wygenerować unikalny kod z nazwy.')
        self.assertContains(response, 'Dodaj krótki opis miejsca pracy…')
        self.assertContains(response, 'placeholder="Nazwa miejsca pracy"')
        self.assertContains(response, 'class="tasks-issue-modal__crumbs"')
        self.assertContains(response, 'class="tasks-project-create-fields tasks-issue-fields workplace-modal__fields"')
        self.assertContains(response, 'class="workplace-modal__content"')
        self.assertContains(response, 'data-profile-photo-editor', count=3)
        self.assertContains(response, 'data-profile-photo-modal', count=3)
        self.assertContains(response, 'data-profile-photo-crop-input', count=3)
        self.assertContains(response, 'data-profile-photo-remove-input', count=3)
        self.assertContains(response, 'Edytuj logo miejsca pracy')
        self.assertContains(response, '>Dodaj</button>', count=1)
        self.assertContains(response, 'Po utworzeniu otworzymy panel zarządzania nowym Workspace.')
        self.assertNotContains(response, 'class="workplace-create-modal__cancel"')
        self.assertNotContains(response, 'workplaces-create-form--filterbar')

    def test_current_workplace_is_visually_and_semantically_distinguished(self):
        self.client.force_login(self.user)
        self._activate(self.second_workplace)

        response = self.client.get(reverse('workplaces:workplaces'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'role="row" aria-current="true"', count=1)
        self.assertContains(response, 'data-workplace-current-badge', count=1)
        self.assertContains(response, '>Bieżący</span>', count=1)
        self.assertContains(response, 'data-workplace-current-action disabled', count=1)
        self.assertContains(response, 'data-workplace-switch-action', count=1)
        self.assertContains(response, 'aria-label="Drugi Workplace — bieżący workspace"')
        self.assertContains(response, 'aria-label="Przełącz na Pierwszy Workplace"')

    def test_current_workplace_is_always_the_first_table_row(self):
        self.client.force_login(self.user)
        self._activate(self.first_workplace)

        response = self.client.get(reverse('workplaces:workplaces'))

        workplace_ids = list(response.context['workplaces'].values_list('id', flat=True))
        self.assertEqual(workplace_ids, [self.first_workplace.pk, self.second_workplace.pk])

        content = response.content.decode()
        self.assertLess(
            content.index('data-workplace-name="Pierwszy Workplace"'),
            content.index('data-workplace-name="Drugi Workplace"'),
        )

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
            'class="profile-avatar-icon" data-icon="briefcase"',
        )
        self.assertNotContains(response, 'data-icon="landmark"')

    def test_workplace_edit_renders_in_tasks_modal_shell(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('workplaces:workplaces'), {'workspace': self.first_workplace.pk, 'view': 'workspaces'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-workplace-edit-modal data-initial-tab=', count=1)
        self.assertContains(response, 'data-workplace-edit-open="workplace-edit-modal-')
        self.assertContains(response, 'tasks-modal app-modal-panel tasks-project-modal tasks-project-edit-modal tasks-issue-modal workplace-edit-modal')
        self.assertContains(response, 'tasks-modal__form tasks-project-modal__form tasks-project-edit-modal__form tasks-issue-modal__form workplace-edit-modal__form')
        self.assertContains(response, 'Edytuj miejsce pracy')
        self.assertContains(response, 'name="code" value="FIRST-01"')
        self.assertContains(response, 'name="description"')
        self.assertContains(response, 'class="tasks-project-create-fields tasks-issue-fields workplace-modal__fields workplace-edit-modal__fields"')
        self.assertContains(response, 'name="workplace_photo_crop"', count=2)
        self.assertContains(response, 'data-profile-photo-save', count=2)
        self.assertContains(response, 'data-profile-photo-change', count=2)
        self.assertContains(response, 'data-profile-photo-remove>Usuń</button>', count=2)
        self.assertNotContains(response, '<span>Slug</span>', html=True)
        self.assertNotContains(response, 'class="workplace-settings workplace-settings--inspector"')
        self.assertNotContains(response, 'class="workplace-settings__form"')

    def test_sidebar_footer_button_stays_fixed_and_header_uses_workplace_photo(self):
        self.first_workplace.workplace_photo = 'workplace_photos/moje-miejsce.webp'
        self.first_workplace.save(update_fields=['workplace_photo'])
        self.client.force_login(self.user)
        self._activate(self.first_workplace)

        response = self.client.get(reverse('tasks:tasks'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="sidebar-workspace-manage"')
        self.assertContains(response, 'data-icon="briefcase"')
        self.assertNotContains(response, 'sidebar-workplace__avatar')
        self.assertContains(response, 'sidebar-workspace-avatar')
        self.assertContains(response, '/media/workplace_photos/moje-miejsce.webp', count=2)

    def test_sidebar_header_lists_workspaces_for_quick_switching(self):
        self.client.force_login(self.user)
        self._activate(self.first_workplace)

        response = self.client.get(reverse('tasks:tasks'))
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-sidebar-workspace-switcher')
        self.assertContains(response, 'data-sidebar-workspace-toggle')
        self.assertContains(response, 'id="sidebar-workspace-menu"')
        self.assertContains(response, 'data-sidebar-workspace-search')
        self.assertContains(response, 'id="sidebar-workspace-search-input"')
        self.assertContains(response, 'placeholder="Szukaj Workspace"')
        self.assertContains(response, 'data-sidebar-workspace-item', count=2)
        self.assertContains(response, reverse('workplaces:switch', args=[self.first_workplace.pk]))
        self.assertContains(response, reverse('workplaces:switch', args=[self.second_workplace.pk]))
        self.assertContains(response, 'class="sidebar-workspace-option is-active"')
        self.assertLess(content.index('data-sidebar-workspace-search'), content.index('data-sidebar-workspace-item'))
        self.assertLess(content.index('data-sidebar-workspace-switcher'), content.index('class="sidebar-navigation"'))

    def test_sidebar_favorite_can_be_added_and_removed_without_page_reload(self):
        self.client.force_login(self.user)
        self._activate(self.first_workplace)
        endpoint = reverse('workplaces:toggle-sidebar-favorite', args=[self.first_workplace.pk])

        response = self.client.post(
            endpoint,
            {
                'item_key': 'tasks-my',
                'favorite_action': 'add',
                'next': reverse('tasks:tasks'),
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['is_favorite'])
        self.assertIn('data-sidebar-favorite-item="tasks-my"', response.json()['html'])
        self.assertTrue(SidebarFavorite.objects.filter(
            user=self.user,
            workplace=self.first_workplace,
            item_key='tasks-my',
        ).exists())

        response = self.client.post(
            endpoint,
            {
                'item_key': 'tasks-my',
                'favorite_action': 'remove',
                'next': reverse('tasks:tasks'),
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['is_favorite'])
        self.assertIn('data-sidebar-favorite-item="dashboard"', response.json()['html'])
        self.assertFalse(SidebarFavorite.objects.filter(
            user=self.user,
            workplace=self.first_workplace,
            item_key='tasks-my',
        ).exists())

    def test_sidebar_favorite_is_idempotent_and_scoped_to_workplace(self):
        self.client.force_login(self.user)
        endpoint = reverse('workplaces:toggle-sidebar-favorite', args=[self.first_workplace.pk])
        payload = {
            'item_key': 'calendar',
            'favorite_action': 'add',
            'next': reverse('planner:index'),
        }

        self.client.post(endpoint, payload)
        self.client.post(endpoint, payload)

        self.assertEqual(SidebarFavorite.objects.filter(
            user=self.user,
            workplace=self.first_workplace,
            item_key='calendar',
        ).count(), 1)

        self._activate(self.second_workplace)
        response = self.client.get(reverse('tasks:tasks'))
        self.assertNotContains(response, 'data-sidebar-favorite-item="calendar"')

    def test_sidebar_favorites_can_be_reordered_and_keep_the_new_order(self):
        SidebarFavorite.objects.create(
            user=self.user,
            workplace=self.first_workplace,
            item_key='tasks-all',
            position=1,
        )
        SidebarFavorite.objects.create(
            user=self.user,
            workplace=self.first_workplace,
            item_key='contacts-companies',
            position=2,
        )
        self.client.force_login(self.user)
        self._activate(self.first_workplace)
        endpoint = reverse('workplaces:reorder-sidebar-favorites', args=[self.first_workplace.pk])

        response = self.client.post(
            endpoint,
            {'item_order': json.dumps(['contacts-companies', 'dashboard', 'tasks-all'])},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(
                SidebarFavorite.objects.filter(user=self.user, workplace=self.first_workplace)
                .values_list('item_key', flat=True)
            ),
            ['contacts-companies', 'dashboard', 'tasks-all'],
        )
        page = self.client.get(reverse('tasks:tasks')).content.decode()
        self.assertLess(
            page.index('data-sidebar-favorite-item="contacts-companies"'),
            page.index('data-sidebar-favorite-item="dashboard"'),
        )
        self.assertLess(
            page.index('data-sidebar-favorite-item="dashboard"'),
            page.index('data-sidebar-favorite-item="tasks-all"'),
        )

    def test_sidebar_favorite_reorder_requires_the_complete_unique_item_set(self):
        SidebarFavorite.objects.create(
            user=self.user,
            workplace=self.first_workplace,
            item_key='tasks-all',
            position=1,
        )
        self.client.force_login(self.user)
        endpoint = reverse('workplaces:reorder-sidebar-favorites', args=[self.first_workplace.pk])

        missing_response = self.client.post(
            endpoint,
            {'item_order': json.dumps(['dashboard'])},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        duplicate_response = self.client.post(
            endpoint,
            {'item_order': json.dumps(['dashboard', 'dashboard'])},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(missing_response.status_code, 400)
        self.assertEqual(duplicate_response.status_code, 400)
        self.assertEqual(
            list(
                SidebarFavorite.objects.filter(user=self.user, workplace=self.first_workplace)
                .values_list('item_key', flat=True)
            ),
            ['dashboard', 'tasks-all'],
        )

    def test_new_sidebar_favorite_is_appended_after_reordered_items(self):
        SidebarFavorite.objects.create(
            user=self.user,
            workplace=self.first_workplace,
            item_key='tasks-all',
            position=1,
        )
        self.client.force_login(self.user)
        reorder_endpoint = reverse('workplaces:reorder-sidebar-favorites', args=[self.first_workplace.pk])
        toggle_endpoint = reverse('workplaces:toggle-sidebar-favorite', args=[self.first_workplace.pk])
        self.client.post(
            reorder_endpoint,
            {'item_order': json.dumps(['tasks-all', 'dashboard'])},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        response = self.client.post(
            toggle_endpoint,
            {'item_key': 'calendar', 'favorite_action': 'add'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(
                SidebarFavorite.objects.filter(user=self.user, workplace=self.first_workplace)
                .values_list('item_key', flat=True)
            ),
            ['tasks-all', 'dashboard', 'calendar'],
        )

    def test_removed_people_search_favorite_is_not_rendered(self):
        SidebarFavorite.objects.create(
            user=self.user,
            workplace=self.first_workplace,
            item_key='contacts-people',
        )
        self.client.force_login(self.user)
        self._activate(self.first_workplace)

        response = self.client.get(reverse('tasks:tasks'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'data-sidebar-favorite-item="contacts-people"')
        self.assertNotContains(response, 'data-sidebar-source-item="contacts-people"')
        self.assertNotContains(response, '>Szukaj osób</span>')

    def test_sidebar_favorite_rejects_unknown_item_and_another_users_workplace(self):
        self.client.force_login(self.user)
        own_endpoint = reverse('workplaces:toggle-sidebar-favorite', args=[self.first_workplace.pk])

        invalid_response = self.client.post(
            own_endpoint,
            {'item_key': 'admin-secret', 'favorite_action': 'add'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(invalid_response.status_code, 400)
        self.assertFalse(SidebarFavorite.objects.filter(
            user=self.user,
            item_key='admin-secret',
        ).exists())

        other_user = get_user_model().objects.create_user(
            username='@favorite.other',
            email='favorite-other@example.com',
            password='secret',
            first_name='Other',
            last_name='Owner',
        )
        other_workplace = create_workplace_for_user(other_user, 'Cudzy Workspace')
        other_endpoint = reverse('workplaces:toggle-sidebar-favorite', args=[other_workplace.pk])

        forbidden_response = self.client.post(
            other_endpoint,
            {'item_key': 'calendar', 'favorite_action': 'add'},
        )

        self.assertEqual(forbidden_response.status_code, 404)
        self.assertFalse(SidebarFavorite.objects.filter(
            user=self.user,
            item_key='admin-secret',
        ).exists())

    def test_sidebar_renders_draggable_favorites_with_remove_dropzone(self):
        SidebarFavorite.objects.create(
            user=self.user,
            workplace=self.first_workplace,
            item_key='tags',
        )
        self.client.force_login(self.user)
        self._activate(self.first_workplace)

        response = self.client.get(reverse('tasks:tasks') + '?view=tags')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-sidebar-favorite-item="dashboard"')
        self.assertContains(response, 'data-sidebar-favorite-item="tags"')
        self.assertContains(response, 'data-sidebar-source-item="tags"')
        self.assertContains(response, 'data-sidebar-favorites-dropzone')
        self.assertContains(response, 'data-sidebar-favorites-reorder-form')
        self.assertContains(response, 'data-sidebar-favorites-order')
        self.assertContains(response, 'data-sidebar-favorites-remove-dropzone')
        self.assertContains(response, 'Usuń z Favorites')
        self.assertNotContains(response, 'data-sidebar-workspace-dropzone')
        self.assertContains(response, 'data-sidebar-favorite-item="tags" draggable="true"')
        self.assertNotContains(response, 'data-sidebar-favorite-drag-handle')
        self.assertNotContains(response, 'data-icon="grip-vertical"')
        self.assertContains(response, 'data-sidebar-source-item="tags" draggable="true"')
        self.assertNotContains(response, 'data-sidebar-favorite-remove')
        self.assertContains(
            response,
            'class="sidebar-favorite-form sidebar-favorite-remove-form u-sr-only"',
            count=2,
        )
        self.assertContains(response, '>Usuń Tagi z Favorites</button>')
        self.assertNotContains(response, 'sidebar-pinnable-row')
        self.assertNotContains(response, 'sidebar-favorite-toggle')
        self.assertNotContains(response, 'data-icon="star"')
        self.assertGreaterEqual(
            response.content.decode().count(f'/workplaces/{self.first_workplace.slug}/tasks/?view=tags'),
            3,
        )

    def test_new_workplaces_have_dashboard_in_favorites_by_default(self):
        self.assertTrue(SidebarFavorite.objects.filter(
            user=self.user,
            workplace=self.first_workplace,
            item_key='dashboard',
        ).exists())
        self.assertTrue(SidebarFavorite.objects.filter(
            user=self.user,
            workplace=self.second_workplace,
            item_key='dashboard',
        ).exists())

        self.client.force_login(self.user)
        self._activate(self.first_workplace)
        response = self.client.get(reverse('tasks:tasks'))

        self.assertContains(response, 'data-sidebar-favorite-item="dashboard"')
        self.assertContains(response, 'data-sidebar-source-item="dashboard" draggable="true"')
        self.assertContains(response, '>Dashboard</span>', count=2)

    def test_sidebar_workspace_management_is_in_header_and_footer_keeps_sticker_and_settings(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('tasks:tasks'))
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="sidebar-header"')
        self.assertContains(response, 'data-sidebar-workspace-switcher')
        self.assertContains(response, 'data-sidebar-workspace-toggle')
        self.assertNotContains(response, 'class="nav-separator"')
        self.assertLess(content.index('class="sidebar-header"'), content.index('class="sidebar-workspace-manage"'))
        self.assertLess(content.index('class="sidebar-workspace-manage"'), content.index('data-sticky-note-toggle'))
        self.assertLess(content.index('class="sidebar-workspace-manage"'), content.index('aria-label="Ustawienia Ancore"'))

    def test_sidebar_workspace_management_link_has_settings_icon(self):
        self.client.force_login(self.user)
        self._activate(self.first_workplace)

        response = self.client.get(reverse('tasks:tasks'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="sidebar-workspace-manage"')
        self.assertContains(
            response,
            '<i data-icon="settings-2" aria-hidden="true"></i>',
            html=True,
        )

    def test_base_layout_does_not_render_workplace_identity_strip(self):
        self.client.force_login(self.user)
        self._activate(self.second_workplace)

        response = self.client.get(reverse('tasks:tasks'))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'class="app-topbar"')
        self.assertNotContains(response, 'class="secondary-menu-workplace"')
        self.assertNotContains(response, 'title="Bieżące miejsce pracy: Drugi Workplace"')

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

    def test_create_workplace_opens_management_without_switching(self):
        self.client.force_login(self.user)
        self._activate(self.first_workplace)

        response = self.client.post(reverse('workplaces:workplaces'), {'name': 'Nowy Workplace'})
        workplace = type(self.first_workplace).objects.get(owner=self.user, name='Nowy Workplace')

        self.assertRedirects(
            response,
            workplace_management_url(workplace, 'workspaces'),
            fetch_redirect_response=False,
        )
        self.assertEqual(self.client.session['active_workplace_id'], self.first_workplace.pk)
        membership = workplace.memberships.get(user=self.user)
        self.assertEqual(membership.role, WorkplaceMembership.Role.OWNER)

    def test_create_workplace_normalizes_whitespace_in_name(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('workplaces:workplaces'), {'name': '  Zespół   wdrożeniowy  '})

        workplace = type(self.first_workplace).objects.get(owner=self.user, name='Zespół wdrożeniowy')
        self.assertRedirects(
            response,
            workplace_management_url(workplace, 'workspaces'),
            fetch_redirect_response=False,
        )

    def test_create_workplace_saves_description_and_normalized_code(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('workplaces:workplaces'), {
            'name': 'Zespół produktowy',
            'code': '  product-01  ',
            'description': '  Rozwój głównego produktu  ',
        })

        workplace = type(self.first_workplace).objects.get(owner=self.user, name='Zespół produktowy')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(workplace.code, 'PRODUCT-01')
        self.assertEqual(workplace.description, 'Rozwój głównego produktu')

    def test_create_workplace_generates_code_from_name_when_code_is_empty(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('workplaces:workplaces'), {
            'name': 'Zespół operacyjny 01',
            'code': '',
        })

        workplace = type(self.first_workplace).objects.get(owner=self.user, name='Zespół operacyjny 01')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(workplace.code, 'ZESPOL-OPERACYJNY-01')

    def test_generated_workplace_code_gets_unique_numeric_suffix(self):
        first = create_workplace_for_user(self.user, 'Zespół A')
        second = create_workplace_for_user(self.user, 'Zespol A')

        self.assertEqual(first.code, 'ZESPOL-A')
        self.assertEqual(second.code, 'ZESPOL-A-2')

    def test_workplace_code_migration_backfills_existing_empty_code(self):
        type(self.second_workplace).objects.filter(pk=self.second_workplace.pk).update(code='')
        migration = import_module('workplaces.migrations.0005_backfill_workplace_codes')

        migration.backfill_workplace_codes(apps, None)

        self.second_workplace.refresh_from_db()
        self.assertEqual(self.second_workplace.code, 'DRUGI-WORKPLACE')

    def test_create_workplace_accepts_valid_logo(self):
        self.client.force_login(self.user)
        logo = SimpleUploadedFile(
            'logo.png',
            b'\x89PNG\r\n\x1a\n' + (b'0' * 32),
            content_type='image/png',
        )

        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            response = self.client.post(
                reverse('workplaces:workplaces'),
                {'name': 'Zespół z logo', 'workplace_photo': logo},
            )

            workplace = type(self.first_workplace).objects.get(owner=self.user, name='Zespół z logo')
            self.assertEqual(response.status_code, 302)
            self.assertTrue(workplace.workplace_photo.name.startswith('workplace_photos/logo'))

    def test_create_workplace_saves_cropped_logo_from_profile_photo_editor(self):
        self.client.force_login(self.user)
        image_content = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII='
        )
        crop_data = f'data:image/png;base64,{base64.b64encode(image_content).decode()}'

        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            response = self.client.post(reverse('workplaces:workplaces'), {
                'name': 'Zespół z kadrowanym logo',
                'workplace_photo_crop': crop_data,
            })

            workplace = type(self.first_workplace).objects.get(
                owner=self.user,
                name='Zespół z kadrowanym logo',
            )
            self.assertEqual(response.status_code, 302)
            self.assertTrue(workplace.workplace_photo.name.startswith('workplace_photos/workplace_'))
            with open(workplace.workplace_photo.path, 'rb') as photo_file:
                self.assertEqual(photo_file.read(), image_content)

    def test_create_workplace_rejects_file_with_invalid_image_content(self):
        self.client.force_login(self.user)
        fake_logo = SimpleUploadedFile('logo.png', b'not-an-image', content_type='image/png')

        response = self.client.post(
            reverse('workplaces:workplaces'),
            {'name': 'Nie powinno powstać', 'workplace_photo': fake_logo},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'workplace-create-modal is-open')
        self.assertContains(response, 'Plik obrazu ma nieprawidłową zawartość.')
        self.assertFalse(
            type(self.first_workplace).objects.filter(owner=self.user, name='Nie powinno powstać').exists()
        )

    def test_duplicate_create_reopens_workplace_create_modal(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('workplaces:workplaces'), {'name': self.first_workplace.name})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'workplace-create-modal is-open')
        self.assertContains(response, 'aria-hidden="false" data-workplace-create-modal')
        self.assertContains(response, 'Masz już miejsce pracy o takiej nazwie.')

    def test_duplicate_create_is_case_insensitive(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('workplaces:workplaces'),
            {'name': self.first_workplace.name.swapcase()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Masz już miejsce pracy o takiej nazwie.')
        self.assertEqual(type(self.first_workplace).objects.filter(owner=self.user).count(), 2)

    def test_duplicate_workplace_code_is_case_insensitive(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('workplaces:workplaces'), {
            'name': 'Nowa nazwa',
            'code': 'first-01',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Masz już miejsce pracy o takim kodzie.')
        self.assertEqual(type(self.first_workplace).objects.filter(owner=self.user).count(), 2)

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

        response = self.client.get(scoped_workplace_app_path(self.second_workplace, 'tasks'), {'tab': 'public'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'href="{scoped_workplace_app_path(self.second_workplace, "tasks")}?view=all-tasks"')
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

        self.assertRedirects(response, workplace_management_url(self.first_workplace))
        self.first_workplace.refresh_from_db()
        self.assertEqual(self.first_workplace.name, 'Nowa nazwa')

    def test_owner_can_update_workplace_description_and_code(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('workplaces:update', args=[self.first_workplace.pk]),
            {
                'name': self.first_workplace.name,
                'code': '  delivery-02 ',
                'description': '  Obsługa wdrożeń klientów  ',
            },
        )

        self.assertRedirects(response, workplace_management_url(self.first_workplace))
        self.first_workplace.refresh_from_db()
        self.assertEqual(self.first_workplace.code, 'DELIVERY-02')
        self.assertEqual(self.first_workplace.description, 'Obsługa wdrożeń klientów')

    def test_owner_can_replace_and_remove_logo_with_profile_photo_editor_fields(self):
        self.client.force_login(self.user)
        image_content = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII='
        )
        crop_data = f'data:image/png;base64,{base64.b64encode(image_content).decode()}'

        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            response = self.client.post(
                reverse('workplaces:update', args=[self.first_workplace.pk]),
                {
                    'name': self.first_workplace.name,
                    'code': self.first_workplace.code,
                    'description': self.first_workplace.description,
                    'workplace_photo_crop': crop_data,
                },
            )

            self.assertRedirects(response, workplace_management_url(self.first_workplace))
            self.first_workplace.refresh_from_db()
            self.assertTrue(self.first_workplace.workplace_photo.name.startswith('workplace_photos/workplace_'))

            response = self.client.get(reverse('workplaces:workplaces'), {'workspace': self.first_workplace.pk, 'tab': 'main'})
            self.assertContains(response, f'data-profile-photo-url="{self.first_workplace.workplace_photo.url}"')

            response = self.client.post(
                reverse('workplaces:update', args=[self.first_workplace.pk]),
                {
                    'name': self.first_workplace.name,
                    'code': self.first_workplace.code,
                    'description': self.first_workplace.description,
                    'workplace_photo_remove': '1',
                },
            )

            self.assertRedirects(response, workplace_management_url(self.first_workplace))
            self.first_workplace.refresh_from_db()
            self.assertFalse(self.first_workplace.workplace_photo)

    def test_owner_can_clear_workplace_code_to_generate_it_again(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('workplaces:update', args=[self.first_workplace.pk]),
            {
                'name': self.first_workplace.name,
                'code': '',
                'description': self.first_workplace.description,
            },
        )

        self.assertRedirects(response, workplace_management_url(self.first_workplace))
        self.first_workplace.refresh_from_db()
        self.assertEqual(self.first_workplace.code, 'PIERWSZY-WORKPLACE')

    def test_owner_cannot_rename_workplace_to_duplicate_name(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('workplaces:update', args=[self.first_workplace.pk]),
            {'name': self.second_workplace.name},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['edit_form'].errors)
        self.assertTrue(response.context['workplace_edit_modal_open'])
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
