"""Task privacy and direct grants across UI, inherited scope and integrations."""
import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from dashboard.notification_service import notification_page, notification_summary
from dashboard.reminders import reminders_for_user
from tasks.access import editable_to, visible_to
from tasks.models import (Task, TaskActivity, TaskAttachment, TaskMembership, TaskProject,
                          TaskProjectMembership, TaskSection, TaskSectionMembership, TaskWorkLog)
from tasks.project_templates import save_project_template
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class TaskSharingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner, cls.creator, cls.admin, cls.member, cls.outsider = [
            get_user_model().objects.create_user(username=name, email=f'{name}@task-sharing.test')
            for name in ['owner', 'creator', 'admin', 'member', 'outsider']
        ]
        cls.workspace = create_workplace_for_user(cls.owner, 'Zadania prywatne')
        cls.other = create_workplace_for_user(cls.owner, 'Druga przestrzeń')
        for user in [cls.creator, cls.admin, cls.member]:
            WorkplaceMembership.objects.create(workplace=cls.workspace, user=user)
        cls.project = TaskProject.objects.create(user=cls.owner, workplace=cls.workspace, name='Publiczny projekt')
        cls.section = TaskSection.objects.create(project=cls.project, title='Publiczna grupa')
        cls.second_section = TaskSection.objects.create(project=cls.project, title='Druga grupa')
        cls.task = Task.objects.create(user=cls.owner, workplace=cls.workspace, section=cls.section,
            title='Poufny plan zadania', visibility='private', private_owner=cls.creator, assignee=cls.member)
        cls.child = Task.objects.create(user=cls.owner, section=cls.second_section, parent=cls.task, title='Poufne stare podzadanie')
        cls.note = TaskActivity.objects.create(task=cls.task, kind='comment', action='commented', actor=cls.creator, message='Tajemnica czatu')
        cls.file = TaskAttachment.objects.bulk_create([TaskAttachment(task=cls.task, file='task_attachments/secret.txt', file_size=4)])[0]
        cls.log = TaskWorkLog.objects.create(task=cls.task, author=cls.creator,
            started_at=timezone.now()-timedelta(minutes=30), ended_at=timezone.now())
        cls.admin_grant = TaskMembership.objects.create(task=cls.task, user=cls.admin, role='admin')

    def setUp(self):
        self.login(self.creator)

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, suffix=''):
        return scoped_workplace_app_path(self.workspace, 'tasks', suffix)

    def detail(self, task=None):
        task = task or self.task
        return self.url(f'view-task/{task.task_id}/?task_pk={task.pk}')

    def team(self, task=None, **data):
        return self.client.post(self.url(f'items/{(task or self.task).pk}/team/'), data)

    def share(self, role='member', task=None):
        response = self.team(task, action='share', email=self.member.email.upper(), role=role)
        self.assertEqual(response.status_code, 200, response.content[:500])
        return TaskMembership.objects.get(task=task or self.task, user=self.member)

    def edit(self, task=None, **data):
        task = task or self.task
        return self.client.post(self.detail(task), {
            'task_pk': task.pk, 'title': task.title, 'section': task.section_id,
            'project': self.project.pk, 'status': task.status, 'priority': task.priority,
            'parent': task.parent_id or '', **data,
        })

    def test_private_content_and_legacy_descendants_are_hidden_even_from_workspace_owner(self):
        for user, access in [(self.creator, True), (self.admin, True), (self.member, False), (self.owner, False), (self.outsider, False)]:
            for obj in [self.task, self.child, self.note, self.file, self.log]:
                with self.subTest(user=user, obj=obj):
                    self.assertEqual(visible_to(type(obj).objects.all(), user).filter(pk=obj.pk).exists(), access)
        self.login(self.member)
        for base in [self.url(), reverse('tasks:tasks')]:
            for suffix in [f'view-task/{self.task.task_id}/?task_pk={self.task.pk}',
                           f'view-subtask/{self.child.task_id}/?task_pk={self.child.pk}',
                           f'attachments/{self.file.pk}/download/', f'items/{self.task.pk}/team/']:
                self.assertEqual(self.client.get(base+suffix, follow=True).status_code, 404)

    def test_direct_share_is_immediate_without_invitation_and_revocation_removes_tree(self):
        grant = self.share()
        self.assertTrue(visible_to(Task.objects.all(), self.member).filter(pk=self.child.pk).exists())
        self.assertEqual(notification_summary(self.member)['pending_invitation_count'], 0)
        self.login(self.member)
        for base in [self.url(), reverse('tasks:tasks')]:
            self.assertEqual(self.client.get(base + f'view-task/{self.task.task_id}/?task_pk={self.task.pk}', follow=True).status_code, 200)
        self.login(self.creator)
        self.assertEqual(self.team(action='remove', member_id=grant.pk).status_code, 200)
        self.assertFalse(visible_to(Task.objects.all(), self.member).filter(pk=self.child.pk).exists())

    def test_observer_is_readonly_and_owner_can_change_role(self):
        grant = self.share('observer')
        self.assertFalse(editable_to(Task.objects.all(), self.member).filter(pk=self.child.pk).exists())
        self.login(self.member)
        response = self.client.get(self.detail())
        self.assertContains(response, 'data-task-readonly="true"')
        self.assertNotContains(response, 'data-project-share-open')
        self.assertEqual(self.edit(title='Niedozwolona zmiana').status_code, 403)
        self.assertEqual(self.team(action='share', email=self.owner.email, role='member').status_code, 403)
        response = self.client.post(self.url(f'update/{self.task.task_id}/'), json.dumps({'task_pk': self.task.pk, 'status':'closed'}), content_type='application/json')
        self.assertEqual(response.status_code, 404)
        self.login(self.creator)
        self.assertEqual(self.team(action='role', member_id=grant.pk, role='member').status_code, 200)
        self.assertTrue(editable_to(Task.objects.all(), self.member).filter(pk=self.child.pk).exists())

    def test_administrator_can_share_members_not_admin_or_visibility(self):
        self.login(self.admin)
        self.assertEqual(self.team(action='share', email=self.member.email, role='admin').status_code, 400)
        grant = self.share('observer')
        self.assertEqual(self.team(action='role', member_id=grant.pk, role='member').status_code, 403)
        self.assertEqual(self.team(action='remove', member_id=self.admin_grant.pk).status_code, 403)
        self.assertEqual(self.edit(visibility='public').status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.visibility, 'private')
        self.assertEqual(self.team(action='remove', member_id=grant.pk).status_code, 200)

    def test_invalid_recipients_duplicates_csrf_and_wrong_scope_fail(self):
        for email in [self.outsider.email, self.creator.email, self.admin.email, 'missing@task-sharing.test']:
            self.assertEqual(self.team(action='share', email=email, role='member').status_code, 400)
        self.assertEqual(self.team(action='share', email=self.member.email, role='owner').status_code, 400)
        self.share()
        self.assertEqual(self.team(action='share', email=self.member.email, role='observer').status_code, 400)
        for pk in ['owner', '-1', '12345678901234567890']:
            self.assertEqual(self.team(action='remove', member_id=pk).status_code, 404)
        self.login(self.owner)
        wrong = scoped_workplace_app_path(self.other, 'tasks', f'items/{self.task.pk}/team/')
        self.assertEqual(self.client.get(wrong).status_code, 404)
        client=Client(enforce_csrf_checks=True); client.force_login(self.creator)
        self.assertEqual(client.post(self.url(f'items/{self.task.pk}/team/'), {'action':'share'}).status_code, 403)

    def test_candidates_are_active_eligible_people_and_exclude_members(self):
        endpoint = self.url(f'items/{self.task.pk}/team/candidates/')
        self.assertEqual(self.client.get(endpoint, {'q':'m'}).json()['results'], [])
        response = self.client.get(endpoint, {'q':'member'})
        self.assertEqual([x['email'] for x in response.json()['results']], [self.member.email])
        self.assertIn('no-store', response['Cache-Control'])
        self.share()
        self.assertEqual(self.client.get(endpoint, {'q':'member'}).json()['results'], [])

    def test_project_group_and_parent_are_permission_ceilings(self):
        self.section.visibility='private'; self.section.private_owner=self.creator; self.section.save(update_fields=['visibility', 'private_owner'])
        self.assertEqual(self.team(action='share', email=self.member.email, role='member').status_code, 400)
        group_grant = TaskSectionMembership.objects.create(section=self.section, user=self.member)
        self.share()
        child = Task.objects.create(user=self.owner, section=self.section, parent=self.task, title='Private child', visibility='private', private_owner=self.creator)
        self.share(task=child)
        group_grant.delete()
        self.assertFalse(TaskMembership.objects.filter(user=self.member).exists())
        TaskSectionMembership.objects.create(section=self.section, user=self.member)
        self.assertFalse(visible_to(Task.objects.all(), self.member).filter(pk=self.task.pk).exists())
        self.project.visibility='private'; self.project.private_owner=self.creator; self.project.save()
        self.assertEqual(self.team(action='share', email=self.member.email, role='member').status_code, 400)

    def test_parent_observer_cannot_manage_private_child_even_as_child_owner(self):
        self.share('observer')
        child = Task.objects.create(user=self.owner, section=self.section, parent=self.task, title='Owned child', visibility='private', private_owner=self.member)
        self.login(self.member)
        self.assertFalse(self.client.get(self.url(f'items/{child.pk}/team/')).json()['can_manage'])
        self.assertEqual(self.team(child, action='share', email=self.creator.email, role='member').status_code, 403)

    def test_revoke_parent_clears_child_grants_but_publishing_preserves_them(self):
        grant = self.share()
        self.child.visibility='private'; self.child.private_owner=self.creator; self.child.save()
        self.share(task=self.child)
        grant.delete()
        self.assertFalse(TaskMembership.objects.filter(task=self.child, user=self.member).exists())
        self.share(); self.share(task=self.child)
        self.assertEqual(self.edit(visibility='public').status_code, 302)
        self.assertTrue(TaskMembership.objects.filter(task=self.child, user=self.member).exists())
        self.assertFalse(TaskMembership.objects.filter(task=self.task).exists())

    def test_workspace_revocation_does_not_restore_old_grants_on_rejoin(self):
        self.share()
        membership=WorkplaceMembership.objects.get(workplace=self.workspace,user=self.member)
        membership.is_active=False; membership.save()
        self.assertFalse(TaskMembership.objects.filter(user=self.member).exists())
        membership.is_active=True; membership.save()
        self.assertFalse(visible_to(Task.objects.all(), self.member).filter(pk=self.task.pk).exists())

    def test_visibility_actual_creator_defaults_and_stale_form_preserves_private(self):
        response=self.client.post(self.url(), {'action':'create_task_modal','title':'Nowe prywatne', 'section':self.section.pk, 'status':'new', 'priority':'medium'})
        self.assertEqual(response.status_code,302)
        task=Task.objects.get(title='Nowe prywatne')
        self.assertEqual((task.visibility, task.private_owner_id, task.user_id),('private',self.creator.pk,self.owner.pk))
        self.assertEqual(self.edit(task, title='Zachowana prywatność').status_code,302)
        task.refresh_from_db();self.assertEqual(task.visibility,'private')
        response=self.client.post(self.url(), {'action':'create_task','title':'Szybkie prywatne','section_id':self.section.pk})
        self.assertEqual(response.status_code,302)
        self.assertEqual(Task.objects.get(title='Szybkie prywatne').private_owner_id,self.creator.pk)
        self.assertEqual(self.edit(task, visibility='internet').status_code,200)
        self.assertEqual(self.edit(task, shared_with=[self.member.pk], sharing_present='1').status_code,200)
        self.assertFalse(task.memberships.exists())

    def test_new_subtask_is_private_and_parent_history_does_not_leak_its_title(self):
        parent=Task.objects.create(user=self.owner,section=self.section,title='Publiczny rodzic')
        response=self.client.post(self.detail(parent),{'task_pk':parent.pk,'action':'create_subtask_modal','title':'Tajny nowy potomek','status':'new'})
        self.assertEqual(response.status_code,302)
        child=parent.subtasks.get()
        self.assertEqual(child.private_owner_id,self.creator.pk)
        history=parent.activities.get(action='subtask_created')
        self.assertEqual(history.metadata['subtask_pk'],child.pk)
        self.assertFalse(visible_to(TaskActivity.objects.all(),self.member).filter(pk=history.pk).exists())
        self.login(self.member)
        response=self.client.get(self.detail(parent))
        self.assertNotContains(response,child.title)
        notifications=notification_page(self.member,{'view':'all','workspace':''})
        self.assertNotIn(child.title,str(notifications))
        self.login(self.creator);self.share(task=child)
        self.assertTrue(visible_to(TaskActivity.objects.all(),self.member).filter(pk=history.pk).exists())

    def test_lists_search_calendar_notifications_metrics_and_templates_hide_private_task(self):
        self.login(self.member)
        for params in [{'view':'all-tasks'},{'view':'my-tasks'},{'project':self.project.pk},{'view':'all-groups','sort':'activity_desc'}]:
            response=self.client.get(self.url(),params)
            self.assertEqual(response.status_code,200)
            self.assertNotContains(response,self.task.title)
            self.assertNotContains(response,self.child.title)
        self.assertNotContains(self.client.get(reverse('global_search'),{'q':'Poufny'}),self.task.title)
        self.assertNotContains(self.client.get(scoped_workplace_app_path(self.workspace,'calendar')),self.task.title)
        template=save_project_template(self.project,self.member)
        self.assertEqual(template.structure['tasks'],[])
        template=save_project_template(self.project,self.creator)
        self.assertEqual(template.visibility,'private')
        self.assertEqual(template.private_owner_id,self.creator.pk)

    def test_cascade_cannot_delete_hidden_task_or_descendant(self):
        self.login(self.owner)
        self.assertEqual(self.client.post(self.url(),{'action':'delete_project','project_id':self.project.pk}).status_code,403)
        self.assertTrue(Task.objects.filter(pk=self.task.pk).exists())

    def test_private_owner_deletion_fails_closed_and_reminder_goes_to_private_owner(self):
        self.task.assignee=None;self.task.reminder_at=timezone.now()-timedelta(minutes=1);self.task.save()
        self.assertTrue(reminders_for_user(self.creator).filter(task=self.task).exists())
        self.assertFalse(reminders_for_user(self.owner).filter(task=self.task).exists())
        self.task.private_owner=None;self.task.save()
        self.assertFalse(visible_to(Task.objects.all(),self.admin).filter(pk=self.task.pk).exists())

    def test_mentions_exclude_people_without_task_access(self):
        from dashboard.collaboration import mention_people
        self.assertEqual(set(mention_people(self.task).values_list('pk', flat=True)), {self.creator.pk, self.admin.pk})
        self.share()
        self.assertTrue(mention_people(self.task).filter(pk=self.member.pk).exists())

    def test_ajax_visibility_save_updates_members_panel(self):
        response=self.client.post(self.detail(),{'task_pk':self.task.pk,'title':self.task.title,'section':self.section.pk,
            'status':'new','priority':'medium','visibility':'public'},HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code,200)
        self.assertIn('Zadanie publiczne',response.json()['team']['members'])
        self.assertFalse(response.json()['team']['can_manage'])


