"""Small, explicit bridge to the existing session/account operations.

Only login and registration, including its session-bound Workspace step, allow
an anonymous session. The general page API remains authenticated; this endpoint
never proxies other application routes.
"""
from copy import copy
from urllib.parse import urlsplit

from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse, QueryDict
from django.urls import reverse, resolve
from django.utils.cache import patch_vary_headers
from django.views.decorators.debug import sensitive_post_parameters

from core.api import api_error, json_object


@sensitive_post_parameters('password', 'password1', 'password2')
def accounts_api(request):
    if request.method not in {'GET', 'POST'}:
        response = api_error('Ta metoda żądania nie jest obsługiwana.', 405)
        response['Allow'] = 'GET, POST'
        return response
    target = request.GET.get('url', '')
    try:
        parsed = urlsplit(target)
    except ValueError:
        return api_error('Nieprawidłowy adres ekranu.', 400)
    if not target.startswith('/') or target.startswith('//') or parsed.netloc or parsed.scheme or '\\' in target:
        return api_error('Nieprawidłowy adres ekranu.', 400)
    routes = {reverse(name): name for name in (
        'login', 'register', 'register_workspace', 'select_workspace', 'profile', 'add_account', 'update_presence_status',
        'switch_account', 'remove_account', 'logout',
    )}
    name = routes.get(parsed.path)
    if not name:
        try:
            match = resolve(parsed.path)
            if match.view_name == 'workplaces:join-link':
                name = 'join'
        except Http404:
            pass
    if not name:
        return api_error('Nie znaleziono elementu.', 404)
    if name not in {'login', 'register', 'join'} and not request.user.is_authenticated:
        return api_error('Sesja wygasła. Zaloguj się ponownie.', 401)
    if request.method == 'GET' and name not in {'login', 'register', 'register_workspace', 'select_workspace', 'profile', 'add_account', 'join'}:
        response = api_error('Ta metoda żądania nie jest obsługiwana.', 405)
        response['Allow'] = 'POST'
        return response
    delegated = copy(request)
    delegated.META = request.META.copy()
    delegated.path = delegated.path_info = parsed.path
    delegated.META.update(PATH_INFO=parsed.path, QUERY_STRING=parsed.query)
    delegated.GET = QueryDict(parsed.query)
    delegated.resolver_match = resolve(parsed.path)
    delegated._react_api = True
    if request.method == 'POST' and request.content_type == 'application/json':
        try:
            values = json_object(request)
        except ValueError as error:
            return api_error(str(error), 400)
        delegated.POST = QueryDict(mutable=True)
        for key, value in values.items():
            delegated.POST[key] = str(value)
    try:
        response = delegated.resolver_match.func(delegated, *delegated.resolver_match.args, **delegated.resolver_match.kwargs)
    except Http404:
        return api_error('Nie znaleziono elementu.', 404)
    except PermissionDenied:
        return api_error('Dodaj konto ponownie, podając aktualne hasło.', 403)
    # login() rotates CSRF and can replace the authenticated user. Propagate the
    # state to middleware as well as the shared session before returning JSON.
    request.user = delegated.user
    for key in ('CSRF_COOKIE', 'CSRF_COOKIE_NEEDS_UPDATE'):
        if key in delegated.META:
            request.META[key] = delegated.META[key]
    if response.status_code in {301, 302, 303, 307, 308}:
        original = response
        response = JsonResponse({'redirect': original['Location']})
        # LoginView's inner csrf_protect may already have written the rotated
        # token cookie and reset NEEDS_UPDATE. Keep it when adapting redirects.
        response.cookies.update(original.cookies)
    elif not response.get('Content-Type', '').startswith('application/json'):
        response = api_error('Ta operacja nie jest obsługiwana.', response.status_code if response.status_code >= 400 else 501)
    response['Cache-Control'] = 'no-store'
    patch_vary_headers(response, ('Cookie',))
    return response
