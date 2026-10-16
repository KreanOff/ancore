"""Session-local, personal navigation history. Never cache titles or access rights."""

from django.utils import timezone

RECENT_SESSION_KEY = 'for_you_recent'
RECENT_LIMIT = 60


def remember_view(request, obj):
    if request.method != 'GET' or obj is None:
        return
    workplace = getattr(request, 'workplace', None)
    if workplace is None:
        return
    identity = [request.user.pk, workplace.pk, obj._meta.label_lower, obj.pk]
    entries = request.session.get(RECENT_SESSION_KEY, [])
    request.session[RECENT_SESSION_KEY] = [
        {'identity': identity, 'at': timezone.now().isoformat()},
        *(entry for entry in entries if entry['identity'] != identity),
    ][:RECENT_LIMIT]


def recent_views(request):
    scope = [request.user.pk, request.workplace.pk]
    return [entry for entry in request.session.get(RECENT_SESSION_KEY, [])
            if entry['identity'][:2] == scope]
