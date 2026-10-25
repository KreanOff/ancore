from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver


@receiver(post_delete, sender='workplaces.WorkplaceMembership')
def removed_workspace_member(sender, instance, using, **kwargs):
    from .models import DashboardMembership, SavedTaskFilterMembership
    DashboardMembership.objects.using(using).filter(
        dashboard__workplace_id=instance.workplace_id, user_id=instance.user_id,
    ).delete()
    SavedTaskFilterMembership.objects.using(using).filter(
        savedtaskfilter__workplace_id=instance.workplace_id, user_id=instance.user_id,
    ).delete()


@receiver(post_save, sender='workplaces.WorkplaceMembership')
def disabled_workspace_member(sender, instance, raw=False, using=None, **kwargs):
    if not raw and (not instance.is_active or instance.role not in {'owner', 'admin', 'member'}):
        removed_workspace_member(sender, instance, using)
