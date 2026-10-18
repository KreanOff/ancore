from .testing import make_space

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

    def test_filters_sort_pagination_and_visible_usage_counts(self):
        for n in range(27):
            TaskTag.objects.create(name=f'Wydanie {n:02}', user=self.owner, workplace=self.workspace, space=self.space, priority='high')
        url = self.url() + '&q=Wydanie&priority=high&sort=name_desc&page_size=25'
        response = self.client.get(url)
        self.assertEqual(response.context['tag_window']['total_tags'], 27)
        self.assertEqual(response.context['tags'][0].name, 'Wydanie 26')
        next_url = response.context['tag_window']['next_url']
        self.assertTrue(next_url.startswith(self.url().split('?')[0]))
        self.assertIn('q=Wydanie', next_url)
        self.assertEqual(len(self.client.get(next_url).context['tags']), 2)
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
