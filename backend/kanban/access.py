"""Keep historical Kanban records inaccessible through current application helpers."""


def visible_to(queryset, viewer):
    """Historical rows are kept in storage, never exposed as active work."""
    return queryset.none() if queryset.model._meta.app_label == 'kanban' else queryset
