"""Workspace-only project grants must apply to all existing privacy boundaries."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .access import visible_to
from .models import Task, TaskActivity, TaskProject, TaskSection


class ProjectSharingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='share-owner', email='owner@share.test')
        cls.author = users.objects.create_user(username='share-author', email='author@share.test')
        cls.member = users.objects.create_user(username='share-member', email='member@share.test')
        cls.outsider = users.objects.create_user(username='share-outsider', email='outsider@share.test')
        cls.inactive = users.objects.create_user(username='share-inactive', email='inactive@share.test', is_active=False)
        cls.workspace = create_workplace_for_user(cls.owner, 'Udostępnianie')
        cls.other = create_workplace_for_user(cls.owner, 'Inna przestrzeń')
        for user in [cls.author, cls.member, cls.inactive]:
            WorkplaceMembership.objects.create(workplace=cls.workspace, user=user)
        WorkplaceMembership.objects.create(workplace=cls.other, user=cls.outsider)
        cls.project = TaskProject.objects.create(user=cls.owner, workplace=cls.workspace, name='Poufna strategia',
                                                 visibility='private', private_owner=cls.author)
        cls.section = TaskSection.objects.create(project=cls.project, title='Poufna grupa')
        cls.task = Task.objects.create(user=cls.owner, section=cls.section, title='Poufne zadanie', due_at=timezone.now())
        cls.child = Task.objects.create(user=cls.owner, section=cls.section, parent=cls.task, title='Poufne podzadanie')
        cls.activity = TaskActivity.objects.create(task=cls.task, actor=cls.author, action='commented', kind='comment', message='Poufny komentarz')

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, suffix=''):
        return scoped_workplace_app_path(self.workspace, 'tasks', suffix)

    def setUp(self):
        self.login(self.author)

    def test_removed_or_disabled_members_do_not_recover_grants_on_rejoining(self):
        for remove in [False, True]:
            self.project.shared_with.add(self.member)
            membership = WorkplaceMembership.objects.get(workplace=self.workspace, user=self.member)
            if remove:
                membership.delete()
                WorkplaceMembership.objects.create(workplace=self.workspace, user=self.member)
            else:
                membership.is_active = False
                membership.save(update_fields=['is_active'])
                membership.is_active = True
                membership.save(update_fields=['is_active'])
            self.assertFalse(self.project.shared_with.filter(pk=self.member.pk).exists())
            self.assertFalse(visible_to(TaskProject.objects.all(), self.member).filter(pk=self.project.pk).exists())

    def test_wrong_workspace_or_deleted_owner_still_denies_grants(self):
        self.project.shared_with.add(self.outsider, self.member)
        self.assertFalse(visible_to(TaskProject.objects.all(), self.outsider).filter(pk=self.project.pk).exists())
        self.author.delete()
        self.assertFalse(visible_to(TaskProject.objects.all(), self.member).filter(pk=self.project.pk).exists())

    def test_new_workspace_member_does_not_inherit_private_access(self):
        self.project.shared_with.add(self.member)
        WorkplaceMembership.objects.create(workplace=self.workspace, user=self.outsider)
        self.assertFalse(visible_to(TaskProject.objects.all(), self.outsider).filter(pk=self.project.pk).exists())
