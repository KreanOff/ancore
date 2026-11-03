from django import template
from spaces.defaults import configuration_name_color

register = template.Library()


@register.filter
def type_badge_style(color):
    if not color:
        return ''
    color = configuration_name_color('types', {'color': color})
    return (f'background-color: color-mix(in srgb, {color} 16%, #ffffff); '
            '--tasks-type-icon-color: var(--text-primary);')


@register.filter
def status_style(status):
    if not status:
        return ''
    color = configuration_name_color('statuses', status if isinstance(status, dict) else {'color': status})
    return (f'--tasks-status-color: {color}; '
            f'--tasks-status-background: color-mix(in srgb, {color} 16%, var(--card-bg)); '
            f'--tasks-status-border: color-mix(in srgb, {color} 30%, var(--card-bg));')


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
        key = (item.task.status, item.status_label, item.status_color)
        group = groups.setdefault(key, {
            'category': item.task.status, 'label': item.status_label,
            'color': item.status_color,
            'order': item.status_order, 'items': [],
        })
        group['items'].append(item)
    return sorted(groups.values(), key=lambda group: group['order'])
