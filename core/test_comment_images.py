import base64
from pathlib import Path
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from dashboard.models import ActivityInterest
from kanban.models import Kanban, KanbanCommentImage
from tasks.models import Task, TaskCommentImage
from workplaces.models import WorkplaceMembership, create_workplace_for_user


PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/2l8AAAAASUVORK5CYII=')


def photo(name='zdjęcie.png', content=PNG):
    return SimpleUploadedFile(name, content, content_type='image/png')


class CommentImageTests(TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.settings_override = override_settings(PRIVATE_DOCUMENT_ROOT=self.directory.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        for model in (TaskCommentImage, KanbanCommentImage):
            field = model._meta.get_field('file')
            self.addCleanup(setattr, field, 'storage', field.storage)
            field.storage = FileSystemStorage(self.directory.name)
        users = get_user_model().objects
        self.owner = users.create_user(username='owner', email='owner@example.test')
        self.member = users.create_user(username='member', email='member@example.test')
        self.outsider = users.create_user(username='outsider', email='outsider@example.test')
        self.workspace = create_workplace_for_user(self.owner, 'Wspólny')
        self.other = create_workplace_for_user(self.owner, 'Inny')
        self.membership = WorkplaceMembership.objects.create(workplace=self.workspace, user=self.member, role='member')
        self.task = Task.objects.create(user=self.owner, workplace=self.workspace, title='Zadanie')
        self.card = Kanban.objects.create(user=self.owner, workplace=self.workspace, title='Karta')
        self.cases = [('tasks', self.task, TaskCommentImage), ('kanban', self.card, KanbanCommentImage)]
        self.login(self.member)

    def login(self, user, workspace=None):
        self.client.force_login(user)
        session = self.client.session
        session['active_workplace_id'] = (workspace or self.workspace).pk
        session.save()

    def url(self, app, task, scoped=True):
        route = 'view-subtask' if task.parent_id else 'view-task'
        url = reverse(f'{app}:{route}', args=[task.task_id])
        if scoped:
            url = f'/workplaces/{self.workspace.slug}' + url
        return url

    def post(self, app, task, files=(), text='', ajax=True, scoped=True):
        return self.client.post(self.url(app, task, scoped), {
            'task_pk': task.pk, 'action': 'add_activity_comment',
            'activity_comment': text, 'comment_attachments': list(files),
        }, headers={'X-Requested-With': 'XMLHttpRequest'} if ajax else {})

    def test_images_with_and_without_text_persist_for_tasks_subtasks_and_cards(self):
        for app, parent, model in self.cases:
            child = type(parent).objects.create(user=self.owner, workplace=self.workspace, parent=parent, title='Podzadanie')
            for task in [parent, child]:
                for scoped in [False, True]:
                    with self.subTest(app=app, child=bool(task.parent_id), scoped=scoped):
                        response = self.post(app, task, [photo(), photo('kolejne.png')], scoped=scoped)
                        self.assertEqual(response.status_code, 200)
                        activity = task.activities.filter(kind='comment').latest('pk')
                        self.assertEqual(activity.actor, self.member)
                        self.assertEqual(activity.message, '')
                        self.assertEqual(activity.images.count(), 2)
                        self.assertFalse(task.attachments.exists())
                        self.assertIn('tasks-comment-image', response.json()['activity_html'])
                        page = self.client.get(self.url(app, task, scoped), {'task_pk': task.pk}, follow=True)
                        self.assertContains(page, activity.images.first().get_url())
            response = self.post(app, parent, [photo()], text='Opis zdjęcia @owner')
            self.assertEqual(response.status_code, 200)
            activity = parent.activities.filter(kind='comment').latest('pk')
            self.assertEqual(activity.message, 'Opis zdjęcia @owner')
            activity_field = 'task_activity' if app == 'tasks' else 'kanban_activity'
            self.assertTrue(ActivityInterest.objects.filter(**{activity_field: activity}, user=self.owner, mentioned=True).exists())

    def test_text_only_and_native_post_still_work(self):
        for app, task, _ in self.cases:
            response = self.post(app, task, text='Zwykły komentarz', ajax=False)
            self.assertEqual(response.status_code, 302)
            response = self.post(app, task, [photo()], ajax=False)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(task.activities.filter(kind='comment').count(), 2)

    def test_invalid_batches_save_neither_comment_nor_files(self):
        for app, task, model in self.cases:
            for name, content in [('zly.png', b'not an image'), ('pusty.png', b''), ('skrypt.svg', b'<svg/>'), ('plik.exe', b'MZ program')]:
                with self.subTest(app=app, name=name):
                    response = self.post(app, task, [photo(), photo(name, content)], text='Zachowaj szkic')
                    self.assertEqual(response.status_code, 400)
                    self.assertFalse(task.activities.filter(kind='comment').exists())
                    self.assertFalse(model.objects.exists())
            self.assertFalse(any(Path(self.directory.name).rglob('*.png')))

    def test_empty_comment_count_and_size_limits(self):
        for app, task, _ in self.cases:
            self.assertEqual(self.post(app, task, text='  ').status_code, 400)
            self.assertEqual(self.post(app, task, [photo() for _ in range(11)]).status_code, 400)
            with override_settings(MAX_ATTACHMENT_SIZE=10):
                self.assertEqual(self.post(app, task, [photo()]).status_code, 400)
            self.assertFalse(task.activities.filter(kind='comment').exists())

    def test_native_validation_keeps_text_and_mentions(self):
        for app, task, _ in self.cases:
            response = self.post(app, task, [photo('bad.png', b'bad')], text='Mój szkic', ajax=False)
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Mój szkic</textarea>')
            self.assertContains(response, 'Załącznik ma nieprawidłową zawartość.')

    def test_private_content_headers_and_missing_file(self):
        for app, task, model in self.cases:
            self.post(app, task, [photo()])
            image = model.objects.get()
            for url in [image.get_url(), reverse(f'{app}:comment_image', args=[image.pk])]:
                response = self.client.get(url, follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response['Content-Type'], 'image/png')
                self.assertIn('inline;', response['Content-Disposition'])
                self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
                self.assertEqual(response['Cache-Control'], 'private, no-store')
                self.assertEqual(b''.join(response.streaming_content), PNG)
            with override_settings(DEBUG=True):
                self.assertEqual(self.client.get('/media/' + image.file.name).status_code, 404)
            image.file.storage.delete(image.file.name)
            self.assertEqual(self.client.get(image.get_url()).status_code, 404)

    def test_wrong_workspace_outsider_and_revoked_membership_cannot_access_images(self):
        images = []
        for app, task, model in self.cases:
            self.post(app, task, [photo()])
            images.append((app, model.objects.get()))
        self.login(self.owner, self.other)
        for app, image in images:
            self.assertEqual(self.client.get(reverse(f'{app}:comment_image', args=[image.pk]), follow=True).status_code, 404)
            wrong_scope = image.get_url().replace(self.workspace.slug, self.other.slug)
            self.assertEqual(self.client.get(wrong_scope).status_code, 404)
        # Assignment does not grant workspace membership.
        self.task.assignee = self.outsider
        self.task.save(update_fields=['assignee'])
        self.login(self.outsider)
        for app, task, _ in self.cases:
            response = self.post(app, task, [photo()])
            self.assertRedirects(response, reverse('workplaces:workplaces'), fetch_redirect_response=False)
            self.assertEqual(task.activities.filter(kind='comment').count(), 1)
        for _, image in images:
            self.assertRedirects(self.client.get(image.get_url()), reverse('workplaces:workplaces'), fetch_redirect_response=False)
        self.membership.delete()
        self.login(self.member)
        for _, image in images:
            self.assertRedirects(self.client.get(image.get_url()), reverse('workplaces:workplaces'), fetch_redirect_response=False)
        self.client.logout()
        for _, image in images:
            self.assertIn(self.client.get(image.get_url()).status_code, [302, 403, 404])

    def test_upload_requires_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.member)
        for app, task, _ in self.cases:
            response = client.post(self.url(app, task), {'task_pk': task.pk, 'action': 'add_activity_comment', 'comment_attachments': photo()})
            self.assertEqual(response.status_code, 403)
            self.assertFalse(task.activities.filter(kind='comment').exists())

    def test_storage_is_cleaned_if_database_save_fails(self):
        for app, task, model in self.cases:
            with patch.object(model, 'save', side_effect=RuntimeError('Test rollback')):
                with self.assertRaises(RuntimeError):
                    self.post(app, task, [photo()], text='@owner')
            self.assertFalse(task.activities.filter(kind='comment').exists())
            self.assertFalse(ActivityInterest.objects.exists())
            self.assertFalse(any(Path(self.directory.name).rglob('*.png')))

    def test_partial_batch_failure_removes_previously_saved_files(self):
        for app, task, model in self.cases:
            original_save = model.save
            def fail_second(instance, *args, **kwargs):
                if instance.filename == 'fail.png':
                    raise RuntimeError('Second image failed')
                return original_save(instance, *args, **kwargs)
            with patch.object(model, 'save', fail_second), self.assertRaises(RuntimeError):
                self.post(app, task, [photo(), photo('fail.png')])
            self.assertFalse(model.objects.exists())
            self.assertFalse(any(Path(self.directory.name).rglob('*.png')))

    def test_deletion_removes_files_only_after_commit(self):
        for app, task, model in self.cases:
            self.post(app, task, [photo()])
            image = model.objects.get()
            name, storage = image.file.name, image.file.storage
            with self.assertRaises(RuntimeError):
                with transaction.atomic():
                    image.activity.delete()
                    raise RuntimeError('Undo deletion')
            self.assertTrue(storage.exists(name))
            self.assertTrue(model.objects.filter(pk=image.pk).exists())
            with self.captureOnCommitCallbacks(execute=True):
                task.delete()
                self.assertTrue(storage.exists(name))
            self.assertFalse(storage.exists(name))
            self.assertFalse(model.objects.exists())

    def test_files_and_images_in_one_comment_and_file_only_messages(self):
        fixtures = [
            ('opis.txt', b'Zalacznik tekstowy', 'text/plain'),
            ('plan.pdf', b'%PDF-1.4\n%%EOF', 'application/pdf'),
            ('umowa.docx', b'PK\x03\x04test', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
            ('dane.xlsx', b'PK\x03\x04test', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ('materialy.zip', b'PK\x05\x06' + b'\0' * 18, 'application/zip'),
        ]
        for app, task, model in self.cases:
            for name, content, mime in fixtures:
                with self.subTest(app=app, filename=name):
                    response = self.post(app, task, [SimpleUploadedFile(name, content, content_type=mime)])
                    self.assertEqual(response.status_code, 200)
                    record = model.objects.latest('pk')
                    self.assertEqual(record.file_size, len(content))
                    self.assertFalse(record.is_image())
                    self.assertIn('download=', response.json()['activity_html'])
                    self.assertIn(record.filename, response.json()['activity_html'])
                    self.assertIn(record.get_formatted_size(), response.json()['activity_html'])
                    download = self.client.get(record.get_url())
                    self.assertIn('attachment;', download['Content-Disposition'])
                    self.assertEqual(download['X-Content-Type-Options'], 'nosniff')
                    self.assertEqual(download['Cache-Control'], 'private, no-store')
                    self.assertEqual(b''.join(download.streaming_content), content)
            response = self.post(app, task, [photo(), SimpleUploadedFile('notatka.txt', b'Materialy')], text='Zdjecie i dokument')
            self.assertEqual(response.status_code, 200)
            activity = task.activities.filter(kind='comment').latest('pk')
            self.assertEqual(activity.images.count(), 2)
            self.assertIn('tasks-comment-image', response.json()['activity_html'])
            self.assertIn('tasks-comment-file', response.json()['activity_html'])
            page = self.client.get(self.url(app, task), {'task_pk': task.pk})
            self.assertContains(page, 'notatka.txt')
            self.assertFalse(task.attachments.exists())

    def test_file_download_and_upload_keep_workspace_boundaries(self):
        for app, task, model in self.cases:
            response = self.post(app, task, [SimpleUploadedFile('dokument.pdf', b'%PDF-1.4\n%%EOF')])
            self.assertEqual(response.status_code, 200)
            file = model.objects.latest('pk')
            self.login(self.owner, self.other)
            url = file.get_url().replace(self.workspace.slug, self.other.slug)
            self.assertEqual(self.client.get(url).status_code, 404)
            self.login(self.outsider)
            self.assertRedirects(self.client.get(file.get_url()), reverse('workplaces:workplaces'), fetch_redirect_response=False)
            self.login(self.member)
        self.membership.delete()
        for _, _, model in self.cases:
            self.assertRedirects(self.client.get(model.objects.latest('pk').get_url()), reverse('workplaces:workplaces'), fetch_redirect_response=False)

    def test_legacy_image_field_and_combined_limit(self):
        for app, task, model in self.cases:
            payload = {'task_pk': task.pk, 'action': 'add_activity_comment', 'comment_images': photo()}
            response = self.client.post(self.url(app, task), payload)
            self.assertEqual(response.status_code, 302)
            saved = model.objects.get()
            self.assertTrue(saved.is_image())
            payload['comment_images'] = [photo() for _ in range(6)]
            payload['comment_attachments'] = [SimpleUploadedFile('n.txt', b'n') for _ in range(5)]
            response = self.client.post(self.url(app, task), payload, headers={'X-Requested-With': 'XMLHttpRequest'})
            self.assertEqual(response.status_code, 400)
            self.assertEqual(model.objects.count(), 1)

    def test_nonimage_payload_with_html_is_always_downloaded(self):
        for app, task, model in self.cases:
            response = self.post(app, task, [SimpleUploadedFile('<script>.txt', b'<script>alert(1)</script>', content_type='text/html')])
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('<script>', response.json()['activity_html'])
            file = model.objects.get()
            download = self.client.get(file.get_url())
            self.assertEqual(download['Content-Type'], 'text/plain')
            self.assertIn('attachment;', download['Content-Disposition'])

    def test_file_batch_rollback_and_committed_deletion_clean_storage(self):
        for app, task, model in self.cases:
            with patch.object(model, 'save', side_effect=RuntimeError('Rollback file')), self.assertRaises(RuntimeError):
                self.post(app, task, [SimpleUploadedFile('n.txt', b'Notatka')])
            self.assertFalse(task.activities.filter(kind='comment').exists())
            self.assertFalse(any(path.is_file() for path in Path(self.directory.name).rglob('*')))
            self.post(app, task, [SimpleUploadedFile('n.txt', b'Notatka')])
            saved = model.objects.get()
            storage, name = saved.file.storage, saved.file.name
            with self.captureOnCommitCallbacks(execute=True):
                saved.activity.delete()
            self.assertFalse(storage.exists(name))