class TaskSharingMigrationTests(TransactionTestCase):
    def test_existing_tasks_keep_access_and_child_history_uses_stable_pk(self):
        executor=MigrationExecutor(connection);latest=executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda:MigrationExecutor(connection).migrate(latest))
        user=get_user_model().objects.create_user(username='task-migration',email='task-migration@task.test')
        executor.migrate([('tasks','0059_direct_sharing')])
        apps=executor.loader.project_state([('tasks','0059_direct_sharing')]).apps
        OldTask=apps.get_model('tasks','Task');Activity=apps.get_model('tasks','TaskActivity')
        parent=OldTask.objects.create(user_id=user.pk,title='Parent',task_id=1)
        child=OldTask.objects.create(user_id=user.pk,title='Child',parent=parent,task_id=2)
        event=Activity.objects.create(task=parent,action='subtask_created',metadata={'subtask_title':'Child','subtask_task_id':2})
        stale=Activity.objects.create(task=parent,action='subtask_created',metadata={'subtask_title':'Gone','subtask_task_id':3})
        MigrationExecutor(connection).migrate(latest)
        restored=Task.objects.get(pk=child.pk)
        self.assertEqual(restored.visibility,'public');self.assertIsNone(restored.private_owner_id)
        self.assertFalse(restored.memberships.exists())
        self.assertEqual(TaskActivity.objects.get(pk=event.pk).metadata['subtask_pk'],child.pk)
        self.assertNotIn('subtask_title',TaskActivity.objects.get(pk=stale.pk).metadata)
