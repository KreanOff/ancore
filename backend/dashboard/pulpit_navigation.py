"""Personal dashboard navigation, rebuilt against current access on every page."""
from django.db.models import Case, Exists, OuterRef, When
from core.emoji import emoji_payload

from workplaces.services import workspace_owner

from .models import Dashboard
from .pulpits import app_url, decorate_dashboard, visible_dashboards
from .recent import recent_views


def sidebar_dashboards(request, limit=6):
    favorites = Dashboard.favorited_by.through.objects.filter(dashboard_id=OuterRef('pk'), user_id=request.user.pk)
    dashboards = visible_dashboards(request).exclude(
        is_default=True, created_by=request.user,
    ).annotate(is_favorite=Exists(favorites))
    starred = list(dashboards.filter(is_favorite=True).order_by('name', 'pk')[:limit])
    recent_ids = list(dict.fromkeys(entry['identity'][3] for entry in recent_views(request)
                                  if entry['identity'][2] == 'dashboard.dashboard'))
    recent = list(dashboards.filter(pk__in=recent_ids, is_favorite=False).order_by(Case(
        *(When(pk=pk, then=position) for position, pk in enumerate(recent_ids)), default=len(recent_ids),
    ))[:limit]) if recent_ids else []
    resolver = getattr(request, 'resolver_match', None)
    current_identifier = resolver.kwargs.get('pk') if resolver and resolver.app_name in {'pulpits', 'workplace_pulpits'} and resolver.url_name == 'detail' else None
    current_lookup = {'pk': current_identifier} if isinstance(current_identifier, int) else {'slug': current_identifier}
    for dashboard in [*starred, *recent]:
        decorate_dashboard(request, dashboard)
        dashboard.is_current = (dashboard.pk if isinstance(current_identifier, int) else dashboard.slug) == current_identifier
    default_is_current = bool(resolver and (
        resolver.url_name == 'home'
        or (resolver.app_name in {'pulpits', 'workplace_pulpits'} and (
            resolver.url_name == 'default'
            or (current_identifier and Dashboard.objects.filter(
                **current_lookup, owner=workspace_owner(request), workplace=request.workplace,
                created_by=request.user, is_default=True,
            ).exists())
        ))
    ))
    default_icon = Dashboard.objects.filter(owner=workspace_owner(request), workplace=request.workplace,
        created_by=request.user, is_default=True).values_list('icon', flat=True).first() or Dashboard.Icon.DASHBOARD
    default_emoji = emoji_payload(default_icon)
    return {'navigation_starred_dashboards': starred, 'navigation_recent_dashboards': recent,
            'default_dashboard_icon': default_icon, 'default_dashboard_emoji': default_emoji['value'],
            'default_dashboard_emoji_art': default_emoji['art'],
            'default_dashboard_url': app_url(request, 'default/'), 'default_dashboard_is_current': default_is_current}
