"""Removing Workspace membership must not leave grants that revive on rejoining."""
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from workplaces.models import WorkplaceMembership
from .models import TaskProject, TaskProjectInvitation


def revoke_project_shares(membership):
    TaskProject.shared_with.through.objects.filter(
        project__workplace_id=membership.workplace_id, user_id=membership.user_id,
    ).delete()
    TaskProjectInvitation.objects.filter(project__workplace_id=membership.workplace_id,
        recipient_id=membership.user_id, status='pending').update(status='revoked')


@receiver(post_delete, sender=WorkplaceMembership)
def membership_deleted(sender, instance, **kwargs):
    revoke_project_shares(instance)


@receiver(post_save, sender=WorkplaceMembership)
def membership_disabled(sender, instance, raw=False, **kwargs):
    if not raw and (not instance.is_active or instance.role not in {'owner', 'admin', 'member'}):
        revoke_project_shares(instance)
