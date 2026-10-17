from django.contrib.auth import get_user_model
from django.test import TestCase

from spaces.models import WorkItem, SpaceTask
from spaces.testing import make_space
from tasks.models import Task, TaskProject, TaskProjectMembership, TaskSection, TaskTag
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
        self.space = make_space(user=self.owner, workplace=self.workspace, name='Osobna przestrzeń')
        self.other_space = make_space(user=self.owner, workplace=self.workspace, name='Inna przestrzeń')
        self.space_task = SpaceTask.objects.create(space=self.space, title='Osobne zadanie', created_by=self.owner)
        self.tag = TaskTag.objects.create(user=self.owner, workplace=self.workspace, space=self.space, name='Source tag')
        self.target_tag = TaskTag.objects.create(user=self.owner, workplace=self.workspace, space=self.other_space, name='Target tag')
        self.client.force_login(self.member)

    def edit_url(self, scoped=True):
        path = f'items/{self.space_task.work_item.pk}/edit/'
        return scoped_workplace_app_path(self.workspace, 'spaces', path) if scoped else '/spaces/' + path

    def location_snapshot(self):
        return (list(Task.objects.order_by('pk').values_list('pk', 'section_id', 'parent_id', 'workplace_id', 'task_id', 'code_number')),
                list(WorkItem.objects.order_by('pk').values_list('task_id', 'space_id', 'key', 'status', 'team_id', 'sprint_id', 'epic_id')))

    def test_space_edit_ignores_legacy_location(self):
        before = self.location_snapshot()
        for scoped in (False, True):
            response = self.client.post(self.edit_url(scoped=scoped), {'title': 'Nowy tytuł', 'priority': 'medium', 'work_type': 'task', 'project': self.target.pk, 'section': self.target_section.pk})
            self.assertEqual(response.status_code, 302)
            self.assertEqual(self.location_snapshot(), before)
            self.space_task.refresh_from_db()
            self.assertEqual(self.space_task.space, self.space)
            self.assertEqual(self.space_task.title, 'Nowy tytuł')

    def test_retired_edits_cannot_change_group_or_parent_location(self):
        before = self.location_snapshot()
        for prefix in ['/tasks/', scoped_workplace_app_path(self.workspace, 'tasks')]:
            response = self.client.post(prefix, {
                'action': 'edit_task', 'task_id': self.root.pk, 'section': self.target_section.pk,
                'parent': self.child.pk, 'title': 'Nie zmieniaj',
            })
            self.assertEqual(response.status_code, 409)
            self.assertEqual(self.location_snapshot(), before)
