import json

from django import template
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.templatetags.static import static
from django.utils.html import format_html

register = template.Library()


@register.simple_tag(takes_context=True)
def global_panels_bootstrap(context):
    from django.urls import reverse
    from core.frontend import api_url
    request = context.get('request')
    if not request or not request.user.is_authenticated or context.get('disable_react_shell'):
        return None
    from core.shell import shell_payload, messages_payload
    return {
        'user_id': str(request.user.pk), 'api_url': api_url(request),
        'search_url': reverse('global_search'), 'notifications_url': reverse('notifications'),
        'action_url': reverse('notification_action'),
        'pending_invitation_count': context.get('pending_notification_invitation_count', 0),
        'shell': shell_payload(request, context.flatten()), 'messages': messages_payload(request),
    }


@register.simple_tag
def react_bundle():
    try:
        manifest = json.loads((settings.BASE_DIR / 'static/frontend/manifest.json').read_text())
        entry = manifest['main']
    except (OSError, ValueError, KeyError) as error:
        raise ImproperlyConfigured('Build frontend/app with pnpm install --frozen-lockfile && pnpm build before starting Ancore.') from error
    return format_html('<script type="module" src="{}"></script>', static(f'frontend/{entry}'))
