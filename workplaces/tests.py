import base64
import tempfile
from importlib import import_module

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
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
        self.assertContains(response, 'Kod miejsca pracy')
        self.assertContains(response, 'Opis')
        self.assertContains(response, 'FIRST-01')
        self.assertContains(response, 'Miejsce pracy zespołu wdrożeniowego')
        self.assertContains(response, 'data-workplace-code="FIRST-01"')
        self.assertContains(response, 'data-workplace-description="Miejsce pracy zespołu wdrożeniowego"')
        self.assertContains(response, 'data-workplace-code="DRUGI-WORKPLACE"')
        self.assertContains(response, 'data-lucide="briefcase-business"')
        self.assertContains(response, 'data-lucide="hash"')
        self.assertContains(response, 'data-lucide="align-left"')
        self.assertContains(response, 'data-workplaces-pagination')
        self.assertContains(response, 'data-workplaces-page-size-toggle')
        self.assertContains(response, 'data-workplaces-pagination-summary')
        self.assertContains(response, 'aria-label="Strony miejsc pracy"')
        self.assertNotContains(response, 'data-column="slug"')
        self.assertNotContains(response, 'data-workplace-slug=')
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
        self.assertContains(response, 'Po utworzeniu przełączymy Cię do nowego miejsca pracy.')
        self.assertNotContains(response, 'class="workplace-create-modal__cancel"')
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
        self.assertContains(response, 'name="code" value="FIRST-01"')
        self.assertContains(response, 'name="description"')
        self.assertContains(response, 'class="tasks-project-create-fields tasks-issue-fields workplace-modal__fields workplace-edit-modal__fields"')
        self.assertContains(response, 'name="workplace_photo_crop"', count=3)
        self.assertContains(response, 'data-profile-photo-save', count=3)
        self.assertContains(response, 'data-profile-photo-change', count=3)
        self.assertContains(response, 'data-profile-photo-remove>Usuń</button>', count=3)
        self.assertNotContains(response, '<span>Slug</span>', html=True)
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

    def test_sidebar_displays_workplace_below_notes_and_above_settings_without_separator(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('tasks:tasks'))
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="sidebar-header"')
        self.assertContains(response, 'href="/" class="logo" aria-label="Ancore"')
        self.assertContains(response, '/static/img/logo-ancore.png')
        self.assertNotContains(response, 'class="nav-separator"')
        self.assertLess(content.index('class="sidebar-header"'), content.index('class="nav-link nav-link--workplace '))
        self.assertLess(content.index('data-sticky-note-toggle'), content.index('class="nav-link nav-link--workplace '))
        self.assertLess(content.index('class="nav-link nav-link--workplace '), content.index('aria-label="Ustawienia Ancore"'))

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

    def test_create_workplace_redirects_to_scoped_tasks_url(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('workplaces:workplaces'), {'name': 'Nowy Workplace'})
        workplace = type(self.first_workplace).objects.get(owner=self.user, name='Nowy Workplace')

        self.assertRedirects(
            response,
            scoped_workplace_app_path(workplace, 'tasks'),
            fetch_redirect_response=False,
        )
        self.assertEqual(self.client.session['active_workplace_id'], workplace.pk)
        membership = workplace.memberships.get(user=self.user)
        self.assertEqual(membership.role, WorkplaceMembership.Role.OWNER)

    def test_create_workplace_normalizes_whitespace_in_name(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('workplaces:workplaces'), {'name': '  Zespół   wdrożeniowy  '})

        workplace = type(self.first_workplace).objects.get(owner=self.user, name='Zespół wdrożeniowy')
        self.assertRedirects(
            response,
            scoped_workplace_app_path(workplace, 'tasks'),
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

        self.assertRedirects(response, reverse('workplaces:workplaces'))
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

            self.assertRedirects(response, reverse('workplaces:workplaces'))
            self.first_workplace.refresh_from_db()
            self.assertTrue(self.first_workplace.workplace_photo.name.startswith('workplace_photos/workplace_'))

            response = self.client.get(reverse('workplaces:workplaces'))
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

            self.assertRedirects(response, reverse('workplaces:workplaces'))
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

        self.assertRedirects(response, reverse('workplaces:workplaces'))
        self.first_workplace.refresh_from_db()
        self.assertEqual(self.first_workplace.code, 'PIERWSZY-WORKPLACE')

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
