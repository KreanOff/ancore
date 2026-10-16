from .presence import mark_user_seen, sync_stale_presence_statuses


PRESENCE_PING_PATH = '/accounts/presence/ping/'


class UserPresenceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        was_authenticated = bool(getattr(user, 'is_authenticated', False))
        is_presence_ping = request.path == PRESENCE_PING_PATH

        if was_authenticated:
            sync_stale_presence_statuses()
            if not is_presence_ping:
                mark_user_seen(user)

        response = self.get_response(request)

        user = getattr(request, 'user', None)
        if not was_authenticated and getattr(user, 'is_authenticated', False):
            mark_user_seen(user, force=True)

        return response
