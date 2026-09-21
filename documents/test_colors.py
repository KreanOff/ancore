from django.contrib.auth import get_user_model
from django.test import TestCase

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import Document, DocumentLibrary, Folder


class IconColorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='colors', email='colors@example.test')
        cls.other = get_user_model().objects.create_user(username='other-colors', email='other-colors@example.test')
        cls.workspace = create_workplace_for_user(cls.user, 'Kolory')
        cls.outside = create_workplace_for_user(cls.user, 'Inny Workspace')
        cls.library = DocumentLibrary.objects.create(owner=cls.user, workplace=cls.workspace, name='Dysk')
        cls.folder = Folder.objects.create(owner=cls.user, workplace=cls.workspace, library=cls.library, name='Folder')

    def setUp(self):
        self.client.force_login(self.user)
        self.client.get(scoped_workplace_app_path(self.workspace, 'documents'))

    def cases(self):
        return [(self.library, 'documents', 'libraries'), (self.folder, 'documents', 'folders')]

    def test_create_and_edit_colors_in_normal_and_scoped_routes(self):
        for item, app, kind in self.cases():
            for base in (f'/{app}/', scoped_workplace_app_path(self.workspace, app)):
                with self.subTest(model=item._meta.model_name, base=base):
                    query = f'?library={self.library.pk}' if item == self.folder else ''
                    name = f'Nowy {app} {base} {kind}'.replace('/', '-')
                    response = self.client.post(f'{base}{kind}/create/{query}', {'name': name, 'color': '#A123BC'})
                    self.assertEqual(response.status_code, 302)
                    created = type(item).objects.get(name=name)
                    self.assertEqual(created.color, '#a123bc')
                    self.assertEqual((created.owner_id, created.workplace_id), (self.user.pk, self.workspace.pk))
                    url = f'{base}{kind}/{created.pk}/edit/'
                    response = self.client.post(url, {'name': name, 'color': '#247C53'}, headers={'X-Document-Modal': 'true'})
                    self.assertIn('redirect_url', response.json())
                    created.refresh_from_db()
                    self.assertEqual(created.color, '#247c53')
                    self.assertContains(self.client.get(url, headers={'X-Document-Modal': 'true'}, follow=True), 'value="#247c53"')

    def test_invalid_colors_do_not_save_and_invalid_name_keeps_selected_color(self):
        for item, app, kind in self.cases():
            url = f'{scoped_workplace_app_path(self.workspace, app)}{kind}/{item.pk}/edit/'
            original = item.color
            for invalid in ('red', '#abc', '#12345g', '#123456;fill:red', '#123456\n!'):
                with self.subTest(model=item._meta.model_name, color=invalid):
                    response = self.client.post(url, {'name': item.name, 'color': invalid}, headers={'X-Document-Modal': 'true'})
                    self.assertIn('color', response.context['modal']['form'].errors)
                    item.refresh_from_db()
                    self.assertEqual(item.color, original)
            response = self.client.post(url, {'name': '', 'color': '#123ABC'}, headers={'X-Document-Modal': 'true'})
            self.assertIn('name', response.context['modal']['form'].errors)
            self.assertContains(response, 'value="#123ABC"')
            self.assertContains(response, '--documents-icon-color: #123abc;')
            item.refresh_from_db()
            self.assertEqual(item.color, original)

    def test_missing_color_preserves_saved_color_and_default_can_be_restored(self):
        for item, app, kind in self.cases():
            url = f'{scoped_workplace_app_path(self.workspace, app)}{kind}/{item.pk}/edit/'
            self.client.post(url, {'name': item.name, 'color': '#112233'})
            self.client.post(url, {'name': item.name})
            item.refresh_from_db()
            self.assertEqual(item.color, '#112233')
            default = item._meta.get_field('color').get_default()
            self.client.post(url, {'name': item.name, 'color': default})
            item.refresh_from_db()
            self.assertEqual(item.color, default)

    def test_color_is_rendered_in_lists_tiles_and_drive_sidebar(self):
        self.library.color = '#123abc'
        self.library.save()
        self.folder.color = '#247c53'
        self.folder.save()
        for display in ('list', 'grid'):
            for scoped in (False, True):
                drive = scoped_workplace_app_path(self.workspace, 'documents') if scoped else '/documents/'
                with self.subTest(display=display, scoped=scoped):
                    self.assertContains(self.client.get(drive, {'display': display}, follow=True), '--documents-icon-color: #123abc;')
                    response = self.client.get(drive, {'library': self.library.pk, 'display': display}, follow=True)
                    self.assertContains(response, '--documents-icon-color: #123abc;')
                    self.assertContains(response, '--documents-icon-color: #247c53;')

    def test_folder_color_survives_transition_from_empty_to_filled(self):
        for folder, model, app in ((self.folder, Document, 'documents'),):
            folder.color = '#247c53'
            folder.save()
            base = scoped_workplace_app_path(self.workspace, app)
            query = {'library': self.library.pk} if app == 'documents' else {}
            response = self.client.get(base, query)
            self.assertContains(response, 'documents-folder-icon--empty')
            kwargs = {'library': self.library, 'filename': 'test.txt'} if app == 'documents' else {}
            model.objects.create(owner=self.user, workplace=self.workspace, folder=folder, title='Test', **kwargs)
            response = self.client.get(base, query)
            self.assertContains(response, 'documents-folder-icon--filled')
            self.assertContains(response, '--documents-icon-color: #247c53;')

    def test_other_workspace_and_membership_cannot_change_colors(self):
        WorkplaceMembership.objects.create(workplace=self.workspace, user=self.other, role=WorkplaceMembership.Role.ADMIN)
        for item, app, kind in self.cases():
            original = item.color
            foreign_url = f'{scoped_workplace_app_path(self.outside, app)}{kind}/{item.pk}/edit/'
            self.assertEqual(self.client.post(foreign_url, {'name': item.name, 'color': '#112233'}).status_code, 404)
            self.client.force_login(self.other)
            base = scoped_workplace_app_path(self.workspace, app)
            self.assertEqual(self.client.post(f'{base}{kind}/{item.pk}/edit/', {'name': item.name, 'color': '#112233'}).status_code, 302)
            response = self.client.post(f'/{app}/{kind}/{item.pk}/edit/', {'name': item.name, 'color': '#112233'}, follow=True)
            self.assertEqual(response.status_code, 404)
            item.refresh_from_db()
            self.assertEqual(item.color, original)
            self.client.force_login(self.user)
