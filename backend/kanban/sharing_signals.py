from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from workplaces.models import WorkplaceMembership
from .models import KanbanProject, KanbanProjectMembership, KanbanSectionMembership


def revoke_workspace_shares(membership):
    KanbanSectionMembership.objects.filter(
        section__project__workplace_id=membership.workplace_id, user_id=membership.user_id,
    ).delete()
    KanbanProjectMembership.objects.filter(
        project__workplace_id=membership.workplace_id, user_id=membership.user_id,
    ).delete()


@receiver(post_delete, sender=WorkplaceMembership)
def workspace_member_deleted(sender, instance, **kwargs):
    revoke_workspace_shares(instance)


@receiver(post_save, sender=WorkplaceMembership)
def workspace_member_disabled(sender, instance, raw=False, **kwargs):
    if not raw and (not instance.is_active or instance.role not in {'owner', 'admin', 'member'}):
        revoke_workspace_shares(instance)


@receiver(post_delete, sender=KanbanProjectMembership)
def project_member_deleted(sender, instance, **kwargs):
    # Publishing preserves independently private boards, just as in Tasks.
    if KanbanProject.objects.filter(pk=instance.project_id, visibility='public').exists():
        return
    KanbanSectionMembership.objects.filter(
        section__project_id=instance.project_id, user_id=instance.user_id,
    ).delete()
