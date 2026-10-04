"""Historical model invariants; HTTP retirement is covered in test_retirement."""
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from .models import KanbanProject, KanbanSection

class LegacyKanbanModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='task-user',
            email='task-user@example.com',
            first_name='Kanban',
            last_name='User',
            password='test-pass-123',
        )
        self.client.force_login(self.user)

    def test_project_code_generation_does_not_load_all_project_codes(self):
        for index in range(20):
            KanbanProject.objects.create(user=self.user, name=f'Istniejący {index}', code=f'OLD-{index:03d}')

        with patch('kanban.models.secrets.choice', side_effect=list('KBN12345')):
            with CaptureQueriesContext(connection) as queries:
                project = KanbanProject.objects.create(user=self.user, name='Nowy projekt')

        select_sql = ' '.join(query['sql'] for query in queries if query['sql'].startswith('SELECT'))
        self.assertEqual(project.code, 'P-KBN12345')
        self.assertIn('"kanban_kanbanproject"."code" =', select_sql)
        self.assertNotIn('SELECT "kanban_kanbanproject"."code"', select_sql)
        self.assertLessEqual(len(queries), 4)

    def test_legacy_entity_icons_are_not_editable(self):
        for model in (KanbanProject, KanbanSection):
            with self.subTest(model=model.__name__):
                self.assertFalse(model._meta.get_field('icon').editable)
