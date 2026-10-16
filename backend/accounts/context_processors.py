from .avatar import account_avatar
from .presence import heartbeat_seconds, idle_seconds


def current_account_avatar(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {}

    return {
        'current_account_avatar': account_avatar(request.user),
        'user_presence_idle_seconds': idle_seconds(),
        'user_presence_heartbeat_seconds': heartbeat_seconds(),
    }
