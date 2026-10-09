from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase

from spaces.models import WorkItem
from tasks.hierarchy import save_task_edit
from tasks.models import Task, TaskMembership, TaskProject, TaskProjectMembership, TaskSection, TaskTag
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class TaskLocationEditTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='move-owner', email='move-owner@example.test')
        self.member = get_user_model().objects.create_user(username='move-member', email='move-member@example.test')
        self.workspace = create_workplace_for_user(self.owner, 'Task locations')
        WorkplaceMembership.objects.create(workplace=self.workspace, user=self.member)
        self.source = TaskProject.objects.create(user=self.owner, workplace=self.workspace, name='Source', visibility='private', private_owner=self.owner)
        self.target = TaskProject.objects.create(user=self.owner, workplace=self.workspace, name='Target', visibility='private', private_owner=self.owner)
        for project in (self.source, self.target):
            TaskProjectMembership.objects.create(project=project, user=self.member, role='member')
        self.section = TaskSection.objects.create(project=self.source, title='Source group')
        self.target_section = TaskSection.objects.create(project=self.target, title='Target group')
        self.root = Task.objects.create(user=self.owner, section=self.section, title='Root')
        self.child = Task.objects.create(user=self.owner, section=self.section, parent=self.root, title='Child')
        self.grandchild = Task.objects.create(user=self.owner, section=self.section, parent=self.child, title='Grandchild')
        self.tag = TaskTag.objects.create(user=self.owner, workplace=self.workspace, space=self.source.space, name='Source tag')
        self.target_tag = TaskTag.objects.create(user=self.owner, workplace=self.workspace, space=self.target.space, name='Target tag')
        self.root.tags.add(self.tag)
        self.client.force_login(self.member)

    def task_url(self, task=None, scoped=True):
        task = task or self.root
        path = f'view-task/{task.task_id}/?task_pk={task.pk}'
        return scoped_workplace_app_path(self.workspace, 'tasks', path) if scoped else '/tasks/' + path

    def edit_url(self, scoped=True):
        path = f'items/{self.root.work_item.pk}/edit/'
        return scoped_workplace_app_path(self.workspace, 'spaces', path) if scoped else '/spaces/' + path

    def payload(self, **overrides):
        data = {'task_pk': self.root.pk, 'title': 'Edited root', 'visibility': 'public',
                'priority': 'medium', 'status': 'new', 'task_type': 'general', 'tags': [self.tag.pk]}
        data.update(overrides)
        return data

    def location_snapshot(self):
        return (list(Task.objects.order_by('pk').values_list('pk', 'section_id', 'parent_id', 'workplace_id', 'task_id', 'code_number')),
                list(WorkItem.objects.order_by('pk').values_list('task_id', 'space_id', 'key', 'status', 'team_id', 'sprint_id', 'epic_id')))

    def test_detail_ignores_posted_location_and_preserves_entire_tree(self):
        same_project_group = TaskSection.objects.create(project=self.source, title='Second group')
        before = self.location_snapshot()
        for scoped in (False, True):
            for section in (self.target_section, same_project_group):
                with self.subTest(scoped=scoped, section=section.pk):
                    response = self.client.post(self.task_url(scoped=scoped), self.payload(project=section.project_id, section=section.pk))
                    self.assertEqual(response.status_code, 302)
                    self.assertEqual(self.location_snapshot(), before)
                    self.root.refresh_from_db()
                    self.assertEqual(self.root.title, 'Edited root')
                    self.assertEqual(list(self.root.tags.all()), [self.tag])
        self.assertFalse(self.child.activities.filter(action='updated').exists())
        self.assertFalse(self.grandchild.activities.filter(action='updated').exists())
        self.assertEqual(self.root.activities.get(action='updated').actor, self.member)

    def test_ajax_edit_without_location_and_with_empty_or_invalid_location(self):
        before = self.location_snapshot()
        for scoped in (False, True):
            for location in ({}, {'project': '', 'section': ''}, {'project': 'invalid', 'section': 'invalid'}):
                with self.subTest(scoped=scoped, location=location):
                    response = self.client.post(self.task_url(scoped=scoped), self.payload(**location), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()['status'], 'success')
                    self.assertEqual(self.location_snapshot(), before)

    def test_unassigned_task_stays_unassigned_when_location_is_posted(self):
        task = Task.objects.create(user=self.owner, workplace=self.workspace, title='Unassigned')
        before = self.location_snapshot()
        response = self.client.post(self.task_url(task), self.payload(task_pk=task.pk, project=self.target.pk, section=self.target_section.pk, tags=[]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.location_snapshot(), before)

    def test_edits_do_not_require_access_to_hidden_or_observed_descendants(self):
        self.child.visibility, self.child.private_owner = 'private', self.owner
        self.child.save(update_fields=['visibility', 'private_owner'])
        before = self.location_snapshot()
        for shared in (False, True):
            with self.subTest(observed=shared):
                if shared:
                    TaskMembership.objects.create(task=self.child, user=self.member, role='observer')
                response = self.client.post(self.task_url(), self.payload(section=self.target_section.pk))
                self.assertEqual(response.status_code, 302)
                self.assertEqual(self.location_snapshot(), before)

    def test_space_edit_ignores_location_without_defaulting_to_another_group(self):
        another = TaskSection.objects.create(project=self.source, title='Another group')
        before = self.location_snapshot()
        for scoped in (False, True):
            for location in ({}, {'section': ''}, {'section': another.pk}, {'section': self.target_section.pk}):
                with self.subTest(scoped=scoped, location=location):
                    response = self.client.post(self.edit_url(scoped=scoped), self.payload(work_type='task', **location))
                    self.assertEqual(response.status_code, 302)
                    self.assertEqual(self.location_snapshot(), before)
                    self.assertEqual(list(self.root.tags.all()), [self.tag])

    def test_tag_and_issue_type_validation_uses_existing_space(self):
        config = self.source.space.configuration
        config.settings = {**config.settings, 'types': [{'key': 'source', 'label': 'Source type'}]}
        config.save(update_fields=['settings'])
        item = self.root.work_item
        item.work_type = 'source'
        item.save(update_fields=['work_type'])
        before = self.location_snapshot()
        response = self.client.post(self.task_url(), self.payload(project=self.target.pk, section=self.target_section.pk, work_type='source'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.location_snapshot(), before)
        for overrides in ({'tags': [self.target_tag.pk]}, {'work_type': 'task'}):
            response = self.client.post(self.task_url(), self.payload(project=self.target.pk, section=self.target_section.pk, **overrides))
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['form'].errors)
            self.assertEqual(self.location_snapshot(), before)
            self.assertEqual(list(self.root.tags.all()), [self.tag])

    def test_parent_selection_cannot_move_subtask_to_another_group(self):
        target_parent = Task.objects.create(user=self.owner, section=self.target_section, title='Target parent')
        before = self.location_snapshot()
        response = self.client.post(self.task_url(self.child), self.payload(task_pk=self.child.pk, parent=target_parent.pk, tags=[]))
        self.assertEqual(response.status_code, 200)
        self.assertIn('parent', response.context['form'].errors)
        self.assertEqual(self.location_snapshot(), before)
        parent = Task.objects.create(user=self.owner, section=self.section, title='Same group parent')
        response = self.client.post(self.task_url(self.child), self.payload(task_pk=self.child.pk, parent=parent.pk, tags=[]))
        self.assertEqual(response.status_code, 302)
        self.child.refresh_from_db()
        self.assertEqual(self.child.parent, parent)
        self.assertEqual(self.child.section, self.section)

    def test_forms_omit_location_information_and_have_no_transfer_fields(self):
        for scoped in (False, True):
            response = self.client.get(self.task_url(scoped=scoped))
            self.assertNotIn('project', response.context['form'].fields)
            self.assertNotIn('section', response.context['form'].fields)
            self.assertNotContains(response, f'<strong title="{self.source.name}">{self.source.name}</strong>', html=True)
            self.assertNotContains(response, f'<strong title="{self.section.title}">{self.section.title}</strong>', html=True)
            response = self.client.get(self.edit_url(scoped=scoped), HTTP_X_WORK_MODAL='true')
            self.assertNotContains(response, 'name="section"')
            response = self.client.get(scoped_workplace_app_path(self.workspace, 'spaces', f'{self.source.space.pk}/items/create/'))
            self.assertContains(response, 'name="section"')

    def test_observer_cannot_edit_or_transfer_a_task(self):
        membership = self.source.memberships.get(user=self.member)
        membership.role = 'observer'
        membership.save(update_fields=['role'])
        before = self.location_snapshot()
        for url in (self.task_url(), self.edit_url()):
            self.assertEqual(self.client.post(url, self.payload(section=self.target_section.pk)).status_code, 403)
        self.assertEqual(self.location_snapshot(), before)
        self.root.refresh_from_db()
        self.assertEqual(self.root.title, 'Root')

    def test_save_helper_rejects_changes_to_group_or_parent_location(self):
        before = self.location_snapshot()
        self.root.section = self.target_section
        with self.assertRaises(PermissionDenied):
            save_task_edit(self.root, self.member)
        self.child.parent = Task.objects.create(user=self.owner, section=self.target_section, title='Target parent')
        before_parent = self.location_snapshot()
        with self.assertRaises(PermissionDenied):
            save_task_edit(self.child, self.member)
        self.assertEqual(self.location_snapshot(), before_parent)
        self.assertEqual(self.location_snapshot()[0][:3], before[0])
