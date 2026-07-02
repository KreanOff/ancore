from django.shortcuts import redirect

from .services import (
    enable_workspace_url_scope,
    get_active_workplace,
    legacy_app_path_to_scoped,
    set_active_workplace,
    workplaces_for_user,
    workspace_url_scope_enabled,
    SCOPED_WORKPLACE_APPS,
)


def _scoped_workplace_segments(path_info):
    parts = (path_info or '').strip('/').split('/')
    if len(parts) >= 3 and parts[0] == 'workplaces' and parts[2] in SCOPED_WORKPLACE_APPS:
        return parts[1], parts[2]
    return None, None


class ActiveWorkplaceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        workplace_slug, _app_label = _scoped_workplace_segments(request.path_info)

        if workplace_slug and user and getattr(user, 'is_authenticated', False):
            workplace = workplaces_for_user(user).filter(slug=workplace_slug).first()
            if workplace is None:
                request.workplace = get_active_workplace(request)
                return redirect('workplaces:workplaces')
            set_active_workplace(request, workplace)
            enable_workspace_url_scope(request)
        else:
            request.workplace = get_active_workplace(request)

        if (
            request.method in {'GET', 'HEAD'}
            and request.workplace is not None
            and workspace_url_scope_enabled(request)
        ):
            scoped_path = legacy_app_path_to_scoped(
                request.workplace,
                request.path_info,
                request.META.get('QUERY_STRING', ''),
            )
            if scoped_path:
                return redirect(scoped_path)

        return self.get_response(request)
