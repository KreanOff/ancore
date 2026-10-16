"""Session-authenticated JSON endpoints for the incrementally migrated UI."""
import json
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.views.csrf import csrf_failure as django_csrf_failure


def is_api_request(request):
    return '/api/v1/' in request.path_info


def api_error(message, status, **extra):
    response = JsonResponse({'message': message, **extra}, status=status)
    response['Cache-Control'] = 'no-store'
    return response


def api_view(methods):
    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return api_error('Sesja wygasła. Zaloguj się ponownie.', 401)
            if request.method not in methods:
                response = api_error('Ta metoda żądania nie jest obsługiwana.', 405)
                response['Allow'] = ', '.join(methods)
                return response
            try:
                response = view(request, *args, **kwargs)
            except Http404:
                response = api_error('Nie znaleziono elementu.', 404)
            except PermissionDenied:
                response = api_error('Nie masz dostępu do tych danych.', 403)
            response['Cache-Control'] = 'no-store'
            return response
        return wrapped
    return decorate


def json_object(request):
    if request.content_type != 'application/json':
        raise ValueError('Wyślij dane w formacie JSON.')
    try:
        data = json.loads(request.body)
    except (ValueError, UnicodeDecodeError) as error:
        raise ValueError('Nieprawidłowe dane JSON.') from error
    if not isinstance(data, dict) or any(isinstance(value, (dict, list)) for value in data.values()):
        raise ValueError('Oczekiwano obiektu z wartościami pól formularza.')
    return {key: '' if value is None else value for key, value in data.items()}


def csrf_failure(request, reason=''):
    if is_api_request(request):
        return api_error('Sesja formularza wygasła. Odśwież stronę i spróbuj ponownie.', 403)
    return django_csrf_failure(request, reason=reason)
