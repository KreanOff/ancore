"""Personal dashboard navigation, rebuilt against current access on every page."""
from django.db.models import Case, Exists, OuterRef, When

from .models import Dashboard
from .pulpits import decorate_dashboard, visible_dashboards
from .recent import recent_views


def sidebar_dashboards(request, limit=6):
    favorites = Dashboard.favorited_by.through.objects.filter(dashboard_id=OuterRef('pk'), user_id=request.user.pk)
    dashboards = visible_dashboards(request).annotate(is_favorite=Exists(favorites))
    starred = list(dashboards.filter(is_favorite=True).order_by('name', 'pk')[:limit])
    recent_ids = list(dict.fromkeys(entry['identity'][3] for entry in recent_views(request)
                                  if entry['identity'][2] == 'dashboard.dashboard'))
    recent = list(dashboards.filter(pk__in=recent_ids, is_favorite=False).order_by(Case(
        *(When(pk=pk, then=position) for position, pk in enumerate(recent_ids)), default=len(recent_ids),
    ))[:limit]) if recent_ids else []
    resolver = getattr(request, 'resolver_match', None)
    current_pk = resolver.kwargs.get('pk') if resolver and resolver.app_name in {'pulpits', 'workplace_pulpits'} and resolver.url_name == 'detail' else None
    for dashboard in [*starred, *recent]:
        decorate_dashboard(request, dashboard)
        dashboard.is_current = dashboard.pk == current_pk
    return {'navigation_starred_dashboards': starred, 'navigation_recent_dashboards': recent}
