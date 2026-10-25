"""Personal stars over already access-scoped document querysets."""
from django.db.models import Exists, OuterRef


def with_personal_stars(queryset, user):
    field = queryset.model._meta.get_field('favorited_by')
    favorites = field.remote_field.through.objects.filter(
        **{f'{field.m2m_field_name()}_id': OuterRef('pk'), 'user_id': user.pk},
    )
    return queryset.annotate(is_starred=Exists(favorites))


def toggle_star(item, user):
    """Call while holding the item's row lock to serialize repeated toggles."""
    if item.favorited_by.filter(pk=user.pk).exists():
        item.favorited_by.remove(user)
    else:
        item.favorited_by.add(user)
