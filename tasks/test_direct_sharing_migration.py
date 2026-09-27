"""Pending invitations become grants only within the current permission scope."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone

from tasks.models import TaskProjectMembership, TaskSectionMembership
from workplaces.models import WorkplaceMembership, create_workplace_for_user


class DirectSharingMigrationTests(TransactionTestCase):
    def test_migration_converts_valid_shares_without_reviving_invalid_access(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(latest))
        executor.migrate([('tasks', '0058_section_sharing')])
        apps = executor.loader.project_state([('tasks', '0058_section_sharing')]).apps
        Project = apps.get_model('tasks', 'TaskProject')
        Section = apps.get_model('tasks', 'TaskSection')
        ProjectMember = apps.get_model('tasks', 'TaskProjectMembership')
        SectionMember = apps.get_model('tasks', 'TaskSectionMembership')
        ProjectInvite = apps.get_model('tasks', 'TaskProjectInvitation')
        SectionInvite = apps.get_model('tasks', 'TaskSectionInvitation')
        owner = get_user_model().objects.create_user(username='direct-owner', email='owner@migration.test')
        workspace = create_workplace_for_user(owner, 'Direct migration')
        expected = []
        for kind in ['project', 'section']:
            for case in ['member', 'admin', 'observer', 'existing', 'expired', 'declined', 'revoked',
                         'inactive', 'foreign', 'inactive_membership', 'no_owner', 'public',
                         'unauthorized_author', 'missing_author', 'admin_promote', 'wrong_scope',
                         'parent_observer', 'parent_hidden']:
                with self.subTest(kind=kind, case=case):
                    person = get_user_model().objects.create_user(
                        username=f'{kind}-{case}', email=f'{kind}-{case}@migration.test', is_active=case != 'inactive',
                    )
                    if case != 'foreign':
                        WorkplaceMembership.objects.create(workplace=workspace, user=person,
                                                           is_active=case != 'inactive_membership')
                    project = Project.objects.create(
                        user_id=person.pk if case == 'wrong_scope' else owner.pk,
                        workplace_id=workspace.pk, name=f'{kind}-{case}',
                        visibility='private', private_owner_id=owner.pk,
                    )
                    target = project if kind == 'project' else Section.objects.create(
                        project=project, title=case, visibility='private', private_owner_id=owner.pk,
                    )
                    Membership = ProjectMember if kind == 'project' else SectionMember
                    Invitation = ProjectInvite if kind == 'project' else SectionInvite
                    if case == 'no_owner':
                        target.private_owner_id = None
                        target.save()
                    if case == 'public':
                        target.visibility = 'public'
                        target.save()
                    actor = owner
                    if case in {'unauthorized_author', 'admin_promote', 'parent_observer'}:
                        actor = get_user_model().objects.create_user(username=f'actor-{kind}-{case}', email=f'actor-{kind}-{case}@migration.test')
                        WorkplaceMembership.objects.create(workplace=workspace, user=actor)
                        if case in {'admin_promote', 'parent_observer'}:
                            Membership.objects.create(**{kind: target, 'user_id': actor.pk, 'role': 'admin'})
                    if kind == 'section':
                        if case != 'parent_hidden':
                            # Validate project grants before checking the child, too.
                            ProjectInvite.objects.create(project=project, recipient_id=person.pk, invited_by_id=owner.pk)
                        if actor != owner:
                            ProjectMember.objects.create(project=project, user_id=actor.pk,
                                                         role='observer' if case == 'parent_observer' else 'member')
                    if case == 'existing':
                        Membership.objects.create(**{kind: target, 'user_id': person.pk, 'role': 'observer'})
                    role = case if case in {'admin', 'observer'} else 'admin' if case == 'admin_promote' else 'member'
                    Invitation.objects.create(**{
                        kind: target, 'recipient_id': person.pk,
                        'invited_by_id': None if case == 'missing_author' else actor.pk, 'role': role,
                        'status': case if case in {'declined', 'revoked'} else 'pending',
                        'expires_at': timezone.now() + timedelta(days=-1 if case == 'expired' else 7),
                    })
                    valid = case in {'member', 'admin', 'observer', 'existing'} or (kind == 'project' and case in {'parent_hidden', 'parent_observer'})
                    expected.append((kind, target.pk, person.pk, 'observer' if case == 'existing' else role if valid else None))

        MigrationExecutor(connection).migrate(latest)
        for kind, target_id, person_id, role in expected:
            Membership = TaskProjectMembership if kind == 'project' else TaskSectionMembership
            with self.subTest(kind=kind, target_id=target_id, role=role):
                grant = Membership.objects.filter(**{f'{kind}_id': target_id, 'user_id': person_id}).first()
                self.assertEqual(grant.role if grant else None, role)
        self.assertFalse(ProjectInvite.objects.filter(status='pending').exists())
        self.assertFalse(SectionInvite.objects.filter(status='pending').exists())
