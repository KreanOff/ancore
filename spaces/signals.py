from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


@receiver(post_save, sender='tasks.TaskProject')
def project_space(sender, instance, raw=False, **kwargs):
    if raw or not instance.workplace_id:
        return
    from .services import ensure_space
    ensure_space(instance)


@receiver(post_save, sender='tasks.Task')
def task_metadata(sender, instance, raw=False, **kwargs):
    if raw:
        return
    from .services import ensure_work_item
    ensure_work_item(instance)


@receiver(post_delete, sender='workplaces.WorkplaceMembership')
def removed_workspace_member(sender, instance, **kwargs):
    from .models import TeamMembership
    TeamMembership.objects.filter(team__workplace_id=instance.workplace_id, user_id=instance.user_id).delete()


@receiver(post_save, sender='workplaces.WorkplaceMembership')
def disabled_workspace_member(sender, instance, raw=False, **kwargs):
    if not raw and not instance.is_active:
        removed_workspace_member(sender, instance)


@receiver(post_save, sender='tasks.TaskSection')
def moved_section(sender, instance, raw=False, **kwargs):
    if raw:
        return
    from .services import ensure_work_item
    for task in instance.tasks.exclude(work_item__space__project_id=instance.project_id):
        ensure_work_item(task)


@receiver(post_delete, sender='spaces.Team')
def deleted_team_photo(sender, instance, using, **kwargs):
    if instance.photo:
        from django.db import transaction
        storage, name = instance.photo.storage, instance.photo.name
        transaction.on_commit(lambda: storage.delete(name), using=using, robust=True)


@receiver(post_delete, sender='spaces.Space')
def deleted_space_avatar(sender, instance, using, **kwargs):
    from .avatars import delete_avatar_after_commit
    if instance.avatar_photo:
        delete_avatar_after_commit(instance.avatar_photo.storage, instance.avatar_photo.name, using)
