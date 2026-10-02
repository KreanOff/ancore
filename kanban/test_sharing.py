"""Kanban sharing, inherited restrictions and every externally reachable entry point."""
import json
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from dashboard.collaboration import mention_people
from dashboard.notification_service import notification_sources
from tasks.access import visible_to, editable_to
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .forms import KanbanModalForm
from .models import (Kanban, KanbanActivity, KanbanAttachment, KanbanBoardColumn,
                     KanbanProject, KanbanProjectMembership, KanbanProjectNote,
                     KanbanSection, KanbanSectionMembership)


class KanbanSharingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner, cls.admin, cls.member, cls.outsider = [get_user_model().objects.create_user(
            username=name, email=f'{name}@kanban-sharing.test') for name in ['owner', 'admin', 'member', 'outsider']]
        cls.workspace = create_workplace_for_user(cls.owner, 'Kanban zespołu')
        cls.other = create_workplace_for_user(cls.owner, 'Drugi Workspace')
        for person in [cls.admin, cls.member]:
            WorkplaceMembership.objects.create(workplace=cls.workspace, user=person, role='admin' if person == cls.admin else 'member')
        cls.project = KanbanProject.objects.create(user=cls.owner, workplace=cls.workspace, name='Poufna przestrzeń', visibility='private', private_owner=cls.owner)
        cls.board = KanbanSection.objects.create(project=cls.project, title='Poufna tablica')
        cls.column = KanbanBoardColumn.objects.create(section=cls.board, title='Start')
        cls.card = Kanban.objects.create(user=cls.owner, workplace=cls.workspace, section=cls.board, column=cls.column, title='Poufna karta', due_at=timezone.now())
        cls.public = KanbanProject.objects.create(user=cls.owner, workplace=cls.workspace, name='Publiczna przestrzeń')
        cls.public_board = KanbanSection.objects.create(project=cls.public, title='Publiczna tablica')
        cls.public_column = KanbanBoardColumn.objects.create(section=cls.public_board, title='Start')
        # Legacy cross-board descendant still inherits the parent's restrictions.
        cls.child = Kanban.objects.create(user=cls.owner, workplace=cls.workspace, section=cls.public_board, parent=cls.card, title='Poufna podkarta')
        cls.public_card = Kanban.objects.create(user=cls.owner, workplace=cls.workspace, section=cls.public_board, column=cls.public_column, title='Publiczna karta')
        cls.note = KanbanProjectNote.objects.create(project=cls.project, author=cls.owner, message='Poufna notatka')
        cls.attachment = KanbanAttachment.objects.bulk_create([KanbanAttachment(task=cls.card, file='kanban_attachments/private.txt', file_size=4)])[0]
        cls.activity = KanbanActivity.objects.create(task=cls.card, actor=cls.owner, action='created', message='Poufna aktywność')

    def setUp(self):
        self.login(self.owner)

    def login(self, person):
        self.client.force_login(person)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, suffix=''):
        return scoped_workplace_app_path(self.workspace, 'kanban', suffix)

    def team(self, kind='project', **data):
        suffix = f'projects/{self.project.pk}/team/' if kind == 'project' else f'groups/{self.board.pk}/team/'
        return self.client.post(self.url(suffix), data)

    def share(self, person=None, role='member', kind='project'):
        person = person or self.member
        response = self.team(kind, action='share', email=person.email.upper(), role=role)
        self.assertEqual(response.status_code, 200, response.content[:300])
        return (self.project if kind == 'project' else self.board).memberships.get(user=person)

    def private_board(self):
        self.board.visibility = 'private'
        self.board.private_owner = self.owner
        self.board.save()

    def post_json(self, suffix, **data):
        return self.client.post(self.url(suffix), json.dumps(data), content_type='application/json')

    def test_workspace_admin_cannot_bypass_private_project_or_its_tree(self):
        for viewer in [self.owner, self.admin, self.member, self.outsider]:
            for model, obj in [(KanbanProject, self.project), (KanbanSection, self.board), (Kanban, self.card),
                               (Kanban, self.child), (KanbanBoardColumn, self.column), (KanbanProjectNote, self.note),
                               (KanbanAttachment, self.attachment), (KanbanActivity, self.activity)]:
                with self.subTest(viewer=viewer, model=model):
                    self.assertEqual(visible_to(model.objects.all(), viewer).filter(pk=obj.pk).exists(), viewer == self.owner)
        self.login(self.admin)
        for base in [self.url(), '/kanban/']:
            for suffix in [f'?project={self.project.pk}', f'groups/{self.board.pk}/', f'projects/{self.project.pk}/team/',
                           f'view-task/{self.card.task_id}/?task_pk={self.card.pk}',
                           f'view-subtask/{self.child.task_id}/?task_pk={self.child.pk}',
                           f'attachments/{self.attachment.pk}/download/']:
                with self.subTest(suffix=suffix):
                    self.assertEqual(self.client.get(base + suffix, follow=True).status_code, 404)

    def test_immediate_sharing_and_catalogs_on_both_routes(self):
        self.share()
        self.login(self.member)
        for base in [self.url(), '/kanban/']:
            for view, key, item in [('projects', 'project_window', self.project), ('all-groups', 'section_window', self.board)]:
                response = self.client.get(base, {'view':view, 'tab':'shared'}, follow=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn(item.pk, [obj.pk for obj in response.context[key]['projects' if view == 'projects' else 'sections']])
            self.assertEqual(self.client.get(base+f'groups/{self.board.pk}/', follow=True).status_code, 200)
            response = self.client.get(base + f'projects/{self.project.pk}/team/', follow=True)
            self.assertFalse(response.json()['can_manage'])
            self.assertIn(self.member.email, response.json()['members'])
        self.assertTrue(visible_to(Kanban.objects.all(), self.member).filter(pk=self.child.pk).exists())

    def test_board_creation_picker_only_offers_editable_workspace_projects(self):
        self.share(role='observer')
        KanbanProject.objects.create(user=self.owner, workplace=self.other, name='Inny Workspace')
        self.login(self.member)
        for base in [self.url(), '/kanban/']:
            response = self.client.get(base, {'view': 'all-groups'}, follow=True)
            self.assertTrue(response.context['section_create_uses_project_select'])
            self.assertEqual([project.pk for project in response.context['section_create_projects']], [self.public.pk])
            self.assertContains(response, 'data-section-create-project-select')
        self.assertEqual(self.client.post(self.url(), {
            'action': 'create_section', 'project_id': self.project.pk,
            'title': 'Niedozwolona tablica', 'visibility': 'private',
        }).status_code, 403)
        self.assertEqual(self.client.post(self.url(), {
            'action': 'create_section', 'project_id': self.public.pk,
            'title': 'Nowa tablica', 'visibility': 'private',
        }).status_code, 302)
        self.assertTrue(KanbanSection.objects.filter(project=self.public, title='Nowa tablica', private_owner=self.member).exists())
        response = self.client.get(self.url(), {'project': self.public.pk})
        self.assertFalse(response.context['section_create_uses_project_select'])
        self.assertNotContains(response, 'data-section-create-project-select')

    def test_role_matrix_and_invalid_recipients(self):
        self.share(self.admin, 'admin')
        for email in [self.outsider.email, self.owner.email, self.admin.email, 'missing@kanban-sharing.test']:
            self.assertEqual(self.team(action='share', email=email, role='member').status_code, 400)
        member = self.share(role='observer')
        self.login(self.admin)
        self.assertEqual(self.team(action='role', member_id=member.pk, role='admin').status_code, 403)
        self.assertEqual(self.team(action='share', email=self.member.email, role='admin').status_code, 400)
        self.assertEqual(self.team(action='remove', member_id=member.pk).status_code, 200)
        member = self.share(role='member')
        self.login(self.owner)
        self.assertEqual(self.team(action='role', member_id=member.pk, role='admin').status_code, 200)
        self.assertEqual(self.team(action='invite', email=self.member.email).status_code, 400)

    def test_candidates_narrow_to_project_and_revalidate_membership(self):
        self.private_board()
        self.assertEqual(self.team('section', action='share', email=self.member.email, role='member').status_code, 400)
        self.share()
        candidates = self.client.get(self.url(f'groups/{self.board.pk}/team/candidates/'), {'q':'kanban-sharing'})
        self.assertEqual([person['email'] for person in candidates.json()['results']], [self.member.email])
        self.share(kind='section')
        self.assertEqual(self.client.get(self.url(f'groups/{self.board.pk}/team/candidates/'), {'q':'member'}).json()['results'], [])
        self.project.memberships.filter(user=self.member).delete()
        self.assertFalse(self.board.memberships.filter(user=self.member).exists())
        self.share()
        self.assertFalse(visible_to(Kanban.objects.all(), self.member).filter(pk=self.card.pk).exists())

    def test_observer_is_readonly_on_every_write_path(self):
        self.share(role='observer')
        self.login(self.member)
        detail = self.client.get(self.url(f'view-task/{self.card.task_id}/?task_pk={self.card.pk}'))
        self.assertEqual(detail.status_code, 200)
        self.assertFalse(detail.context['can_edit_task'])
        self.assertNotContains(detail, 'id="activity-comment-form"')
        self.assertIn(self.board, detail.context['form'].fields['section'].queryset)
        for data in [dict(action='edit_project', project_id=self.project.pk, name='Zmiana'),
                     dict(action='edit_section', section_id=self.board.pk, title='Zmiana'),
                     dict(action='create_section', project_id=self.project.pk, title='Zmiana'),
                     dict(action='add_project_note', project_id=self.project.pk, message='Zmiana'),
                     dict(action='rename_board_column', column_id=self.column.pk, title='Zmiana'),
                     dict(action='delete_board_column', column_id=self.column.pk)]:
            with self.subTest(data=data):
                self.assertEqual(self.client.post(self.url(), data).status_code, 403)
        self.assertEqual(self.client.post(self.url(f'groups/{self.board.pk}/'), {'action':'create_board_column','title':'Zmiana'}).status_code, 403)
        for suffix in [f'update/{self.card.task_id}/', f'delete/{self.card.task_id}/']:
            self.assertEqual(self.post_json(suffix, task_pk=self.card.pk, status='closed').status_code, 403)
        self.assertEqual(self.client.post(self.url(f'delete-attachment/{self.attachment.pk}/')).status_code, 403)
        self.assertEqual(self.client.post(self.url(f'view-task/{self.card.task_id}/?task_pk={self.card.pk}'), {'action':'add_activity_comment', 'activity_comment':'Zmiana'}).status_code, 403)
        self.assertEqual(self.post_json(f'groups/{self.board.pk}/reorder-columns/', column_ids=[self.column.pk]).status_code, 403)
        self.assertFalse(editable_to(Kanban.objects.all(), self.member).filter(pk=self.child.pk).exists())

    def test_board_observer_and_parent_observer_override_ownership(self):
        self.share(role='observer')
        self.private_board()
        self.board.private_owner = self.member
        self.board.save()
        self.login(self.member)
        self.assertFalse(self.client.get(self.url(f'groups/{self.board.pk}/team/')).json()['can_manage'])
        self.assertEqual(self.team('section', action='share', email=self.owner.email, role='member').status_code, 403)
        self.project.memberships.filter(user=self.member).update(role='member')
        self.board.private_owner = self.owner
        self.board.save()
        KanbanSectionMembership.objects.create(section=self.board, user=self.member, role='observer')
        self.assertFalse(editable_to(Kanban.objects.all(), self.member).filter(pk=self.card.pk).exists())

    def test_bulk_and_ancestor_deletions_do_not_partially_modify(self):
        self.login(self.member)
        for suffix in ['delete/', 'bulk-update-status/']:
            self.assertEqual(self.post_json(suffix, task_pks=[self.public_card.pk, self.card.pk], status='closed').status_code, 403)
            self.public_card.refresh_from_db()
            self.assertEqual(self.public_card.status, 'new')
        # A public ancestor cannot cascade through a hidden child.
        Kanban.objects.filter(pk=self.card.pk).update(parent=self.public_card)
        self.assertEqual(self.post_json(f'delete/{self.public_card.task_id}/', task_pk=self.public_card.pk).status_code, 403)
        self.private_board()
        self.board.project = self.public
        self.board.save()
        self.assertEqual(self.client.post(self.url(), {'action':'delete_project', 'project_ids':[self.public.pk]}).status_code, 403)
        self.assertTrue(KanbanProject.objects.filter(pk=self.public.pk).exists())

    def test_new_defaults_actual_creator_and_unchanged_visibility_without_field(self):
        self.login(self.member)
        response = self.client.post(self.url(), {'action':'create_project', 'name':'Moja przestrzeń', 'section_title':'Pierwsza'})
        self.assertEqual(response.status_code, 302)
        created = KanbanProject.objects.get(name='Moja przestrzeń')
        self.assertEqual((created.user_id, created.private_owner_id, created.visibility), (self.owner.pk,self.member.pk,'private'))
        self.assertEqual(created.sections.get().visibility,'public')
        response = self.client.post(self.url(), {'action':'edit_project', 'project_id':created.pk, 'name':'Nowa nazwa'})
        self.assertEqual(response.status_code,302)
        created.refresh_from_db(); self.assertEqual(created.visibility,'private')
        self.assertFalse(visible_to(KanbanProject.objects.all(),self.owner).filter(pk=created.pk).exists())
        response = self.client.post(self.url(), {'action':'create_section', 'project_id':self.public.pk, 'title':'Moja tablica'})
        self.assertEqual(response.status_code,302)
        self.assertEqual(KanbanSection.objects.get(title='Moja tablica').private_owner_id,self.member.pk)

    def test_publication_and_visibility_are_owner_only(self):
        self.private_board(); self.share(self.admin,'admin'); self.share(); self.share(kind='section')
        self.login(self.admin)
        response=self.client.post(self.url(),{'action':'edit_project','project_id':self.project.pk,'name':self.project.name,'visibility':'public'})
        self.assertIn('visibility',response.context['project_rename_form'].errors)
        self.login(self.owner)
        self.assertEqual(self.client.post(self.url(),{'action':'edit_project','project_id':self.project.pk,'name':self.project.name,'visibility':'public'}).status_code,302)
        self.project.refresh_from_db()
        self.assertIsNone(self.project.private_owner_id); self.assertFalse(self.project.memberships.exists())
        self.assertTrue(self.board.memberships.filter(user=self.member).exists())
        self.assertEqual(self.client.post(self.url(),{'action':'edit_section','section_id':self.board.pk,'title':self.board.title,'visibility':'public'}).status_code,302)
        self.board.refresh_from_db(); self.assertIsNone(self.board.private_owner_id); self.assertFalse(self.board.memberships.exists())

    def test_workspace_revocation_does_not_resurrect_shares(self):
        self.private_board();self.share();self.share(kind='section')
        membership=WorkplaceMembership.objects.get(workplace=self.workspace,user=self.member)
        membership.is_active=False; membership.save()
        self.assertFalse(self.project.memberships.filter(user=self.member).exists())
        self.assertFalse(self.board.memberships.filter(user=self.member).exists())
        membership.is_active=True; membership.save()
        self.assertFalse(visible_to(Kanban.objects.all(),self.member).filter(pk=self.card.pk).exists())

    def test_hidden_content_not_in_search_calendar_notifications_mentions_or_favorites(self):
        self.project.favorited_by.add(self.member);self.board.favorited_by.add(self.member)
        self.login(self.member)
        for suffix in ['?view=projects&tab=favorites','?view=all-groups&tab=favorites','?view=all-tasks']:
            response=self.client.get(self.url(suffix));self.assertNotContains(response,'Poufna')
        self.assertEqual(self.client.get(reverse('global_search'),{'q':'Poufna'}).json()['total'],0)
        self.assertNotContains(self.client.get(scoped_workplace_app_path(self.workspace,'calendar')),'Poufna')
        self.assertFalse(notification_sources(self.member)['kanban'].filter(pk=self.activity.pk).exists())
        self.assertEqual(self.client.post(self.url(f'follow/task/{self.card.pk}/'), {'action':'follow'}).status_code,404)
        self.assertEqual(self.client.post(self.url(f'favorites/project/{self.project.pk}/'),{'favorite_action':'add'}).status_code,404)
        self.assertNotIn(self.member,mention_people(self.card))

    def test_forms_reject_hidden_or_observer_relationships(self):
        for role in [None, 'observer']:
            if role: self.share(role=role)
            form=KanbanModalForm({'title':'Nowa','section':self.board.pk,'status':'new'},user=self.owner,viewer=self.member,workplace=self.workspace,project=self.project)
            self.assertFalse(form.is_valid())
            self.assertIn('section',form.errors)

    def test_revoke_blocks_previously_accessible_files_and_content(self):
        grant=self.share(); self.project.favorited_by.add(self.member)
        self.assertTrue(visible_to(KanbanAttachment.objects.all(),self.member).filter(pk=self.attachment.pk).exists())
        self.assertEqual(self.team(action='remove',member_id=grant.pk).status_code,200)
        self.login(self.member)
        for suffix in [f'attachments/{self.attachment.pk}/download/', f'groups/{self.board.pk}/team/',f'?project={self.project.pk}']:
            self.assertEqual(self.client.get(self.url(suffix)).status_code,404)

    def test_deleting_nonempty_private_directories_cannot_expose_orphans(self):
        for data in [dict(action='delete_project',project_id=self.project.pk),dict(action='delete_section',section_id=self.board.pk)]:
            response=self.client.post(self.url(),data,follow=True)
            self.assertEqual(response.status_code,200)
            self.assertIn('Najpierw usuń karty',response.content.decode())
            self.card.refresh_from_db();self.assertEqual(self.card.section_id,self.board.pk)
        self.card.delete()
        self.assertEqual(self.client.post(self.url(),dict(action='delete_project',project_id=self.project.pk)).status_code,302)
        self.assertFalse(KanbanProject.objects.filter(pk=self.project.pk).exists())

    def test_old_history_cannot_leak_hidden_subcard_names(self):
        old=KanbanActivity.objects.create(task=self.public_card,actor=self.owner,action='subtask_created',metadata={'subtask_title':self.card.title,'subtask_task_id':self.card.task_id})
        stable=KanbanActivity.objects.create(task=self.public_card,actor=self.owner,action='subtask_created',metadata={'subtask_pk':self.card.pk,'subtask_title':self.card.title})
        self.assertFalse(visible_to(KanbanActivity.objects.all(),self.member).filter(pk__in=[old.pk,stable.pk]).exists())
        self.share()
        self.assertTrue(visible_to(KanbanActivity.objects.all(),self.member).filter(pk=stable.pk).exists())

    def test_csrf_and_workspace_isolation(self):
        csrf=Client(enforce_csrf_checks=True);csrf.force_login(self.owner)
        self.assertEqual(csrf.post(self.url(f'projects/{self.project.pk}/team/'),{'action':'share','email':self.member.email,'role':'member'}).status_code,403)
        foreign=scoped_workplace_app_path(self.other,'kanban',f'projects/{self.project.pk}/team/')
        self.assertEqual(self.client.get(foreign).status_code,404)
        self.assertEqual(self.team(action='role',member_id='bad',role='member').status_code,404)


class KanbanSharingMigrationTests(TransactionTestCase):
    def test_existing_spaces_boards_and_content_remain_public(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(latest))
        owner = get_user_model().objects.create_user(username='kanban-migration', email='migration@kanban-sharing.test')
        executor.migrate([('kanban', '0038_directory_favorites')])
        apps = executor.loader.project_state([('kanban', '0038_directory_favorites')]).apps
        project = apps.get_model('kanban', 'KanbanProject').objects.create(user_id=owner.pk, name='Istniejąca przestrzeń', code='OLD')
        board = apps.get_model('kanban', 'KanbanSection').objects.create(project=project, title='Istniejąca tablica', description='Treść')
        project.favorited_by.add(owner.pk)
        MigrationExecutor(connection).migrate(latest)
        restored = KanbanProject.objects.get(pk=project.pk)
        restored_board = KanbanSection.objects.get(pk=board.pk)
        self.assertEqual((restored.visibility, restored.private_owner_id), ('public', None))
        self.assertEqual((restored_board.visibility, restored_board.private_owner_id), ('public', None))
        self.assertEqual(restored_board.description, 'Treść')
        self.assertTrue(restored.favorited_by.filter(pk=owner.pk).exists())
        self.assertFalse(restored.memberships.exists())
