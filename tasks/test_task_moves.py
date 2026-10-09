from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from spaces.models import WorkItem
from tasks.models import Task, TaskMembership, TaskProject, TaskProjectMembership, TaskSection
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class TaskTreeMoveTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='move-owner', email='move-owner@example.test')
        self.member = get_user_model().objects.create_user(username='move-member', email='move-member@example.test')
        self.workspace = create_workplace_for_user(self.owner, 'Task moves')
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
        self.client.force_login(self.member)
        self.url = scoped_workplace_app_path(self.workspace, 'tasks', f'view-task/{self.root.task_id}/')

    def move(self, target_section=None, **overrides):
        section = target_section or self.target_section
        data = {'task_pk': self.root.pk, 'title': self.root.title, 'project': section.project_id, 'section': section.pk,
                'visibility': 'public', 'priority': 'medium', 'status': 'new', 'task_type': 'general'}
        data.update(overrides)
        return self.client.post(self.url, data)

    def test_move_keeps_full_tree_together_and_survives_old_group_deletion(self):
        original_ids = dict(Task.objects.values_list('pk', 'task_id'))
        child_keys = dict(WorkItem.objects.values_list('task_id', 'key'))
        self.assertEqual(self.move().status_code, 302)
        for task in (self.root, self.child, self.grandchild):
            task.refresh_from_db()
            self.assertEqual(task.section, self.target_section)
            self.assertEqual(task.workplace, self.workspace)
            self.assertEqual(task.task_id, original_ids[task.pk])
            self.assertEqual(task.work_item.space, self.target.space)
            self.assertEqual(task.work_item.key, child_keys[task.pk])
        numbers = list(Task.objects.values_list('code_number', flat=True))
        self.assertEqual(len(numbers), len(set(numbers)))
        for child in (self.child, self.grandchild):
            activity = child.activities.get(action='updated')
            self.assertEqual(activity.actor, self.member)
            self.assertEqual(activity.metadata['changes'][0]['from_label'], self.section.title)
        response = self.client.post(scoped_workplace_app_path(self.workspace, 'tasks'), {'action': 'delete_section', 'section_id': self.section.pk})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Task.objects.count(), 3)

    def test_move_is_blocked_for_hidden_or_observed_descendant(self):
        self.child.visibility, self.child.private_owner = 'private', self.owner
        self.child.save(update_fields=['visibility', 'private_owner'])
        for shared in (False, True):
            with self.subTest(observed=shared):
                if shared:
                    TaskMembership.objects.create(task=self.child, user=self.member, role='observer')
                response = self.move()
                self.assertEqual(response.status_code, 200)
                self.assertIn('section', response.context['form'].errors)
                self.assertFalse(Task.objects.exclude(section=self.section).exists())
                self.assertFalse(WorkItem.objects.exclude(space=self.source.space).exists())

    def test_same_group_edit_does_not_require_access_to_hidden_child(self):
        self.child.visibility, self.child.private_owner = 'private', self.owner
        self.child.save(update_fields=['visibility', 'private_owner'])
        response = self.move(self.section, title='Edited root')
        self.assertEqual(response.status_code, 302)
        self.root.refresh_from_db()
        self.assertEqual(self.root.title, 'Edited root')

    def test_detach_from_space_moves_descendants_to_unassigned_tasks(self):
        response = self.move(project='', section='')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Task.objects.filter(section__isnull=False).exists())
        self.assertFalse(WorkItem.objects.filter(space__isnull=False).exists())

    def test_failed_descendant_save_rolls_back_entire_move(self):
        original_save = Task.save

        def fail_child(task, *args, **kwargs):
            if task.pk == self.child.pk:
                raise RuntimeError('Cannot save child')
            return original_save(task, *args, **kwargs)

        with patch.object(Task, 'save', fail_child), self.assertRaisesMessage(RuntimeError, 'Cannot save child'):
            self.move()
        self.assertFalse(Task.objects.exclude(section=self.section).exists())
        self.assertFalse(WorkItem.objects.exclude(space=self.source.space).exists())

    def test_space_item_edit_uses_the_same_tree_move(self):
        target_group = TaskSection.objects.create(project=self.source, title='Second group')
        response = self.client.post(scoped_workplace_app_path(self.workspace, 'spaces', f'items/{self.root.work_item.pk}/edit/'), {
            'title': self.root.title, 'work_type': 'task', 'priority': 'medium', 'section': target_group.pk,
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Task.objects.exclude(section=target_group).exists())
