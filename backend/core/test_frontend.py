import json
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from planner.models import CalendarEvent
from spaces.models import SpaceTask
from spaces.testing import make_space
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path


class ReactPageApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='react-owner', email='react-owner@example.test')
        cls.member = users.objects.create_user(username='react-member', email='react-member@example.test')
        cls.outsider = users.objects.create_user(username='react-outsider', email='react-outsider@example.test')
        cls.workspace = create_workplace_for_user(cls.owner, 'React API')
        cls.other = create_workplace_for_user(cls.owner, 'Drugi React API')
        cls.foreign = create_workplace_for_user(cls.outsider, 'Obcy React API')
        cls.membership = WorkplaceMembership.objects.create(workplace=cls.workspace, user=cls.member)
        cls.space = make_space(user=cls.owner, workplace=cls.workspace, name='Dostępna przestrzeń', visibility='public')
        cls.private = make_space(user=cls.owner, workplace=cls.workspace, name='Ukryta przestrzeń', visibility='private', private_owner=cls.owner)
        cls.task = SpaceTask.objects.create(space=cls.space, created_by=cls.owner, title='Widoczne zadanie', assignee=cls.member, priority='high', due_at=timezone.now() + timedelta(days=1))
        cls.hidden = SpaceTask.objects.create(space=cls.private, created_by=cls.owner, title='Ukryte zadanie', assignee=cls.member, priority='high')

    def setUp(self):
        self.client.force_login(self.member)
        session = self.client.session
        session['active_workplace_id'] = self.workspace.pk
        session.save()

    def api(self, workspace=None):
        return scoped_workplace_app_path(workspace or self.workspace, 'api', 'v1/page/')

    def path(self, app, suffix='', workspace=None):
        return scoped_workplace_app_path(workspace or self.workspace, app, suffix)

    def test_known_screens_have_typed_json_and_react_bootstrap(self):
        for path, kind in [(self.path('calendar'), 'calendar'), (self.path('for-you'), 'for-you'), (reverse('settings'), 'settings')]:
            with self.subTest(kind=kind):
                response = self.client.get(self.api(), {'url': path})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['type'], kind)
                self.assertEqual(response.json()['api_url'], self.api())
                self.assertNotIn('html', response.json())
                self.assertEqual(response['Cache-Control'], 'no-store')
                self.assertContains(self.client.get(path), 'data-react-root="page"')

    def test_personal_rows_use_space_acl_and_do_not_expose_private_assignment(self):
        response = self.client.get(self.api(), {'url': self.path('for-you') + '?tab=assigned'})
        data = json.dumps(response.json(), ensure_ascii=False)
        self.assertIn(self.task.title, data)
        self.assertNotIn(self.hidden.title, data)
        self.assertNotIn(self.private.name, data)
        self.assertEqual(response.json()['data']['assigned_count'], 1)

    def test_settings_management_links_follow_existing_permissions(self):
        data = self.client.get(self.api(), {'url': reverse('settings')}).json()['data']
        self.assertEqual(data['user']['email'], self.member.email)
        titles = [row['title'] for row in data['rows']]
        self.assertNotIn('Zarządzaj przestrzeniami', titles)
        self.assertNotIn('Panel administracyjny', titles)
        self.assertNotIn('Zarządzaj filtrami', titles)

    def test_proxy_is_allowlisted_and_cannot_cross_workspace_context(self):
        for target in ['/admin/', '/resources/', '/accounts/logout/', self.api()]:
            self.assertEqual(self.client.get(self.api(), {'url': target}).status_code, 404)
        self.client.force_login(self.owner)
        for target in [self.path('calendar', workspace=self.other), self.path('for-you', workspace=self.other)]:
            self.assertEqual(self.client.get(self.api(), {'url': target}).status_code, 403)

    def test_rejects_external_urls_and_malformed_targets(self):
        for target in ['https://example.test/', '//example.test/', '/\\example.test/', 'calendar/', '']:
            self.assertEqual(self.client.get(self.api(), {'url': target}).status_code, 400)

    def test_json_auth_revocation_and_methods(self):
        target = self.path('calendar')
        self.assertEqual(self.client.post(self.api() + '?url=' + target).status_code, 200)
        self.assertEqual(self.client.post(self.api() + '?url=' + self.path('calendar', 'events/')).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.get(self.api(), {'url': target}).status_code, 401)
        self.client.force_login(self.member)
        self.membership.is_active = False
        self.membership.save()
        self.assertEqual(self.client.get(self.api(), {'url': target}).status_code, 403)

    def test_calendar_crud_keeps_owner_actor_context_and_validates(self):
        start = timezone.localtime().replace(second=0, microsecond=0)
        values = {'title': 'Wydarzenie React', 'description': 'Opis', 'start': start.strftime('%Y-%m-%dT%H:%M'), 'end': (start + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'), 'color': 'blue', 'user': self.outsider.pk, 'workplace': self.foreign.pk}
        created = self.client.post(self.api(), values, QUERY_STRING='url=' + self.path('calendar', 'events/create/'))
        self.assertEqual(created.status_code, 200)
        event = CalendarEvent.objects.get(pk=created.json()['event']['id'])
        self.assertEqual((event.user_id, event.workplace_id), (self.owner.pk, self.workspace.pk))
        updated = self.client.post(self.api(), {**values, 'title': 'Zmienione wydarzenie'}, QUERY_STRING='url=' + self.path('calendar', f'events/{event.pk}/update/'))
        self.assertEqual(updated.status_code, 200)
        event.refresh_from_db()
        self.assertEqual(event.title, 'Zmienione wydarzenie')
        invalid = self.client.post(self.api(), {**values, 'end': (start - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M')}, QUERY_STRING='url=' + self.path('calendar', f'events/{event.pk}/update/'))
        self.assertEqual(invalid.status_code, 400)
        event.refresh_from_db()
        self.assertEqual(event.title, 'Zmienione wydarzenie')
        self.assertEqual(self.client.post(self.api(), QUERY_STRING='url=' + self.path('calendar', f'events/{event.pk}/delete/')).status_code, 200)
        self.assertFalse(CalendarEvent.objects.filter(pk=event.pk).exists())

    def test_calendar_cross_workspace_record_is_not_accessible_through_api(self):
        event = CalendarEvent.objects.create(user=self.owner, workplace=self.other, title='Tajne wydarzenie', start=timezone.now(), end=timezone.now())
        for operation in ['update', 'delete']:
            response = self.client.post(self.api(), QUERY_STRING='url=' + self.path('calendar', f'events/{event.pk}/{operation}/'))
            self.assertEqual(response.status_code, 404)
        self.assertTrue(CalendarEvent.objects.filter(pk=event.pk).exists())

    def test_csrf_is_enforced_and_dom_token_can_be_used_with_httponly_cookie(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.member)
        target = self.path('calendar', 'events/create/')
        self.assertEqual(client.post(self.api(), QUERY_STRING='url=' + target).status_code, 403)
        with self.settings(CSRF_COOKIE_HTTPONLY=True):
            page = client.get(self.path('calendar'))
            token = str(page.context['csrf_token'])
            self.assertTrue(client.cookies[settings.CSRF_COOKIE_NAME]['httponly'])
            response = client.post(self.api(), {}, QUERY_STRING='url=' + target, HTTP_X_CSRFTOKEN=token)
            self.assertEqual(response.status_code, 400)
            self.assertIn('title', response.json()['errors'])

    def test_space_directory_and_details_keep_private_rows_out_of_api(self):
        response = self.client.get(self.api(), {'url': self.path('spaces')})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['type'], 'space-directory')
        self.assertEqual([space['id'] for space in response.json()['data']['results']], [self.space.pk])
        for view in ['overview', 'list', 'board', 'timeline', 'reports', 'settings']:
            with self.subTest(view=view):
                path = self.path('space', f'{self.space.slug}/?view={view}')
                response = self.client.get(self.api(), {'url': path})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['type'], 'space-detail')
                self.assertNotIn(self.hidden.title, json.dumps(response.json(), ensure_ascii=False))
                self.assertContains(self.client.get(path), 'data-react-root="page"')
        for suffix in ['', 'edit/', 'items/create/']:
            path = self.path('space', f'{self.private.slug}/{suffix}')
            self.assertEqual(self.client.get(self.api(), {'url': path}).status_code, 404)

    def test_space_forms_expose_validated_fields_and_scoped_urls(self):
        target = self.path('spaces', 'create/')
        response = self.client.get(self.api(), {'url': target})
        self.assertEqual(response.json()['type'], 'form')
        schema = response.json()['data']['form']
        self.assertEqual(len(schema['templates']), 6)
        fields = {field['name']: field for field in schema['fields']}
        self.assertTrue(fields['template']['hidden'])
        self.assertNotIn('user', fields)
        values = {'name': 'Nowa React', 'key': self.space.key, 'kind': 'business', 'template': 'tasks', 'management': 'team', 'visibility': 'public'}
        invalid = self.client.post(self.api(), values, QUERY_STRING='url=' + target)
        self.assertEqual(invalid.status_code, 400)
        self.assertTrue(next(field for field in invalid.json()['data']['form']['fields'] if field['name'] == 'key')['errors'])
        saved = self.client.post(self.api(), {**values, 'key': 'NEWREACT'}, QUERY_STRING='url=' + target)
        self.assertEqual(saved.status_code, 200)
        from spaces.models import Space
        created = Space.objects.get(key='NEWREACT', workplace=self.workspace)
        self.assertEqual(created.user, self.owner)
        self.assertEqual(created.responsible_user, self.member)
        self.assertIn('/workplaces/', saved.json()['redirect'])

    def test_item_api_preserves_status_history_and_completion(self):
        self.client.force_login(self.owner)
        path = self.path('space', f'{self.space.slug}/?view=list')
        row = self.client.get(self.api(), {'url': path}).json()['data']['items'][0]
        target = row['action_url']
        # Follow the configured workflow; the default space does not allow new -> closed.
        for status in ['in_progress', 'resolved', 'closed']:
            with self.subTest(status=status):
                response = self.client.post(self.api(), {'action': 'status', 'status': status, 'return_view': 'list'}, QUERY_STRING='url=' + target)
                self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'closed')
        self.assertIsNotNone(self.task.completion_date)
        self.assertTrue(self.task.activities.filter(actor=self.owner, action='status_changed').exists())
        invalid = self.client.post(self.api(), {'action': 'status', 'status': 'does-not-exist'}, QUERY_STRING='url=' + target)
        self.assertEqual(invalid.status_code, 400)
        self.assertIn('error', invalid.json())
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, 'closed')

    def test_board_api_detects_stale_rank_without_partial_change(self):
        self.client.force_login(self.owner)
        path = self.path('space', f'{self.space.slug}/?view=board')
        row = self.client.get(self.api(), {'url': path}).json()['data']['items'][0]
        data = {'action':'position', 'space':self.space.pk, 'source_status':row['status'], 'status':row['status'], 'source_sprint':'', 'source_rank':row['rank']+1, 'before':'', 'after':'', 'before_rank':'', 'after_rank':''}
        response = self.client.post(self.api(), data, QUERY_STRING='url=' + row['action_url'])
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
        self.task.work_item.refresh_from_db()
        self.assertEqual(self.task.work_item.rank, row['rank'])

    def task_path(self):
        return self.path('space', f'{self.space.slug}/tasks/{self.task.work_item.key}/')

    def test_task_page_api_has_native_data_and_no_html_fragments(self):
        response = self.client.get(self.api(), {'url': self.task_path()})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['type'], 'space-task')
        self.assertEqual(data['data']['item']['key'], self.task.work_item.key)
        self.assertEqual(len(data['data']['tabs']), 5)
        self.assertEqual(data['data']['team']['members'][0]['avatar'].keys(), data['data']['created_by']['avatar'].keys())
        self.assertNotIn('html', json.dumps(data))
        self.assertContains(self.client.get(self.task_path()), 'data-react-root="page"')
        hidden = self.path('space', f'{self.private.slug}/tasks/{self.hidden.work_item.key}/')
        self.assertEqual(self.client.get(self.api(), {'url': hidden}).status_code, 404)

    def test_task_autosave_api_merges_live_planning_and_records_actor(self):
        from spaces.models import WorkItem
        item = self.task.work_item
        item.points = 8
        item.save()
        response = self.client.post(self.api(), {'action': 'save', 'title': 'Tytuł z React', 'autosave_fields': '["title"]'}, QUERY_STRING='url=' + self.task_path())
        self.assertEqual(response.status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Tytuł z React')
        self.assertEqual(self.task.assignee, self.member)
        self.assertEqual(WorkItem.objects.get(pk=item.pk).points, 8)
        self.assertTrue(self.task.activities.filter(actor=self.member, action='updated').exists())
        invalid = self.client.post(self.api(), {'action': 'save', 'title': '', 'autosave_fields': '["title"]'}, QUERY_STRING='url=' + self.task_path())
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.json()['type'], 'space-task')
        self.assertTrue(next(field for field in invalid.json()['data']['form']['fields'] if field['name'] == 'title')['errors'])
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Tytuł z React')

    def test_task_comment_subtask_and_work_log_operations_return_typed_data(self):
        target = self.task_path()
        response = self.client.post(self.api(), {'action': 'comment', 'message': 'Wiadomość React'}, QUERY_STRING='url=' + target)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.task.activities.filter(message='Wiadomość React', kind='comment', actor=self.member).exists())
        response = self.client.post(self.api(), {'action':'create_subtask_modal', 'subtask-title':'Podzadanie React', 'subtask-visibility':'public', 'subtask-status':'new'}, QUERY_STRING='url=' + target)
        self.assertEqual(response.status_code, 200)
        child = self.task.subtasks.get(title='Podzadanie React')
        self.assertEqual(child.created_by, self.member)
        start = timezone.localtime().replace(second=0, microsecond=0)
        values = {'action': 'add_work_log', 'worklog-started_at': start.strftime('%Y-%m-%dT%H:%M'), 'worklog-ended_at': (start + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M'), 'worklog-description': 'Praca w React'}
        self.assertEqual(self.client.post(self.api(), values, QUERY_STRING='url=' + target).status_code, 200)
        self.assertEqual(self.task.work_logs.get().duration_minutes, 60)
        page = self.client.get(self.api(), {'url': target}).json()['data']
        self.assertEqual(page['comments'][-1]['message'], 'Wiadomość React')
        self.assertEqual(page['children'][0]['key'], child.work_item.key)
        self.assertEqual(page['work_log']['total_minutes'], 60)
        self.assertNotIn('html', json.dumps(page))

    def test_task_team_api_keeps_inheritance_and_observer_readonly(self):
        from spaces.models import SpaceTaskMembership
        self.task.visibility, self.task.private_owner = 'private', self.owner
        self.task.save()
        SpaceTaskMembership.objects.create(task=self.task, user=self.member, role='observer')
        response = self.client.get(self.api(), {'url': self.task_path()})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['data']['can_edit'])
        self.assertTrue(all(field['disabled'] for field in response.json()['data']['form']['fields']))
        for values in [{'action': 'save', 'title':'Obca zmiana'}, {'action':'comment','message':'Obcy komentarz'}, {'action':'delete'}]:
            self.assertEqual(self.client.post(self.api(), values, QUERY_STRING='url=' + self.task_path()).status_code, 403)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, 'Widoczne zadanie')

    def test_configuration_schema_respects_empty_formset_rows_and_revision(self):
        self.client.force_login(self.owner)
        target = self.path('space', f'{self.space.slug}/configuration/')
        response = self.client.get(self.api(), {'url': target})
        self.assertEqual(response.status_code, 200)
        data = response.json()['data']
        self.assertEqual(response.json()['type'], 'space-configuration')
        self.assertFalse(any(field['required'] for group in data['sets'] for field in group['forms'][-1]['fields']))
        values = {'revision': data['revision']}
        for group in data['sets']:
            for form in [group['management'], *group['forms']]:
                for field in form['fields']:
                    if field['type'] == 'checkbox':
                        if field['checked']:
                            values[field['name']] = 'on'
                    elif field.get('multiple') and not field['value']:
                        continue
                    else:
                        values[field['name']] = field['value'] or ''
        response = self.client.post(self.api(), values, QUERY_STRING='url=' + target)
        self.assertEqual(response.status_code, 200, response.json())
        self.assertIn('redirect', response.json())
        self.space.configuration.refresh_from_db()
        self.space.configuration.settings['statuses'][0]['label'] = 'Zmieniona nazwa'
        self.space.configuration.save()
        stale = self.client.post(self.api(), values, QUERY_STRING='url=' + target)
        self.assertEqual(stale.status_code, 400)
        self.assertTrue(stale.json()['data']['errors'])

    def test_teams_api_uses_visible_space_choices_and_protects_last_admin(self):
        from spaces.models import Team, TeamMembership
        target = self.path('teams', 'create/')
        schema = self.client.get(self.api(), {'url': target}).json()['data']['form']
        choices = next(field for field in schema['fields'] if field['name'] == 'spaces')['choices']
        self.assertNotIn(str(self.private.pk), [choice['value'] for choice in choices])
        invalid = self.client.post(self.api(), {'name':'Zespół React', 'spaces':[self.private.pk]}, QUERY_STRING='url=' + target)
        self.assertEqual(invalid.status_code, 400)
        response = self.client.post(self.api(), {'name':'Zespół React', 'spaces':[self.space.pk]}, QUERY_STRING='url=' + target)
        self.assertEqual(response.status_code, 200)
        team = Team.objects.get(name='Zespół React', workplace=self.workspace)
        self.assertEqual(team.owner, self.owner)
        self.assertEqual(team.created_by, self.member)
        self.assertEqual(self.client.get(self.api(), {'url': self.path('teams')}).json()['type'], 'teams')
        detail = self.client.get(self.api(), {'url': self.path('teams', f'{team.pk}/')})
        self.assertEqual(detail.json()['type'], 'team')
        member = TeamMembership.objects.get(team=team, user=self.member)
        remove = self.path('teams', f'{team.pk}/members/{member.pk}/remove/')
        self.assertEqual(self.client.post(self.api(), QUERY_STRING='url=' + remove).status_code, 400)
        self.assertTrue(TeamMembership.objects.filter(pk=member.pk).exists())

    def test_legacy_ajax_headers_cannot_switch_api_back_to_html_fragments(self):
        target = self.task_path()
        response = self.client.post(self.api(), {'action':'save','title':'Zapis JSON','autosave_fields':'["title"]'}, QUERY_STRING='url=' + target, HTTP_X_REQUESTED_WITH='XMLHttpRequest', HTTP_X_WORK_MODAL='true')
        self.assertEqual(response.status_code, 200)
        self.assertIn('redirect', response.json())
        self.assertNotIn('activity_html', response.json())
