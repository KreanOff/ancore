"""Replace valid pending project/group invitations with immediate membership."""
from django.db import migrations
from django.utils import timezone


def grant_pending_shares(apps, schema_editor):
    db = schema_editor.connection.alias
    WorkspaceMember = apps.get_model('workplaces', 'WorkplaceMembership')
    ProjectMember = apps.get_model('tasks', 'TaskProjectMembership')
    SectionMember = apps.get_model('tasks', 'TaskSectionMembership')
    now = timezone.now()

    def active_person(person, workplace):
        return person and person.is_active and (
            person.pk == workplace.owner_id or WorkspaceMember.objects.using(db).filter(
                workplace_id=workplace.pk, user_id=person.pk, is_active=True,
                role__in=['admin', 'member'],
            ).exists()
        )

    def project_role(project, person):
        if project.visibility == 'public':
            return 'member'
        if not project.private_owner_id:
            return ''
        if project.private_owner_id == person.pk:
            return 'owner'
        return ProjectMember.objects.using(db).filter(
            project_id=project.pk, user_id=person.pk,
        ).values_list('role', flat=True).first() or ''

    # Project grants must be ready before groups check their parent boundary.
    for kind, Membership in [('project', ProjectMember), ('section', SectionMember)]:
        Invitation = apps.get_model('tasks', f'Task{kind.title()}Invitation')
        parent = 'project' if kind == 'project' else 'section__project'
        invitations = Invitation.objects.using(db).filter(
            status='pending', expires_at__gt=now,
        ).select_related(kind, f'{parent}__workplace', 'recipient', 'invited_by')
        for invitation in invitations.iterator():
            target = getattr(invitation, kind)
            project = target if kind == 'project' else target.project
            workplace = project.workplace
            if (not workplace or project.user_id != workplace.owner_id
                    or target.visibility != 'private' or not target.private_owner_id
                    or invitation.recipient_id == target.private_owner_id
                    or not active_person(invitation.recipient, workplace)
                    or not active_person(invitation.invited_by, workplace)):
                continue
            if kind == 'project':
                actor_role = project_role(project, invitation.invited_by)
            else:
                if (not project_role(project, invitation.recipient)
                        or project_role(project, invitation.invited_by) not in {'owner', 'admin', 'member'}):
                    continue
                actor_role = 'owner' if target.private_owner_id == invitation.invited_by_id else (
                    Membership.objects.using(db).filter(section_id=target.pk, user_id=invitation.invited_by_id)
                    .values_list('role', flat=True).first()
                )
            allowed_roles = {'admin', 'member', 'observer'} if actor_role == 'owner' else (
                {'member', 'observer'} if actor_role == 'admin' else set()
            )
            if invitation.role in allowed_roles:
                Membership.objects.using(db).get_or_create(
                    **{f'{kind}_id': target.pk, 'user_id': invitation.recipient_id},
                    defaults={'role': invitation.role},
                )
        # End the old workflow without pretending the recipient accepted it.
        # Existing memberships and declined/revoked decisions remain untouched.
        Invitation.objects.using(db).filter(status='pending').update(status='revoked')


class Migration(migrations.Migration):
    dependencies = [
        ('tasks', '0058_section_sharing'),
        ('workplaces', '0008_team_invitations'),
    ]

    operations = [migrations.RunPython(grant_pending_shares, migrations.RunPython.noop)]
