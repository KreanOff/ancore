from datetime import timedelta
from urllib.parse import parse_qs, urlencode, urlsplit

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from tasks.models import TaskTag
from workplaces.models import create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .models import WorkspaceDocument as Document, WorkspaceDocumentFolder as Folder


class OfficeQueryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username='office-query', email='office-query@example.test')
        cls.other = get_user_model().objects.create_user(username='office-query-other', email='office-query-other@example.test')
        cls.workspace = create_workplace_for_user(cls.user, 'Dokumenty — filtry')
        cls.outside = create_workplace_for_user(cls.user, 'Drugi Workspace')
        cls.base = scoped_workplace_app_path(cls.workspace, 'office')
        cls.folder = Folder.objects.create(owner=cls.user, workplace=cls.workspace, name='alpha')
        cls.nested = Folder.objects.create(owner=cls.user, workplace=cls.workspace, parent=cls.folder, name='Zulu')
        cls.tag = TaskTag.objects.create(user=cls.user, workplace=cls.workspace, name='Klient')
        cls.alpha = Document.objects.create(owner=cls.user, workplace=cls.workspace, folder=cls.nested,
                                           kind='file', title='alpha umowa', filename='alpha.PDF', file_size=1024 * 1024, is_starred=True)
        cls.zulu = Document.objects.create(owner=cls.user, workplace=cls.workspace, kind='file',
                                          title='Zulu', filename='zulu.txt', file_size=6 * 1024 * 1024)
        cls.alpha.tags.add(cls.tag)
        past = timezone.now() - timedelta(days=40)
        Document.objects.filter(pk=cls.alpha.pk).update(created_at=past, updated_at=past)
        Folder.objects.filter(pk=cls.folder.pk).update(created_at=past)
        for overrides in [{'owner': cls.other}, {'workplace': cls.outside}]:
            scope = {'owner': cls.user, 'workplace': cls.workspace, **overrides}
            Document.objects.create(**scope, kind='file', title='Ukryty dokument', filename='secret.pdf')
            Folder.objects.create(**scope, name='Ukryty folder')

    def setUp(self):
        self.client.force_login(self.user)

    def rows(self, **params):
        response = self.client.get(self.base, {'view': 'recent', **params})
        self.assertEqual(response.status_code, 200)
        return [row['item'].pk for row in response.context['rows']]

    def test_text_conditions_search_and_nested_folder_scope(self):
        self.assertEqual(self.rows(view='all', folder=self.folder.pk, name='UMOWA'), [self.alpha.pk])
        self.assertEqual(self.rows(filename='.PDF', name='alpha'), [self.alpha.pk])
        self.assertEqual(self.rows(name='alpha', name_op='not_contains'), [self.zulu.pk])
        self.assertEqual(self.rows(filename_op='is_empty'), [])
        self.assertEqual(set(self.rows(filename_op='is_not_empty')), {self.alpha.pk, self.zulu.pk})
        self.assertEqual(self.rows(name='alpha', q='Zulu'), [])
        self.assertEqual(self.rows(name='alpha', q='Klient'), [self.alpha.pk])
        self.assertEqual(self.rows(view='all', folder=self.folder.pk), [self.nested.pk])

    def test_choice_filters_combine_and_hide_folders(self):
        filters = {'view': 'all', 'tag': self.tag.pk, 'file_type': '.pdf', 'size': 'medium', 'starred': 'yes'}
        self.assertEqual(self.rows(**filters), [self.alpha.pk])
        self.assertEqual(self.rows(**{**filters, 'starred': 'no'}), [])
        self.assertEqual(self.rows(view='all', file_type='.txt', starred='no'), [self.zulu.pk])
        self.assertEqual(self.rows(view='starred'), [self.alpha.pk])

    def test_type_filter_includes_native_and_uploaded_documents(self):
        for kind in ['text', 'board']:
            item = Document.objects.create(owner=self.user, workplace=self.workspace, kind=kind, title=kind)
            self.assertEqual(self.rows(view='all', file_type=kind), [item.pk])
        for extension in ['docx', 'xlsx', 'pptx']:
            item = Document.objects.create(owner=self.user, workplace=self.workspace, kind='file',
                                           title=extension, filename=f'Nowy.{extension.upper()}')
            self.assertEqual(self.rows(file_type=f'.{extension}'), [item.pk])

    def test_size_boundaries_are_disjoint(self):
        for size, expected in [(1024 * 1024 - 1, 'small'), (1024 * 1024, 'medium'),
                               (5 * 1024 * 1024, 'medium'), (5 * 1024 * 1024 + 1, 'large')]:
            Document.objects.filter(pk=self.alpha.pk).update(file_size=size)
            for option in ['small', 'medium', 'large']:
                with self.subTest(size=size, option=option):
                    self.assertEqual(self.rows(tag=self.tag.pk, size=option), [self.alpha.pk] if option == expected else [])

    def test_date_filters_and_trash_sort_use_deletion_date(self):
        for value in ['today', '7', '30']:
            self.assertEqual(self.rows(modified=value), [self.zulu.pk])
        Document.objects.filter(pk=self.alpha.pk).update(deleted_at=timezone.now())
        Document.objects.filter(pk=self.zulu.pk).update(deleted_at=timezone.now() - timedelta(days=2))
        self.assertEqual(self.rows(view='trash', modified='today'), [self.alpha.pk])
        self.assertEqual(self.rows(view='trash', sort='updated_desc'), [self.alpha.pk, self.zulu.pk])
        response = self.client.get(self.base, {'view': 'trash'})
        self.assertContains(response, 'Usunięto malejąco')

    def test_all_sort_fields_both_directions_and_legacy_links(self):
        for field in ['name', 'filename', 'size', 'created', 'updated']:
            with self.subTest(field=field):
                self.assertEqual(self.rows(sort=f'{field}_asc'), [self.alpha.pk, self.zulu.pk])
                self.assertEqual(self.rows(sort=f'{field}_desc'), [self.zulu.pk, self.alpha.pk])
        for direction in ['asc', 'desc']:
            self.assertEqual(self.rows(sort=f'folder_{direction}'), [self.alpha.pk, self.zulu.pk])
        # Creation and modification order differ: the old alias must keep its meaning.
        Document.objects.filter(pk=self.alpha.pk).update(updated_at=timezone.now() + timedelta(minutes=1))
        for old, current in [('name', 'name_asc'), ('updated', 'updated_desc'), ('oldest', 'updated_asc')]:
            self.assertEqual(self.rows(sort=old), self.rows(sort=current))

    def test_folder_filter_and_order_precede_documents(self):
        self.assertEqual(self.rows(view='all', name='l', sort='name_desc'),
                         [self.nested.pk, self.folder.pk, self.zulu.pk, self.alpha.pk])
        self.assertEqual(self.rows(view='all', modified='today', sort='created_asc'), [self.nested.pk, self.zulu.pk])
        response = self.client.get(self.base, {'folder': self.folder.pk, 'name': 'umowa'})
        self.assertContains(response, '<small>Zulu</small>', html=True)

    def test_invalid_filters_and_direct_links_keep_access_boundaries(self):
        self.assertEqual(self.rows(sort='owner__password', file_type='invalid', modified='invalid', size='invalid'),
                         [self.zulu.pk, self.alpha.pk])
        self.assertEqual(self.rows(name='alpha', name_op='invalid'), [self.alpha.pk])
        for scope in [{'user': self.other, 'workplace': self.workspace}, {'user': self.user, 'workplace': self.outside}]:
            tag = TaskTag.objects.create(**scope, name='Ukryty tag')
            for base in [self.base, '/office/']:
                self.client.get(self.base)
                self.assertEqual(self.client.get(base, {'tag': tag.pk}, follow=True).status_code, 404)
        for base in [self.base, '/office/']:
            response = self.client.get(base, {'name': 'Ukryty', 'display': 'grid'}, follow=True)
            self.assertEqual(response.context['rows'], [])
            self.assertContains(response, 'Brak pasujących dokumentów')
            self.assertNotContains(response, 'Ukryty tag')
            self.assertNotContains(response, 'Ukryty folder')

    def test_pagination_display_tags_and_actions_preserve_filters(self):
        for number in range(27):
            Document.objects.create(owner=self.user, workplace=self.workspace, kind='file',
                                    title=f'Oferta {number:02}', filename=f'oferta{number}.pdf')
        params = {'view': 'all', 'name': 'Oferta', 'filename': 'secret', 'filename_op': 'not_contains',
                  'file_type': '.pdf', 'sort': 'name_desc', 'page_size': '25', 'display': 'list'}
        response = self.client.get(self.base, params)
        first = [row['item'].pk for row in response.context['rows']]
        second = self.client.get(response.context['document_window']['next_url'])
        last = [row['item'].pk for row in second.context['rows']]
        self.assertEqual((len(first), len(last), len(set(first + last))), (25, 2, 27))
        for url in [response.context['document_window']['next_url'], response.context['tag_filter_url']]:
            returned = parse_qs(urlsplit(url).query)
            for key, value in params.items():
                self.assertEqual(returned[key], [value])
        for option in second.context['display_options']:
            returned = parse_qs(urlsplit(option['url']).query)
            self.assertEqual(returned['page'], ['2'])
            for key, value in params.items():
                if key != 'display':
                    self.assertEqual(returned[key], [value])
        for operation in ['star', 'trash', 'restore']:
            response = self.client.post(f'{self.base}{last[0]}/{operation}/', {
                'return_query': urlencode({**params, 'page': '2', 'next': 'https://example.test/'})})
            returned = parse_qs(urlsplit(response.url).query)
            for key, value in params.items():
                self.assertEqual(returned[key], [value])
            self.assertEqual(returned['page'], ['2'])
            self.assertNotIn('next', returned)
