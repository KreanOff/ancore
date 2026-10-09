from django.db.models.signals import m2m_changed, post_save, post_delete
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


@receiver(m2m_changed, sender='tasks.Task_tags')
def scoped_task_tags(sender, instance, action, reverse, pk_set, **kwargs):
    if action != 'pre_add' or not pk_set:
        return
    from django.core.exceptions import ValidationError
    from tasks.models import Task, TaskTag
    from .models import WorkItem
    if reverse:
        if not instance.space_id:
            return  # Retain the historical, unscoped model contract.
        if Task.objects.filter(pk__in=pk_set).exclude(
            user_id=instance.user_id, workplace_id=instance.workplace_id,
            work_item__space_id=instance.space_id,
        ).exists():
            raise ValidationError('Tag musi należeć do przestrzeni zadania.')
    else:
        space_id = WorkItem.objects.filter(task=instance).values_list('space_id', flat=True).first()
        if TaskTag.objects.filter(pk__in=pk_set, space__isnull=False).exclude(
            user_id=instance.user_id, workplace_id=instance.workplace_id, space_id=space_id,
        ).exists():
            raise ValidationError('Tag musi należeć do przestrzeni zadania.')


@receiver(m2m_changed, sender='tasks.TaskTag_related_tags')
def scoped_related_tags(sender, instance, action, pk_set, **kwargs):
    if action != 'pre_add' or not pk_set:
        return
    from django.core.exceptions import ValidationError
    from tasks.models import TaskTag
    if TaskTag.objects.filter(pk__in=pk_set).exclude(
        user_id=instance.user_id, workplace_id=instance.workplace_id, space_id=instance.space_id,
    ).exists():
        raise ValidationError('Powiązane tagi muszą należeć do tej samej przestrzeni.')
