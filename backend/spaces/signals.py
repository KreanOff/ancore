from django.db.models.signals import m2m_changed, post_save, post_delete
from django.dispatch import receiver


@receiver(post_save, sender='spaces.SpaceTask')
def task_metadata(sender, instance, created=False, raw=False, **kwargs):
    if raw or not created:
        return
    from .services import create_work_item, record
    item = create_work_item(instance)
    record(item, getattr(instance, '_activity_actor', instance.created_by), 'created', 'utworzył zadanie', {'title': instance.title})


@receiver(post_delete, sender='workplaces.WorkplaceMembership')
def removed_workspace_member(sender, instance, **kwargs):
    from .models import TeamMembership, SpaceMembership, SpaceTaskMembership
    TeamMembership.objects.filter(team__workplace_id=instance.workplace_id, user_id=instance.user_id).delete()
    SpaceMembership.objects.filter(space__workplace_id=instance.workplace_id, user_id=instance.user_id).delete()
    SpaceTaskMembership.objects.filter(task__space__workplace_id=instance.workplace_id, user_id=instance.user_id).delete()


@receiver(post_save, sender='workplaces.WorkplaceMembership')
def disabled_workspace_member(sender, instance, raw=False, **kwargs):
    if not raw and (not instance.is_active or instance.role not in {'owner', 'admin', 'member', 'guest'}):
        removed_workspace_member(sender, instance)


@receiver(post_delete, sender='spaces.SpaceMembership')
def removed_space_member(sender, instance, **kwargs):
    from .models import Space, SpaceTaskMembership
    if Space.objects.filter(pk=instance.space_id, visibility='private').exists():
        SpaceTaskMembership.objects.filter(task__space_id=instance.space_id, user_id=instance.user_id).delete()


@receiver(post_delete, sender='spaces.SpaceTaskMembership')
def removed_task_member(sender, instance, **kwargs):
    from .access import tree_ids
    from .models import SpaceTask, SpaceTaskMembership
    if SpaceTask.objects.filter(pk=instance.task_id, visibility='private').exists():
        descendants = tree_ids(SpaceTask.objects.filter(parent_id=instance.task_id))
        SpaceTaskMembership.objects.filter(task_id__in=descendants, user_id=instance.user_id).delete()


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


@receiver(post_delete, sender='spaces.SpaceTaskFile')
def deleted_task_file(sender, instance, using, **kwargs):
    from core.task_files import delete_after_commit
    delete_after_commit(instance, using)


@receiver(m2m_changed, sender='spaces.SpaceTask_tags')
def scoped_space_task_tags(sender, instance, action, reverse, pk_set, **kwargs):
    if action != 'pre_add' or not pk_set:
        return
    from django.core.exceptions import ValidationError
    from tasks.models import TaskTag
    from .models import SpaceTask
    invalid = SpaceTask.objects.filter(pk__in=pk_set).exclude(space_id=instance.space_id) if reverse else TaskTag.objects.filter(pk__in=pk_set).exclude(space_id=instance.space_id)
    if invalid.exists():
        raise ValidationError('Tag musi należeć do przestrzeni zadania.')
