from django import template

register = template.Library()


@register.simple_tag
def pagination_pages(page):
    """Keep the first, last and neighbouring pages in a compact footer."""
    return page.paginator.get_elided_page_range(page.number, on_each_side=1, on_ends=1)


@register.simple_tag
def space_avatar(space):
    from spaces.avatars import space_avatar as get_avatar
    return get_avatar(space)


@register.filter
def status_groups(items):
    """Group an already permission-filtered page without hiding custom statuses."""
    groups = {}
    for item in items:
        key = (item.task.status, item.status_label)
        group = groups.setdefault(key, {
            'category': item.task.status, 'label': item.status_label,
            'order': item.status_order, 'items': [],
        })
        group['items'].append(item)
    return sorted(groups.values(), key=lambda group: group['order'])
