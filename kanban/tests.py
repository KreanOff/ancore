import json

from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from .models import Workspace, KanbanBoard, KanbanColumn, KanbanCard, KanbanAttachment
from .utils import board_index_url

User = get_user_model()

class KanbanWorkspaceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='password123')
        self.client.login(email='test@example.com', password='password123')

    def test_default_workspace_created_on_index_access(self):
        # Access index view
        response = self.client.get(reverse('kanban:index'))
        self.assertEqual(response.status_code, 200)
        
        # Verify default workspace was created
        workspaces = Workspace.objects.filter(user=self.user)
        self.assertEqual(workspaces.count(), 1)
        self.assertEqual(workspaces.first().name, "Moja Przestrzeń")

        # Verify a default board was created in that workspace
        boards = KanbanBoard.objects.filter(workspace=workspaces.first())
        self.assertEqual(boards.count(), 1)
        self.assertEqual(boards.first().name, "Główna Tablica")

    def test_workspaces_page(self):
        response = self.client.get(reverse('kanban:workspaces'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Twoje przestrzenie robocze')

    def test_create_workspace(self):
        response = self.client.post(reverse('kanban:create_workspace'), {'name': 'Nowy Projekt'})
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('kanban:workspaces'))
        
        workspace = Workspace.objects.filter(name='Nowy Projekt', user=self.user).first()
        self.assertIsNotNone(workspace)
        
        # Verify a default board is created for the new workspace
        self.assertTrue(KanbanBoard.objects.filter(workspace=workspace, name="Główna Tablica").exists())

    def test_rename_workspace(self):
        workspace = Workspace.objects.create(name="Stara Nazwa", user=self.user)
        response = self.client.post(
            reverse('kanban:rename_workspace', args=[workspace.id]),
            data='{"name": "Nowa Nazwa"}',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        workspace.refresh_from_db()
        self.assertEqual(workspace.name, "Nowa Nazwa")

    def test_delete_workspace(self):
        workspace = Workspace.objects.create(name="Do Usunięcia", user=self.user)
        remaining = Workspace.objects.create(name="Inny", user=self.user)

        response = self.client.post(reverse('kanban:delete_workspace', args=[workspace.id]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, board_index_url(workspace_id=remaining.id))
        self.assertFalse(Workspace.objects.filter(id=workspace.id).exists())

    def test_create_board(self):
        workspace = Workspace.objects.create(name="Szkicownik", user=self.user)
        response = self.client.post(reverse('kanban:create_board'), {
            'workspace_id': workspace.id,
            'name': 'Baza Danych'
        })
        self.assertEqual(response.status_code, 302)
        
        board = KanbanBoard.objects.filter(name='Baza Danych', workspace=workspace, user=self.user).first()
        self.assertIsNotNone(board)
        # Verify default columns were created
        self.assertEqual(board.columns.count(), 3)

    def test_rename_board(self):
        workspace = Workspace.objects.create(name="Szkicownik", user=self.user)
        board = KanbanBoard.objects.create(name="Stara Tablica", workspace=workspace, user=self.user)
        
        response = self.client.post(
            reverse('kanban:rename_board', args=[board.id]),
            data='{"name": "Nowa Tablica"}',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        board.refresh_from_db()
        self.assertEqual(board.name, "Nowa Tablica")

    def test_update_board_background(self):
        workspace = Workspace.objects.create(name="Szkicownik", user=self.user)
        board = KanbanBoard.objects.create(name="Tablica", workspace=workspace, user=self.user, background='ocean')

        response = self.client.post(
            reverse('kanban:update_board_background', args=[board.id]),
            data='{"background": "forest"}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        board.refresh_from_db()
        self.assertEqual(board.background, 'forest')
        self.assertEqual(board.background_source, 'preset')

        bad = self.client.post(
            reverse('kanban:update_board_background', args=[board.id]),
            data='{"background": "invalid"}',
            content_type='application/json',
        )
        self.assertEqual(bad.status_code, 400)

    def test_update_board_background_url(self):
        workspace = Workspace.objects.create(name="Szkicownik", user=self.user)
        board = KanbanBoard.objects.create(name="Tablica", workspace=workspace, user=self.user)

        response = self.client.post(
            reverse('kanban:update_board_background', args=[board.id]),
            data='{"background_url": "https://example.com/wall.jpg"}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        board.refresh_from_db()
        self.assertEqual(board.background_url, 'https://example.com/wall.jpg')
        self.assertEqual(board.background_source, 'url')
        self.assertIn('example.com', board.background_style)

        invalid = self.client.post(
            reverse('kanban:update_board_background', args=[board.id]),
            data='{"background_url": "not-a-url"}',
            content_type='application/json',
        )
        self.assertEqual(invalid.status_code, 400)

    def test_upload_board_background(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        workspace = Workspace.objects.create(name="Szkicownik", user=self.user)
        board = KanbanBoard.objects.create(name="Tablica", workspace=workspace, user=self.user)
        image = SimpleUploadedFile(
            'tapeta.jpg',
            b'\xff\xd8\xff\xe0' + b'\x00' * 100,
            content_type='image/jpeg',
        )

        response = self.client.post(
            reverse('kanban:upload_board_background', args=[board.id]),
            {'background_image': image},
        )
        self.assertEqual(response.status_code, 200)
        board.refresh_from_db()
        self.assertTrue(board.background_image)
        self.assertEqual(board.background_source, 'image')

        response_preset = self.client.post(
            reverse('kanban:update_board_background', args=[board.id]),
            data='{"background": "neutral"}',
            content_type='application/json',
        )
        self.assertEqual(response_preset.status_code, 200)
        board.refresh_from_db()
        self.assertFalse(board.background_image)
        self.assertEqual(board.background_url, '')

    def test_delete_board(self):
        workspace = Workspace.objects.create(name="Szkicownik", user=self.user)
        board = KanbanBoard.objects.create(name="Tablica do Usunięcia", workspace=workspace, user=self.user)
        KanbanBoard.objects.create(name="Druga Tablica", workspace=workspace, user=self.user)

        response = self.client.post(reverse('kanban:delete_board', args=[board.id]))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, board_index_url(workspace_id=workspace.id))
        self.assertFalse(KanbanBoard.objects.filter(id=board.id).exists())

    def test_create_column_requires_params(self):
        workspace = Workspace.objects.create(name="Szkicownik", user=self.user)
        board = KanbanBoard.objects.create(name="Tablica", workspace=workspace, user=self.user)

        response = self.client.post(
            reverse('kanban:create_column'),
            {'is_ajax': 'true'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['status'], 'error')

    def test_move_card_rejects_cross_board(self):
        workspace = Workspace.objects.create(name="Szkicownik", user=self.user)
        board_a = KanbanBoard.objects.create(name="A", workspace=workspace, user=self.user)
        board_b = KanbanBoard.objects.create(name="B", workspace=workspace, user=self.user)
        col_a = KanbanColumn.objects.create(board=board_a, name="Lista A", order=0)
        col_b = KanbanColumn.objects.create(board=board_b, name="Lista B", order=0)
        card = KanbanCard.objects.create(
            column=col_a, user=self.user, title="Karta", order=0,
        )

        response = self.client.post(
            reverse('kanban:move_card'),
            data=json.dumps({
                'card_id': card.id,
                'column_id': col_b.id,
                'order': 0,
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        card.refresh_from_db()
        self.assertEqual(card.column_id, col_a.id)

    def test_delete_attachment_requires_card_owner(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        other = User.objects.create_user(
            username='other', email='other@example.com', password='password123',
        )
        workspace = Workspace.objects.create(name="Szkicownik", user=self.user)
        board = KanbanBoard.objects.create(name="Tablica", workspace=workspace, user=self.user)
        column = KanbanColumn.objects.create(board=board, name="Lista", order=0)
        card = KanbanCard.objects.create(column=column, user=self.user, title="Karta", order=0)
        attachment = KanbanAttachment.objects.create(
            card=card,
            file=SimpleUploadedFile('test.txt', b'hello'),
            original_name='test.txt',
            uploaded_by=self.user,
        )

        self.client.logout()
        self.client.login(email='other@example.com', password='password123')
        response = self.client.post(
            reverse('kanban:delete_attachment', args=[attachment.id]),
        )
        self.assertEqual(response.status_code, 404)
        self.assertTrue(KanbanAttachment.objects.filter(id=attachment.id).exists())

