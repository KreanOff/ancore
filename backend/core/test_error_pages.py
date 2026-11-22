from copy import deepcopy

from django.conf import settings
from django.core.exceptions import BadRequest, PermissionDenied
from django.db import OperationalError
from django.test import Client, SimpleTestCase, override_settings
from django.urls import path, reverse

from ancore import urls as application_urls


PRIVATE_DETAIL = 'Szczegóły wewnętrzne awarii'


def bad_request(request):
    raise BadRequest(PRIVATE_DETAIL)


def forbidden(request):
    raise PermissionDenied(PRIVATE_DETAIL)


def unavailable_database(request):
    raise OperationalError(PRIVATE_DETAIL)


def unexpected_context_processor(request):
    raise AssertionError('Strona błędu uruchomiła procesory kontekstu żądania.')


urlpatterns = [
    path('_test-errors/bad-request/', bad_request),
    path('_test-errors/forbidden/', forbidden),
    path('_test-errors/database/', unavailable_database),
    path('api/v1/_test-errors/bad-request/', bad_request),
    path('api/v1/_test-errors/database/', unavailable_database),
    path('workplaces/example/api/v1/_test-errors/forbidden/', forbidden),
    *application_urls.urlpatterns,
]
handler400 = application_urls.handler400
handler403 = application_urls.handler403
handler404 = application_urls.handler404
handler500 = application_urls.handler500


@override_settings(
    ALLOWED_HOSTS=['testserver'],
    ALLOW_IP_HOSTS=False,
    DEBUG=False,
    SECURE_SSL_REDIRECT=False,
)
class ErrorPageTests(SimpleTestCase):
    def assert_error_page(self, response, status, heading):
        self.assertEqual(response.status_code, status)
        self.assertTrue(response.headers['Content-Type'].startswith('text/html'))
        self.assertIn('no-store', response.headers['Cache-Control'])
        html = response.content.decode()
        self.assertRegex(html, rf'<title>[^<]*\b{status}\b[^<]*</title>')
        self.assertRegex(html, rf'<h1\b[^>]*>\s*{heading}\s*</h1>')
        self.assertIn('<main', html)
        self.assertIn(f'href="{reverse("home")}"', html)
        self.assertNotIn(PRIVATE_DETAIL, html)

    def test_missing_browser_pages_in_global_and_workspace_routes(self):
        for url in (
            '/_test-errors/missing/',
            '/workplaces/example/space/missing/another-segment/',
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assert_error_page(response, 404, 'Nie znaleziono strony')

    def test_disallowed_host_renders_bad_request_without_echoing_host(self):
        host = 'rejected.example'
        response = self.client.get('/', HTTP_HOST=host)
        self.assert_error_page(response, 400, 'Nieprawidłowe żądanie')
        self.assertNotContains(response, host, status_code=400)

    @override_settings(ROOT_URLCONF=__name__)
    def test_production_error_pages_render_even_without_request_context(self):
        templates = deepcopy(settings.TEMPLATES)
        templates[0]['OPTIONS']['context_processors'].append(
            f'{__name__}.unexpected_context_processor',
        )
        client = Client(raise_request_exception=False)
        with self.settings(TEMPLATES=templates):
            for url, status, heading in (
                ('/_test-errors/bad-request/', 400, 'Nieprawidłowe żądanie'),
                ('/_test-errors/forbidden/', 403, 'Brak dostępu'),
                ('/_test-errors/database/', 500, 'Błąd serwera'),
            ):
                with self.subTest(status=status):
                    self.assert_error_page(client.get(url), status, heading)

    @override_settings(ROOT_URLCONF=__name__)
    def test_api_errors_retain_json_for_global_and_workspace_routes(self):
        client = Client(raise_request_exception=False)
        for url, status in (
            ('/api/v1/_test-errors/bad-request/', 400),
            ('/api/v1/_test-errors/missing/', 404),
            ('/workplaces/example/api/v1/_test-errors/missing/', 404),
            ('/workplaces/example/api/v1/_test-errors/forbidden/', 403),
            ('/api/v1/_test-errors/database/', 500),
        ):
            with self.subTest(url=url):
                response = client.get(url)
                self.assertEqual(response.status_code, status)
                self.assertEqual(response.headers['Content-Type'], 'application/json')
                self.assertIn('no-store', response.headers['Cache-Control'])
                self.assertTrue(response.json()['message'])
                self.assertNotIn(PRIVATE_DETAIL, response.content.decode())

    def test_csrf_failure_uses_error_page_and_keeps_api_message(self):
        client = Client(enforce_csrf_checks=True)
        response = client.post(reverse('login'))
        self.assert_error_page(response, 403, 'Nie udało się potwierdzić formularza')
        self.assertNotContains(response, 'CSRF cookie not set', status_code=403)

        for url in (reverse('react-page'), '/workplaces/example/api/v1/page/'):
            with self.subTest(url=url):
                response = client.post(url)
                self.assertEqual(response.status_code, 403)
                self.assertIn('no-store', response.headers['Cache-Control'])
                self.assertEqual(response.json(), {
                    'message': 'Sesja formularza wygasła. Odśwież stronę i spróbuj ponownie.',
                })
