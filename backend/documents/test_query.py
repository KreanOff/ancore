from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from tasks.models import TaskTag
from workplaces.models import create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import Document, DocumentLibrary, Folder


class DocumentQueryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='query-owner', email='query-owner@example.test')
        cls.other = get_user_model().objects.create_user(username='query-other', email='query-other@example.test')
        cls.workspace = create_workplace_for_user(cls.user, 'Query workspace')
        cls.other_workspace = create_workplace_for_user(cls.user, 'Other workspace')
        cls.base = scoped_workplace_app_path(cls.workspace, 'documents')
        cls.alpha = DocumentLibrary.objects.create(owner=cls.user, workplace=cls.workspace, name='alpha', description='Umowy zespołu')
        cls.zulu = DocumentLibrary.objects.create(owner=cls.user, workplace=cls.workspace, name='Zulu', description='')
        cls.folder = Folder.objects.create(owner=cls.user, workplace=cls.workspace, library=cls.alpha, name='Archiwum')
        cls.nested = Folder.objects.create(owner=cls.user, workplace=cls.workspace, library=cls.alpha, parent=cls.folder, name='Załączniki')
        cls.tag = TaskTag.objects.create(user=cls.user, workplace=cls.workspace, name='Klient')
        cls.a = Document.objects.create(owner=cls.user, workplace=cls.workspace, library=cls.alpha, folder=cls.nested,
                                       title='alpha umowa', filename='alpha.PDF', description='Oferta klienta', file_size=1024 * 1024)
        cls.a.favorited_by.add(cls.user)
        cls.z = Document.objects.create(owner=cls.user, workplace=cls.workspace, library=cls.zulu,
                                       title='Zulu', filename='zulu.txt', description='', file_size=6 * 1024 * 1024)
        cls.a.tags.add(cls.tag)
        past = timezone.now() - timedelta(days=40)
        Document.objects.filter(pk=cls.a.pk).update(created_at=past, updated_at=past)
        DocumentLibrary.objects.filter(pk=cls.alpha.pk).update(created_at=past, updated_at=past)
        cls.foreign_library = DocumentLibrary.objects.create(owner=cls.other, workplace=cls.workspace, name='Foreign secret')
        cls.outside_library = DocumentLibrary.objects.create(owner=cls.user, workplace=cls.other_workspace, name='Outside secret')
        for lib in [cls.foreign_library, cls.outside_library]:
            Document.objects.create(owner=lib.owner, workplace=lib.workplace, library=lib, title='Hidden', filename='hidden.PDF')

    def setUp(self):
        self.client.force_login(self.user)

    def rows(self, **params):
        response = self.client.get(self.base, {'view': 'all', **params})
        self.assertEqual(response.status_code, 200)
        return [row['item'].pk for row in response.context['rows']]

    def libraries(self, **params):
        response = self.client.get(self.base, params)
        self.assertEqual(response.status_code, 200)
        return [item.pk for item in response.context['libraries']]

    def test_text_conditions_combine_with_search_and_find_nested_documents(self):
        self.assertEqual(self.rows(library=self.alpha.pk, name='UMOWA'), [self.a.pk])
        self.assertEqual(self.rows(description='oferta', filename='.PDF'), [self.a.pk])
        self.assertEqual(self.rows(description='klienta', description_op='not_contains'), [self.z.pk])
        self.assertEqual(self.rows(description_op='is_empty'), [self.z.pk])
        self.assertEqual(self.rows(description_op='is_not_empty'), [self.a.pk])
        self.assertEqual(self.rows(name='alpha', q='Zulu'), [])
        self.assertEqual(self.libraries(name='ALPHA', description='zespołu'), [self.alpha.pk])
        self.assertEqual(self.libraries(description_op='is_empty'), [self.zulu.pk])
        self.assertEqual(self.libraries(description='zespołu', description_op='not_contains'), [self.zulu.pk])

    def test_choice_filters_compose_and_do_not_include_unrelated_folders(self):
        params = {'library': self.alpha.pk, 'file_type': '.pdf', 'size': 'medium', 'starred': 'yes'}
        self.assertEqual(self.rows(**params), [self.a.pk])
        self.assertEqual(self.rows(**{**params, 'starred': 'no'}), [])
        self.assertEqual(self.rows(document_library=self.zulu.pk), [self.z.pk])
        self.assertEqual(self.rows(size='large'), [self.z.pk])
        self.assertEqual(self.rows(size='small'), [])
        self.assertEqual(self.rows(file_type='.txt', starred='no'), [self.z.pk])

    def test_size_boundaries_are_disjoint(self):
        for size, expected in [(1024 * 1024 - 1, 'small'), (1024 * 1024, 'medium'), (5 * 1024 * 1024, 'medium'), (5 * 1024 * 1024 + 1, 'large')]:
            Document.objects.filter(pk=self.a.pk).update(file_size=size)
            for option in ['small', 'medium', 'large']:
                with self.subTest(size=size, option=option):
                    self.assertEqual(self.rows(document_library=self.alpha.pk, size=option), [self.a.pk] if option == expected else [])

    def test_date_filters_use_deletion_date_in_trash(self):
        self.assertEqual(self.rows(modified='today'), [self.z.pk])
        self.assertEqual(self.rows(modified='30'), [self.z.pk])
        self.assertEqual(self.libraries(modified='7'), [self.zulu.pk])
        Document.objects.filter(pk=self.a.pk).update(deleted_at=timezone.now())
        self.assertEqual(self.rows(view='trash', modified='today'), [self.a.pk])
        self.assertEqual(self.rows(view='all', modified='today'), [self.z.pk])

    def test_library_presence_counts_distinguish_active_files_and_folders(self):
        self.assertEqual(self.libraries(folders='yes'), [self.alpha.pk])
        self.assertEqual(self.libraries(folders='no'), [self.zulu.pk])
        self.assertEqual(self.libraries(documents='no'), [])
        Document.objects.filter(pk=self.a.pk).update(deleted_at=timezone.now())
        self.assertEqual(self.libraries(documents='no', folders='yes'), [self.alpha.pk])
        self.assertEqual(self.libraries(documents='yes'), [self.zulu.pk])

    def test_library_sort_fields_support_both_directions_and_distinct_counts(self):
        Document.objects.create(owner=self.user, workplace=self.workspace, library=self.alpha, title='Drugi plik', filename='drugi.txt')
        expected = {
            'name': [self.alpha.pk, self.zulu.pk], 'description': [self.zulu.pk, self.alpha.pk],
            'documents': [self.zulu.pk, self.alpha.pk], 'folders': [self.zulu.pk, self.alpha.pk],
            'created': [self.alpha.pk, self.zulu.pk], 'updated': [self.alpha.pk, self.zulu.pk],
        }
        for field, ids in expected.items():
            for direction in ['asc', 'desc']:
                with self.subTest(field=field, direction=direction):
                    self.assertEqual(self.libraries(sort=f'{field}_{direction}'), ids if direction == 'asc' else ids[::-1])
        library = self.client.get(self.base).context['libraries'][0]
        self.assertEqual((library.document_count, library.folder_count), (2, 2))

    def test_document_sort_fields_support_both_directions_with_null_folders_last(self):
        expected = {
            'name': [self.a.pk, self.z.pk], 'filename': [self.a.pk, self.z.pk],
            'description': [self.z.pk, self.a.pk], 'library': [self.a.pk, self.z.pk],
            'size': [self.a.pk, self.z.pk], 'created': [self.a.pk, self.z.pk], 'updated': [self.a.pk, self.z.pk],
        }
        for field, ids in expected.items():
            for direction in ['asc', 'desc']:
                with self.subTest(field=field, direction=direction):
                    self.assertEqual(self.rows(sort=f'{field}_{direction}'), ids if direction == 'asc' else ids[::-1])
        for direction in ['asc', 'desc']:
            self.assertEqual(self.rows(sort=f'folder_{direction}'), [self.a.pk, self.z.pk])
        Document.objects.filter(pk=self.a.pk).update(deleted_at=timezone.now())
        Document.objects.filter(pk=self.z.pk).update(deleted_at=timezone.now() - timedelta(days=1))
        self.assertEqual(self.rows(view='trash', sort='updated_desc'), [self.a.pk, self.z.pk])

    def test_invalid_filters_and_legacy_sort_links_are_safe(self):
        self.assertEqual(self.libraries(sort='owner__password'), [self.alpha.pk, self.zulu.pk])
        self.assertEqual(self.rows(sort='owner__password', file_type='unknown', size='invalid', modified='invalid'), [self.z.pk, self.a.pk])
        self.assertEqual(self.rows(name='alpha', name_op='invalid'), [self.a.pk])
        for old, current in [('name', 'name_asc'), ('updated', 'updated_desc'), ('oldest', 'created_asc'), ('size', 'size_desc')]:
            self.assertEqual(self.rows(sort=old), self.rows(sort=current))
        self.assertEqual(self.rows(sort=''), self.rows(sort='updated_desc'))

    def test_filter_choices_and_direct_urls_keep_owner_and_workspace_boundaries(self):
        tag = TaskTag.objects.create(user=self.other, workplace=self.workspace, name='Secret tag')
        for library in [self.foreign_library, self.outside_library]:
            self.assertEqual(self.client.get(self.base, {'view': 'all', 'document_library': library.pk}).status_code, 404)
        self.assertEqual(set(self.rows(tag=tag.pk)), {self.a.pk, self.z.pk})
        response = self.client.get(self.base, {'view': 'all'})
        for text in ['Foreign secret', 'Outside secret', 'Secret tag', 'Hidden']:
            self.assertNotContains(response, text)
        self.assertEqual(set(self.rows()), {self.a.pk, self.z.pk})

    def test_filtered_pagination_and_actions_preserve_query_state(self):
        for i in range(22):
            Document.objects.create(owner=self.user, workplace=self.workspace, library=self.alpha,
                                    title=f'Oferta {i:02}', filename=f'oferta{i}.PDF')
        params = {'view': 'all', 'name': 'Oferta', 'name_op': 'contains', 'file_type': '.pdf', 'sort': 'name_desc', 'page_size': '10'}
        response = self.client.get(self.base, {**params, 'tag': self.tag.pk})
        first = [row['item'].pk for row in response.context['rows']]
        next_url = response.context['document_window']['next_url']
        query = parse_qs(urlsplit(next_url).query)
        self.assertNotIn('tag', query)
        self.assertEqual(query['name'], ['Oferta'])
        self.assertEqual(query['sort'], ['name_desc'])
        second = [row['item'].pk for row in self.client.get(next_url).context['rows']]
        self.assertEqual((len(first), len(second), len(set(first + second))), (20, 22, 22))
        for action in ['star', 'trash', 'restore']:
            response = self.client.post(f'{self.base}{first[0]}/{action}/', {**params, 'scope': 'workspace', 'page': '2'})
            returned = parse_qs(urlsplit(response.url).query)
            for key, value in params.items():
                self.assertEqual(returned[key], [value])
            self.assertEqual(returned['page'], ['2'])

    def test_name_filter_and_sort_apply_to_folders_before_files(self):
        ids = self.rows(library=self.alpha.pk, name='a', sort='name_desc')
        self.assertEqual(ids, [self.nested.pk, self.folder.pk, self.a.pk])
        self.assertEqual(self.rows(library=self.alpha.pk, filename='alpha'), [self.a.pk])
        self.assertEqual(self.rows(library=self.alpha.pk, name='no matching result'), [])
