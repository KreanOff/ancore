from .avatar import account_avatar


def current_account_avatar(request):
    if not getattr(request, 'user', None) or not request.user.is_authenticated:
        return {}

    return {
        'current_account_avatar': account_avatar(request.user),
    }
