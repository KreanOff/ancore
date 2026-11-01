from .testing import make_space
from urllib.parse import parse_qs, urlencode, urlsplit

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import Client, TestCase

from .forms import ItemForm
from django.test import RequestFactory
from tasks.models import TaskTag, TaskTagNote
from .models import SpaceTask, SpaceMembership
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class SpaceTagTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(username='tags-owner', email='tags-owner@example.test')
        cls.member = User.objects.create_user(username='tags-member', email='tags-member@example.test')
        cls.observer = User.objects.create_user(username='tags-observer', email='tags-observer@example.test')
        cls.other = User.objects.create_user(username='tags-other', email='tags-other@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Tagi')
        cls.foreign = create_workplace_for_user(cls.other, 'Inny Workspace')
        for person in (cls.member, cls.observer):
            WorkplaceMembership.objects.create(workplace=cls.workspace, user=person, role='member')
        cls.project = make_space(name='Produkt', user=cls.owner, workplace=cls.workspace, visibility='private', private_owner=cls.owner)
        for person, role in ((cls.member, 'member'), (cls.observer, 'observer')):
            SpaceMembership.objects.create(space=cls.project, user=person, role=role)
        cls.space = cls.project
        cls.section = cls.project
        cls.task = SpaceTask.objects.create(created_by=cls.owner, space=cls.section, title='Test tagów')
        cls.hidden = make_space(name='Ukryta', user=cls.owner, workplace=cls.workspace, visibility='private', private_owner=cls.owner)
        cls.foreign_space = make_space(name='Obca', user=cls.other, workplace=cls.foreign)
        cls.tag = TaskTag.objects.create(name='Tag produktu', user=cls.owner, workplace=cls.workspace, space=cls.space)
        cls.hidden_tag = TaskTag.objects.create(name='Poufny tag', owner_label='Poufny dział', user=cls.owner, workplace=cls.workspace, space=cls.hidden)
        cls.foreign_tag = TaskTag.objects.create(name='Obcy tag', user=cls.other, workplace=cls.foreign, space=cls.foreign_space)
        cls.legacy_tag = TaskTag.objects.create(name='Stary tag', user=cls.owner, workplace=cls.workspace)
        cls.task.tags.add(cls.tag)

    def setUp(self):
        self.client.force_login(self.owner)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, space=None, plain=False):
        suffix = f'{(space or self.space).slug}/?view=tags'
        return '/space/' + suffix if plain else scoped_workplace_app_path(self.workspace, 'space', suffix)

    def test_directory_plain_scoped_excludes_legacy_tags(self):
        self.client.force_login(self.member)
        for plain in (True, False):
            response = self.client.get(self.url(plain=plain))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Tag produktu')
            self.assertContains(response, 'Dodaj tag')
            self.assertContains(response, 'aria-current="page"><i data-icon="tag"', html=False)
            for value in ('Poufny tag', 'Poufny dział', 'Obcy tag', 'Stary tag'):
                self.assertNotContains(response, value)
        self.assertEqual(self.client.get(f'/workplaces/{self.workspace.slug}/tasks/?view=tags').status_code, 404)

    def test_create_duplicate_edit_and_related_scope(self):
        self.client.force_login(self.member)
        response = self.client.post(self.url(), {'action': 'create_tag', 'name': 'Wydanie', 'related_tags': [self.tag.pk], 'color': '#5b5fc7'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url())
        tag = TaskTag.objects.get(space=self.space, name='Wydanie')
        self.assertEqual(tag.user, self.owner)
        self.assertEqual(tag.workplace, self.workspace)
        self.assertEqual(list(tag.related_tags.all()), [self.tag])
        response = self.client.post(self.url(), {'action': 'create_tag', 'name': ' wydanie '})
        self.assertContains(response, 'Taki tag już istnieje.')
        self.assertTrue(response.context['tag_modal_open'])
        response = self.client.post(self.url(), {'action': 'edit_tag', 'tag_id': tag.pk, 'name': 'Nowa nazwa', 'status': 'archived'})
        self.assertEqual(response.status_code, 302)
        tag.refresh_from_db()
        self.assertEqual(tag.status, 'archived')
        self.assertEqual(tag.name, 'Nowa nazwa')
        for foreign in (self.hidden_tag, self.foreign_tag, self.legacy_tag):
            response = self.client.post(self.url(), {'action': 'create_tag', 'name': 'Nie zapisuj', 'related_tags': [foreign.pk]})
            self.assertTrue(response.context['tag_form'].errors)
        self.assertFalse(TaskTag.objects.filter(name='Nie zapisuj').exists())

    def test_same_names_allowed_in_different_spaces_only(self):
        TaskTag.objects.create(name=self.tag.name, user=self.owner, workplace=self.workspace, space=self.hidden)
        with self.assertRaises(IntegrityError), transaction.atomic():
            TaskTag.objects.create(name=self.tag.name, user=self.owner, workplace=self.workspace, space=self.space)

    def test_foreign_ids_and_bulk_delete_are_rejected_atomically(self):
        for tag in (self.hidden_tag, self.foreign_tag, self.legacy_tag):
            for action in ('edit_tag', 'delete_tag', 'add_tag_note'):
                response = self.client.post(self.url(), {'action': action, 'tag_id': tag.pk, 'name': 'Zmiana', 'message': 'Notatka'})
                self.assertEqual(response.status_code, 404)
        response = self.client.post(self.url(), {'action': 'delete_tag', 'tag_ids': [self.tag.pk, self.hidden_tag.pk]})
        self.assertEqual(response.status_code, 404)
        self.assertTrue(TaskTag.objects.filter(pk=self.tag.pk).exists())
        response = self.client.post(self.url(), {'action': 'delete_tag', 'tag_ids': [self.tag.pk]})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.task.tags.exists())

    def test_hidden_space_and_revoked_access(self):
        self.client.force_login(self.member)
        for space in (self.hidden, self.foreign_space):
            self.assertEqual(self.client.get(self.url(space)).status_code, 404)
            self.assertEqual(self.client.post(self.url(space), {'action': 'create_tag', 'name': 'Brak'}).status_code, 404)
        SpaceMembership.objects.filter(space=self.project, user=self.member).delete()
        self.assertEqual(self.client.get(self.url()).status_code, 404)

    def test_observer_reads_but_cannot_modify(self):
        self.client.force_login(self.observer)
        response = self.client.get(self.url())
        self.assertContains(response, 'Tag produktu')
        self.assertNotContains(response, 'Dodaj tag')
        self.assertNotContains(response, 'id="tag-create-form"')
        self.assertNotContains(response, 'data-directory-row-action="delete"')
        for action in ('create_tag', 'edit_tag', 'delete_tag', 'add_tag_note'):
            self.assertEqual(self.client.post(self.url(), {'action': action, 'tag_id': self.tag.pk, 'name': 'Brak', 'message': 'Brak'}).status_code, 403)

    def test_notes_keep_author_and_only_author_edits(self):
        self.client.force_login(self.member)
        self.client.post(self.url(), {'action': 'add_tag_note', 'tag_id': self.tag.pk, 'message': 'Treść'})
        note = TaskTagNote.objects.get(tag=self.tag)
        self.assertEqual(note.author, self.member)
        response = self.client.post(self.url(), {'action': 'edit_tag_note', 'tag_id': self.tag.pk, 'note_id': note.pk, 'message': 'Zmieniona'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.json()['note']['message'], 'Zmieniona')
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(self.url(), {'action': 'delete_tag_note', 'tag_id': self.tag.pk, 'note_id': note.pk}).status_code, 404)

    def test_filters_sort_loading_and_visible_usage_counts(self):
        for n in range(27):
            TaskTag.objects.create(name=f'Wydanie {n:02}', user=self.owner, workplace=self.workspace, space=self.space, priority='high')
        url = self.url() + '&q=Wydanie&priority=high&sort=name_desc&page_size=25'
        response = self.client.get(url)
        self.assertEqual(response.context['tag_window']['total_tags'], 27)
        self.assertEqual(response.context['tag_window']['loaded_count'], 20)
        self.assertEqual(response.context['tags'][0].name, 'Wydanie 26')
        next_url = response.context['tag_window']['more_url']
        self.assertTrue(next_url.startswith(self.url().split('?')[0]))
        self.assertIn('q=Wydanie', next_url)
        self.assertEqual(len(self.client.get(next_url).context['tags']), 27)
        self.client.force_login(self.member)
        self.task.visibility = 'private'
        self.task.private_owner = self.owner
        self.task.save()
        response = self.client.get(self.url())
        tag = next(tag for tag in response.context['tags'] if tag.pk == self.tag.pk)
        self.assertEqual(tag.total_tasks, 0)
        self.assertEqual(self.client.get(self.url() + '&q=brak-wyników').context['tags'], [])

    def test_task_forms_and_creation_reject_foreign_tags(self):
        request = RequestFactory().get(self.url())
        request.user, request.workplace = self.member, self.workspace
        form = ItemForm(request=request, space=self.space, item=self.task.work_item)
        self.assertEqual(list(form.fields['tags'].queryset), [self.tag])
        form = ItemForm(request=request, space=self.space)
        self.assertEqual(list(form.fields['tags'].queryset), [self.tag])
        item_url = scoped_workplace_app_path(self.workspace, 'spaces', f'{self.space.pk}/items/create/')
        for tag in (self.hidden_tag, self.foreign_tag, self.legacy_tag):
            response = self.client.post(item_url, {'title': 'Nie dodawaj', 'work_type': 'task', 'priority': 'medium', 'tags': [tag.pk]}, HTTP_X_WORK_MODAL='true')
            self.assertEqual(response.status_code, 400)
        self.assertFalse(SpaceTask.objects.filter(title='Nie dodawaj').exists())
        response = self.client.post(item_url, {'title': 'Z tagiem', 'work_type': 'task', 'priority': 'medium', 'tags': [self.tag.pk]})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(list(SpaceTask.objects.get(title='Z tagiem').tags.all()), [self.tag])

    def test_model_links_and_moves_respect_scope(self):
        with self.assertRaises(ValidationError), transaction.atomic():
            self.task.tags.add(self.hidden_tag)
        with self.assertRaises(ValidationError), transaction.atomic():
            self.hidden_tag.space_tasks.add(self.task)
        with self.assertRaises(ValidationError), transaction.atomic():
            self.tag.related_tags.add(self.hidden_tag)
        self.task.space = self.hidden
        with self.assertRaises(ValidationError), transaction.atomic():
            self.task.save()
        self.task.refresh_from_db()
        self.assertEqual(self.task.space, self.space)
        self.assertEqual(list(self.task.tags.all()), [self.tag])

    def test_global_search_hides_private_space_tags_and_links_to_space(self):
        self.client.force_login(self.member)
        response = self.client.get('/global-search/', {'q': 'Tag produktu'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.url().split('?')[0], str(response.json()))
        response = self.client.get('/global-search/', {'q': 'Poufny tag'})
        self.assertEqual(response.json()['groups'], [])
        self.assertEqual(response.json()['total'], 0)

    def test_legacy_endpoint_cannot_edit_space_tags(self):
        url = f'/workplaces/{self.workspace.slug}/tasks/?view=tags'
        for action in ('edit_tag', 'delete_tag', 'add_tag_note'):
            self.assertEqual(self.client.post(url, {'action': action, 'tag_id': self.tag.pk, 'name': 'Brak', 'message': 'Brak'}).status_code, 404)

    def test_csrf_is_required(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post(self.url(), {'action': 'create_tag', 'name': 'Brak CSRF'}).status_code, 403)

    def test_legacy_tags_do_not_change_independent_assignments(self):
        linked = TaskTag.objects.create(name='Powiązany', user=self.owner, workplace=self.workspace, space=self.space)
        self.tag.related_tags.add(linked)
        note = TaskTagNote.objects.create(tag=self.tag, author=self.member, message='Notatka')
        self.legacy_tag.name = 'Zmieniony stary tag'
        self.legacy_tag.save()
        self.assertEqual(list(self.task.tags.all()), [self.tag])
        self.assertEqual(self.tag.related_tags.get(), linked)
        self.assertEqual(self.tag.tag_notes.get(), note)
        self.assertTrue(TaskTag.objects.filter(pk=self.legacy_tag.pk, space__isnull=True).exists())


class TagWindowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='tag-window-owner', email='tag-window-owner@example.test')
        cls.member = users.objects.create_user(username='tag-window-member', email='tag-window-member@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Doładowywanie tagów')
        WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Tagi',
                               visibility='private', private_owner=cls.owner)
        SpaceMembership.objects.create(space=cls.space, user=cls.member)
        cls.tags = [TaskTag.objects.create(
            user=cls.owner, workplace=cls.workspace, space=cls.space, name=f'Wydanie {index:02}',
            priority='high' if index % 2 == 0 else 'low', owner_label='Zespół',
        ) for index in range(65)]
        cls.other_workspace = create_workplace_for_user(cls.owner, 'Inne tagi')
        WorkplaceMembership.objects.create(workplace=cls.other_workspace, user=cls.member)
        cls.other_space = make_space(user=cls.owner, workplace=cls.other_workspace, name='Tagi', slug=cls.space.slug)
        cls.foreign_tag = TaskTag.objects.create(user=cls.owner, workplace=cls.other_workspace,
                                                space=cls.other_space, name='Obcy Workspace')

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, scoped=True, **params):
        path = (scoped_workplace_app_path(self.workspace, 'space', self.space.slug + '/')
                if scoped else f'/space/{self.space.slug}/')
        return path + '?' + urlencode({'view': 'tags', **params})

    def page(self, target=None, *, scoped=True, **params):
        endpoint = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/') if scoped else '/api/v1/page/'
        response = self.client.get(endpoint, {'url': target or self.url(scoped, **params)}, follow=True)
        self.assertEqual(response.status_code, 200)
        return response.json()['data']

    def test_plain_and_scoped_html_and_api_load_twenty_and_remove_page_controls(self):
        for scoped in (False, True):
            with self.subTest(scoped=scoped):
                target = self.url(scoped, page=99, page_size=150)
                response = self.client.get(target, follow=True)
                self.assertEqual(response.status_code, 200)
                window = response.context['tag_window']
                self.assertEqual((window['loaded_count'], window['total_tags']), (20, 65))
                self.assertEqual(list(response.context['tags']), self.tags[:20])
                self.assertContains(response, 'Pokaż więcej: Tagi (20 / 65)')
                self.assertNotContains(response, 'Strony tagów')
                self.assertNotContains(response, 'data-project-search-page-size')
                data = self.page(target, scoped=scoped)
                self.assertEqual(set(data['window']), {'total_tags', 'loaded_count', 'more_url'})
                self.assertEqual(data['window']['loaded_count'], 20)
                self.assertEqual([tag['id'] for tag in data['tags']], [tag.pk for tag in self.tags[:20]])

    def test_more_retains_prefix_and_filters_through_last_partial_batch(self):
        params = {'q': 'Wydanie', 'category': 'general', 'scope': 'tasks', 'owner': 'Zespół',
                  'status': 'active', 'sort': 'name_desc'}
        data = self.page(page=2, page_size=10, **params)
        expected = [tag.pk for tag in reversed(self.tags)]
        for loaded in (20, 40, 60, 65):
            with self.subTest(loaded=loaded):
                self.assertEqual([tag['id'] for tag in data['tags']], expected[:loaded])
                self.assertEqual(data['window']['loaded_count'], loaded)
                self.assertEqual(data['window']['total_tags'], 65)
                target = data['window']['more_url']
                if loaded == 65:
                    self.assertEqual(target, '')
                else:
                    query = parse_qs(urlsplit(target).query)
                    self.assertEqual(query, {key: [str(value)] for key, value in {
                        'view': 'tags', **params, 'tags_limit': min(loaded + 20, 65),
                    }.items()})
                    data = self.page(target)
        filtered = self.page(priority='high', sort='name_desc', tags_limit=40)
        self.assertEqual([tag['id'] for tag in filtered['tags']], [tag.pk for tag in reversed(self.tags[::2])])
        self.assertEqual(filtered['window'], {'total_tags': 33, 'loaded_count': 33, 'more_url': ''})

    def test_limits_are_bounded_and_all_rows_remain_reachable(self):
        for value in ('', '-1', '0', '5', 'abc', '20.5', '９９', '0' * 200):
            with self.subTest(value=value):
                data = self.page(tags_limit=value)
                self.assertEqual([tag['id'] for tag in data['tags']], [tag.pk for tag in self.tags[:20]])
        for value in ('9' * 200, '0' * 200 + '65'):
            with self.subTest(value=value):
                data = self.page(tags_limit=value)
                self.assertEqual([tag['id'] for tag in data['tags']], [tag.pk for tag in self.tags])
                self.assertEqual(data['window']['more_url'], '')

    def test_completed_small_and_empty_results_have_correct_footer(self):
        response = self.client.get(self.url(tags_limit=999))
        self.assertContains(response, 'Wszystkie tagi <span class="work-list-more__count">(65 / 65)</span>', html=False)
        self.assertNotContains(response, 'Pokaż więcej: Tagi')
        for query, expected_count in (('Wydanie 00', 1), ('Brak wyników', 0)):
            with self.subTest(query=query):
                data = self.page(q=query, tags_limit=999)
                self.assertEqual(data['window'], {'total_tags': expected_count, 'loaded_count': expected_count, 'more_url': ''})
                response = self.client.get(self.url(q=query, tags_limit=999))
                self.assertNotContains(response, 'work-list-more')
        self.assertContains(response, 'Nie znaleziono tagów.')

    def test_more_rechecks_space_access_and_workspace_scope(self):
        target = self.page()['window']['more_url']
        SpaceMembership.objects.filter(space=self.space, user=self.member).delete()
        endpoint = scoped_workplace_app_path(self.workspace, 'api', 'v1/page/')
        self.assertEqual(self.client.get(endpoint, {'url': target}).status_code, 404)
        other_endpoint = scoped_workplace_app_path(self.other_workspace, 'api', 'v1/page/')
        other_target = scoped_workplace_app_path(self.other_workspace, 'space', self.other_space.slug + '/')
        response = self.client.get(other_endpoint, {'url': other_target + '?view=tags&tags_limit=100'})
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual([tag['id'] for tag in data['tags']], [self.foreign_tag.pk])
        self.assertEqual(data['window'], {'total_tags': 1, 'loaded_count': 1, 'more_url': ''})

    def test_mutations_keep_expanded_context_and_recount_remaining_rows(self):
        for scoped in (False, True):
            with self.subTest(scoped=scoped):
                target = self.url(scoped, tags_limit=40, sort='name_desc', q='Wydanie')
                response = self.client.post(target, {
                    'action': 'add_tag_note', 'tag_id': self.tags[-1].pk, 'message': 'Notatka',
                })
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, target)
                self.assertEqual(self.page(response.url, scoped=scoped)['window']['loaded_count'], 40)
        target = self.url(tags_limit=65)
        response = self.client.post(target, {'action': 'delete_tag', 'tag_ids': [self.tags[0].pk]})
        self.assertEqual(response.status_code, 302)
        data = self.page(response.url)
        self.assertEqual(data['window'], {'total_tags': 64, 'loaded_count': 64, 'more_url': ''})
        self.assertEqual([tag['id'] for tag in data['tags']], [tag.pk for tag in self.tags[1:]])
