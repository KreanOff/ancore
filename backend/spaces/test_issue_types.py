from .testing import make_space
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from core.frontend import form_payload
from dashboard.filter_forms import BasicTaskSearchForm
from .models import SpaceTask, SpaceMembership
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path
from .defaults import TEMPLATES, issue_type_icon, template_settings
from .models import WorkItem


class IssueTypeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.owner = User.objects.create_user(username='issue-owner', email='issue-owner@example.test')
        cls.member = User.objects.create_user(username='issue-member', email='issue-member@example.test')
        cls.observer = User.objects.create_user(username='issue-observer', email='issue-observer@example.test')
        cls.other = User.objects.create_user(username='issue-other', email='issue-other@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'Typy zgłoszeń')
        cls.foreign = create_workplace_for_user(cls.other, 'Obcy Workspace')
        for user in (cls.member, cls.observer):
            WorkplaceMembership.objects.create(workplace=cls.workspace, user=user, role='member')
        cls.project = make_space(name='Marketing', user=cls.owner, workplace=cls.workspace, visibility='private', private_owner=cls.owner)
        for user, role in ((cls.member, 'member'), (cls.observer, 'observer')):
            SpaceMembership.objects.create(space=cls.project, user=user, role=role)
        cls.space = cls.project
        cls.space.template = 'marketing'
        cls.space.save()
        cls.space.configuration.settings = template_settings('marketing')
        cls.space.configuration.save()
        cls.section = cls.project
        cls.task = SpaceTask.objects.create(created_by=cls.owner, space=cls.section, title='Kampania zespołu')
        cls.item = cls.task.work_item

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def url(self, suffix='', app='spaces', scoped=True):
        return scoped_workplace_app_path(self.workspace, app, suffix) if scoped else f'/{app}/{suffix}'

    def detail_url(self, scoped=True):
        return self.url(f'{self.space.slug}/tasks/{self.item.key}/', app='space', scoped=scoped)

    def detail_data(self, work_type='bug'):
        return {'title': self.task.title, 'visibility': 'public', 'section': self.section.pk,
                'project': self.project.pk, 'priority': 'medium', 'status': 'new',
                'task_type': 'general', 'work_type': work_type, 'epic': self.item.epic_id or ''}

    def test_all_templates_offer_standard_types_and_keep_domain_defaults(self):
        for template in TEMPLATES:
            types = template_settings(template)['types']
            self.assertTrue({'task', 'bug', 'story', 'epic'}.issubset({row['key'] for row in types}))
        self.assertEqual(template_settings('service')['types'][0]['key'], 'request')
        self.assertEqual(template_settings('recruitment')['types'][0]['key'], 'candidate')
        self.assertTrue({'campaign', 'content'}.issubset({row['key'] for row in template_settings('marketing')['types']}))

    def test_creation_and_edit_in_marketing_use_same_task_and_actor(self):
        for scoped in (False, True):
            response = self.client.post(self.url(f'{self.space.pk}/items/create/', scoped=scoped),
                                        {'title': f'Błąd {scoped}', 'priority': 'medium', 'work_type': 'bug'}, HTTP_X_WORK_MODAL='true')
            self.assertEqual(response.status_code, 200)
            task = SpaceTask.objects.get(title=f'Błąd {scoped}')
            self.assertEqual(task.work_item.work_type, 'bug')
            self.assertEqual(task.space.user, self.owner)
            self.assertEqual(task.activities.get(action='created').actor, self.member)
            self.assertEqual(task.work_item.space, self.space)
            response = self.client.post(self.url(f'items/{task.work_item.pk}/edit/', scoped=scoped),
                                        {'title': task.title, 'priority': 'medium', 'work_type': 'story'}, HTTP_X_WORK_MODAL='true')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(WorkItem.objects.get(task=task).work_type, 'story')
            activity = task.activities.get(action='updated')
            self.assertEqual(activity.actor, self.member)
            self.assertEqual(activity.metadata['changes'], [{'field': 'typ zgłoszenia', 'from_label': 'Błąd', 'to_label': 'Historyjka'}])

    def test_detail_edit_and_reopen_keep_type_and_history(self):
        for scoped, work_type in ((False, 'bug'), (True, 'campaign')):
            response = self.client.post(self.detail_url(scoped), self.detail_data(work_type), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['status'], 'success')
            self.assertEqual(WorkItem.objects.get(pk=self.item.pk).work_type, work_type)
            activity = self.task.activities.filter(action='updated').latest('id')
            self.assertEqual(activity.actor, self.member)
            self.assertEqual(activity.metadata['before']['work_type'], 'task' if scoped is False else 'bug')
            response = self.client.get(self.detail_url(scoped))
            self.assertContains(response, 'Typ zgłoszenia')
            field = response.context['form']['work_type']
            self.assertEqual(field.value(), work_type)
            self.assertIn(work_type, {value for value, label in field.field.widget.choices})
        self.assertEqual(self.task.activities.filter(action='updated').count(), 2)

    def test_other_detail_edits_do_not_reset_type(self):
        self.item.work_type = 'campaign'
        self.item.save()
        data = self.detail_data()
        data['work_type'] = 'campaign'
        response = self.client.post(self.detail_url(), data, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'success')
        self.assertEqual(WorkItem.objects.get(pk=self.item.pk).work_type, 'campaign')
        self.assertEqual(self.task.activities.latest('pk').actor, self.member)

    def test_unknown_or_unconfigured_type_leaves_task_unchanged(self):
        config = self.space.configuration
        config.settings['types'] = [{'key': 'task', 'label': 'Zadanie'}]
        config.save()
        for work_type in ('unknown', 'bug'):
            for url, data, headers in (
                (self.detail_url(), self.detail_data(work_type), {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}),
                (self.url(f'items/{self.item.pk}/edit/'), {'title': 'Zmiana', 'priority': 'medium', 'work_type': work_type}, {'HTTP_X_WORK_MODAL': 'true'}),
            ):
                response = self.client.post(url, data, **headers)
                self.assertEqual(response.status_code, 400)
                self.task.refresh_from_db()
                self.assertEqual(self.task.title, 'Kampania zespołu')
                self.assertEqual(WorkItem.objects.get(pk=self.item.pk).work_type, 'task')

    def test_observer_and_foreign_workspace_cannot_change_type(self):
        for user in (self.observer, self.other):
            self.client.force_login(user)
            for scoped in (False, True):
                response = self.client.post(self.detail_url(scoped), self.detail_data(), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
                self.assertIn(response.status_code, (302, 403, 404))
                response = self.client.post(self.url(f'items/{self.item.pk}/edit/', scoped=scoped),
                                            {'title': self.task.title, 'priority': 'medium', 'work_type': 'bug'}, HTTP_X_WORK_MODAL='true')
                self.assertIn(response.status_code, (302, 403, 404))
                self.assertEqual(WorkItem.objects.get(pk=self.item.pk).work_type, 'task')
        self.assertEqual(WorkItem.objects.get(pk=self.item.pk).work_type, 'task')

    def test_type_filters_combine_with_search_and_preserve_privacy(self):
        self.item.work_type = 'bug'
        self.item.save()
        SpaceTask.objects.create(created_by=self.owner, space=self.section, title='Zwykłe zadanie')
        hidden = SpaceTask.objects.create(created_by=self.owner, space=self.section, title='Poufny błąd', visibility='private', private_owner=self.owner)
        WorkItem.objects.filter(task=hidden).update(work_type='bug')
        for scoped in (False, True):
            for suffix, app in ((f'{self.space.slug}/?view=list', 'space'), (f'{self.space.slug}/?view=board', 'space'), ('items/?', 'spaces')):
                response = self.client.get(self.url(suffix, app=app, scoped=scoped) + '&work_type=bug&q=zespołu', follow=True)
                self.assertContains(response, self.task.title)
                self.assertNotContains(response, 'Zwykłe zadanie')
                self.assertNotContains(response, 'Poufny błąd')
                if app == 'spaces':
                    self.assertEqual(response.context['search_form'].cleaned_data['type'], ['bug'])
                else:
                    self.assertContains(response, 'Typ zgłoszenia: Błąd')
            response = self.client.get(self.url(f'{self.space.slug}/?view=list&work_type=unknown', app='space', scoped=scoped), follow=True)
            self.assertEqual(sum(column['count'] for column in response.context['columns']), 0)

    def test_epic_relations_are_validated_in_detail_form(self):
        self.item.work_type = 'epic'
        self.item.save()
        child = SpaceTask.objects.create(created_by=self.owner, space=self.section, title='Część epika')
        WorkItem.objects.filter(task=child).update(epic=self.item)
        response = self.client.post(self.detail_url(), self.detail_data('bug'), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(WorkItem.objects.get(pk=self.item.pk).work_type, 'epic')
        self.item.work_type, self.item.epic = 'task', child.work_item
        self.item.save()
        response = self.client.post(self.detail_url(), self.detail_data('epic'), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(response.status_code, 400)

    def test_history_failure_rolls_back_type(self):
        with patch('spaces.task_views.record', side_effect=RuntimeError('History failure')):
            with self.assertRaises(RuntimeError):
                self.client.post(self.detail_url(), self.detail_data(), HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(WorkItem.objects.get(pk=self.item.pk).work_type, 'task')

    def test_configured_icons_reach_tasks_filters_forms_summary_and_search(self):
        config = self.space.configuration
        config.settings['types'].append({'key': 'review', 'label': 'Przegląd', 'icon': 'shield-check', 'description': 'Kontrola jakości'})
        config.save()
        self.item.work_type = 'review'
        self.item.save(update_fields=['work_type'])
        self.item.refresh_from_db()
        self.assertEqual(self.item.type_icon, 'shield-check')
        for scoped in (False, True):
            with self.subTest(scoped=scoped):
                base = self.url(self.space.slug + '/', app='space', scoped=scoped)
                api = self.url('v1/page/', app='api', scoped=scoped)
                response = self.client.get(api, {'url': base + '?view=list'})
                self.assertEqual(response.status_code, 200)
                data = response.json()['data']
                self.assertEqual(data['type_icons']['review'], 'shield-check')
                self.assertEqual(data['items'][0]['type_icon'], 'shield-check')
                summary = self.client.get(api, {'url': base}).json()['data']['summary']
                self.assertEqual(next(row for row in summary['types'] if row['key'] == 'review')['icon'], 'shield-check')
                detail = self.client.get(self.detail_url(scoped))
                fields = form_payload(detail.context['form'])['fields']
                work_type = next(field for field in fields if field['field_name'] == 'work_type')
                self.assertEqual(next(choice for choice in work_type['choices'] if choice['value'] == 'review')['icon'], 'shield-check')
                filter_form = BasicTaskSearchForm(request=detail.wsgi_request)
                type_field = next(field for field in form_payload(filter_form)['fields'] if field['field_name'] == 'type')
                self.assertEqual(next(choice for choice in type_field['choices'] if choice['value'] == 'review')['icon'], 'shield-check')
                self.assertContains(detail, 'data-ancore-option-icon="shield-check"')
        search = self.client.get(reverse('global_search'), {'q': self.task.title}).json()
        results = [row for group in search['groups'] for row in group['results']]
        self.assertEqual(next(row for row in results if row['title'] == self.task.title)['icon'], 'shield-check')

    def test_icon_resolver_keeps_legacy_defaults_and_rejects_untrusted_names(self):
        for key, expected in [('bug', 'circle-alert'), ('task', 'square-check'), ('custom', 'shapes')]:
            for configured in (None, '', 'not-in-catalog', '<svg onload="alert(1)">', ['target']):
                with self.subTest(key=key, configured=configured):
                    self.assertEqual(issue_type_icon(key, configured), expected)
            self.assertEqual(issue_type_icon(key, 'target'), 'target')


    def test_type_colors_follow_configuration_in_views_forms_and_first_render(self):
        config = self.space.configuration
        config.settings['types'].append({'key': 'review', 'label': 'Przegląd', 'icon': 'square-check', 'color': '#ee33cc'})
        config.save()
        self.item.work_type = 'review'
        self.item.save(update_fields=['work_type'])
        for scoped in (False, True):
            base = self.url(self.space.slug + '/', app='space', scoped=scoped)
            api = self.url('v1/page/', app='api', scoped=scoped)
            for view in ('list', 'board', 'backlog', 'timeline', 'summary', 'reports'):
                with self.subTest(scoped=scoped, view=view):
                    response = self.client.get(api, {'url': base + '?view=' + view}, follow=True)
                    self.assertEqual(response.status_code, 200)
                    data = response.json()['data']
                    self.assertEqual(data['type_colors']['review'], '#ee33cc')
                    self.assertEqual(data['type_colors']['task'], '#2563eb')
                    for item in data['items']:
                        if item['id'] == self.item.pk:
                            self.assertEqual(item['type_color'], '#ee33cc')
                    if view == 'summary':
                        self.assertEqual(next(t['color'] for t in data['summary']['types'] if t['key'] == 'review'), '#ee33cc')
                    if view in ('list', 'board'):
                        self.assertContains(self.client.get(base + '?view=' + view), 'background-color: color-mix(in srgb, #ee33cc 16%, #ffffff)')
            detail = self.client.get(api, {'url': self.detail_url(scoped)}, follow=True).json()['data']
            self.assertEqual(detail['item']['type_color'], '#ee33cc')
            choices = next(f['choices'] for f in detail['form']['fields'] if f['field_name'] == 'work_type')
            self.assertEqual(next(c['type_color'] for c in choices if c['value'] == 'review'), '#ee33cc')
            response = self.client.get(self.detail_url(scoped))
            self.assertContains(response, '--tasks-type-icon-color: #ee33cc')
            filter_form = BasicTaskSearchForm(request=response.wsgi_request)
            choices = next(f['choices'] for f in form_payload(filter_form)['fields'] if f['field_name'] == 'type')
            self.assertEqual(next(c['type_color'] for c in choices if c['value'] == 'review'), '#ee33cc')

    def test_type_color_is_local_to_space_and_reset_does_not_change_task(self):
        config = self.space.configuration
        other_space = make_space(user=self.owner, workplace=self.workspace, name='Inny kolor')
        other_task = SpaceTask.objects.create(created_by=self.owner, space=other_space, title='Niezależny kolor')
        for color, expected in [('#27ab91', '#27ab91'), ('', '#2563eb')]:
            definition = next(t for t in config.settings['types'] if t['key'] == 'task')
            definition.update(icon='circle-alert', color=color)
            config.save()
            item = WorkItem.objects.select_related('space__configuration').get(pk=self.item.pk)
            self.assertEqual(item.type_color, expected)
            self.assertEqual(item.type_icon, 'circle-alert')
            self.assertEqual(other_task.work_item.type_color, '#2563eb')
            self.assertEqual(item.work_type, 'task')
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'new')
        self.assertIsNone(self.task.completion_date)
