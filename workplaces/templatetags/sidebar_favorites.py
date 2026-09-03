from django import template


register = template.Library()


@register.inclusion_tag(
    'workplaces/includes/sidebar_favorite_toggle.html',
    takes_context=True,
)
def sidebar_favorite_toggle(context, item_key, label, icon, url):
    request = context.get('request')
    workplace = context.get('current_workplace')
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated or workplace is None:
        return {'show_sidebar_favorite_toggle': False}

    is_favorite = item_key in (context.get('sidebar_favorite_keys') or [])
    return {
        'show_sidebar_favorite_toggle': True,
        'csrf_token': context.get('csrf_token'),
        'current_workplace': workplace,
        'item_key': item_key,
        'label': label,
        'icon': icon,
        'url': url,
        'is_favorite': is_favorite,
        'next_url': request.get_full_path(),
    }
