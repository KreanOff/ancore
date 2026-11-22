"""HTTP error responses that can render even when the database is unavailable."""
from django.shortcuts import render

from core.api import api_error, is_api_request


ERROR_PAGES = {
    400: ('Nieprawidłowe żądanie', 'Sprawdź adres strony i spróbuj ponownie.'),
    403: ('Brak dostępu', 'Twoje konto nie ma uprawnień do tej strony lub działania.'),
    404: ('Nie znaleziono strony', 'Sprawdź adres. Strona mogła zostać przeniesiona lub usunięta.'),
    500: ('Błąd serwera', 'Nie udało się wczytać strony. Spróbuj ponownie za chwilę.'),
    503: ('Usługa jest chwilowo niedostępna', 'Spróbuj ponownie za chwilę.'),
}

API_MESSAGES = {
    403: 'Nie masz dostępu do tych danych.',
    404: 'Nie znaleziono elementu.',
}


def render_error(status, *, title=None, description=None):
    default_title, default_description = ERROR_PAGES[status]
    # Rendering without a request skips session and Workspace context processors.
    response = render(None, 'core/http_error.html', {
        'status': status,
        'title': title or default_title,
        'description': description or default_description,
    }, status=status)
    response['Cache-Control'] = 'no-store'
    return response


def _error_response(request, status):
    if is_api_request(request):
        return api_error(API_MESSAGES.get(status, f'{ERROR_PAGES[status][0]}.'), status)
    return render_error(status)


def bad_request(request, exception):
    return _error_response(request, 400)


def permission_denied(request, exception):
    return _error_response(request, 403)


def page_not_found(request, exception):
    return _error_response(request, 404)


def server_error(request):
    return _error_response(request, 500)


def csrf_failure(request, reason=''):
    if is_api_request(request):
        return api_error('Sesja formularza wygasła. Odśwież stronę i spróbuj ponownie.', 403)
    return render_error(
        403,
        title='Nie udało się potwierdzić formularza',
        description='Wróć do formularza, odśwież stronę i spróbuj wysłać go ponownie.',
    )
