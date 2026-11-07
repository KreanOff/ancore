from urllib.parse import parse_qs, urlsplit

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase

from .frontend import pagination_payload
from .list_window import window_page, window_payload, window_url


class ListWindowTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.items = list(range(45))

    def test_next_urls_keep_the_visible_prefix_and_finish_at_the_total(self):
        url = '/workplaces/team/spaces/?q=Projekt&status=open&status=blocked&sort=name'
        for loaded in (20, 40, 45):
            request = self.factory.get(url)
            page = window_page(self.items, request)
            data = pagination_payload(request, page)
            self.assertEqual(list(page), self.items[:loaded])
            self.assertEqual((data['count'], data['start'], data['end']), (45, 1, loaded))
            self.assertEqual((data['previous'], data['pages']), ('', []))
            if loaded < 45:
                url = data['next']
                query = parse_qs(urlsplit(url).query)
                self.assertEqual(query['q'], ['Projekt'])
                self.assertEqual(query['status'], ['open', 'blocked'])
                self.assertEqual(query['sort'], ['name'])
                self.assertNotIn('page', query)
            else:
                self.assertEqual(data['next'], '')

    def test_old_pages_are_cumulative_and_ignore_old_page_size(self):
        for params, expected in [({'page': '2', 'page_size': '100'}, 40),
                                 ({'page': '3'}, 45), ({'page': '99999'}, 45),
                                 ({'page': '2', 'limit': '20'}, 20)]:
            with self.subTest(params=params):
                request = self.factory.get('/items/', params)
                page = window_page(self.items, request)
                self.assertEqual(list(page), self.items[:expected])
                self.assertNotIn('page_size', window_url(request, page))

    def test_malformed_limits_fall_back_and_huge_limits_are_clamped(self):
        for value in ('', '-1', 'bad', '1.5', ' 40', '２０', '٤٠'):
            with self.subTest(limit=value):
                page = window_page(self.items, self.factory.get('/', {'limit': value}))
                self.assertEqual(list(page), self.items[:20])
        for value, expected in [('0', 20), ('1', 20), ('00040', 40), ('9' * 5000, 45)]:
            with self.subTest(limit=value[:10]):
                page = window_page(self.items, self.factory.get('/', {'limit': value}))
                self.assertEqual(list(page), self.items[:expected])

    def test_empty_results_and_small_lists_have_no_footer(self):
        for items in ([], list(range(20))):
            request = self.factory.get('/')
            page = window_page(items, request)
            data = window_payload(request, page)
            self.assertEqual((data['count'], data['end']), (len(items), len(items)))
            self.assertEqual(data['start'], 1 if items else 0)
            self.assertEqual(data['next_url'], '')
            html = render_to_string('core/includes/load_more.html', {'loaded': len(items), 'total': len(items)})
            self.assertNotIn('<button', html)
            self.assertNotIn('<a ', html)

    def test_footer_exposes_one_next_action_then_a_disabled_end_state(self):
        html = render_to_string('core/includes/load_more.html', {'loaded': 20, 'total': 45, 'next_url': '/?limit=40'})
        self.assertIn('Pokaż więcej', html)
        self.assertIn('href="/?limit=40"', html)
        self.assertIn('(20 / 45)', html)
        html = render_to_string('core/includes/load_more.html', {'loaded': 45, 'total': 45})
        self.assertIn('disabled', html)
        self.assertIn('Wszystkie wyniki', html)
        self.assertNotIn('<a ', html)

    def test_nested_windows_keep_their_own_parameter_and_existing_filters(self):
        request = self.factory.get('/task/', {'tab': 'main', 'q': 'Query', 'work_log_page': '2'})
        page = window_page(self.items, request, limit_parameter='work_log_limit', page_parameter='work_log_page')
        query = parse_qs(urlsplit(window_url(request, page, extra={'tab': 'work-log'})).query)
        self.assertEqual(query, {'tab': ['work-log'], 'q': ['Query'], 'work_log_limit': ['45']})
        request = self.factory.get('/resource/overview/', {'history_page': '2'})
        page = window_page(self.items, request, limit_parameter='history_limit', page_parameter='history_page')
        self.assertEqual(window_url(request, page), '/resource/overview/?history_limit=45')

    def test_module_can_preserve_only_its_validated_query_parameters(self):
        request = self.factory.get('/resources/', {'q': 'x', 'page': '1', 'next': 'https://example.test'})
        page = window_page(self.items, request)
        self.assertEqual(window_url(request, page, parameters={'q': 'x'}), '/resources/?q=x&limit=40')
