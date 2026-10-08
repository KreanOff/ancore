import json
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from tasks.models import Task, TaskActivity, TaskProject, TaskSection
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import ACTIVE_WORKPLACE_SESSION_KEY, scoped_workplace_app_path
from .models import Dashboard, DashboardGadget


class PulpitTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = get_user_model().objects.create_user(username='pulpit-owner', email='owner@example.test')
        cls.member = get_user_model().objects.create_user(username='pulpit-member', email='member@example.test')
        cls.outsider = get_user_model().objects.create_user(username='pulpit-outsider', email='outsider@example.test')
        cls.workplace = create_workplace_for_user(cls.owner, 'Pulpity zespołu')
        cls.other = create_workplace_for_user(cls.owner, 'Inny Workspace')
        cls.membership = WorkplaceMembership.objects.create(workplace=cls.workplace, user=cls.member)

    def setUp(self):
        self.login(self.owner)

    def login(self, user, client=None):
        client = client or self.client
        client.force_login(user)
        session = client.session
        session[ACTIVE_WORKPLACE_SESSION_KEY] = self.workplace.pk
        session.save()

    def dashboard(self, **kwargs):
        return Dashboard.objects.create(owner=self.owner, workplace=self.workplace, created_by=self.owner, name='Przegląd zespołu', **kwargs)

    def task(self, **kwargs):
        return Task.objects.create(**{'user': self.owner, 'workplace': self.workplace, 'title': 'Jawne zadanie', **kwargs})

    def url(self, dashboard, suffix=''):
        return f'/dashboards/{dashboard.pk}/{suffix}'

    def form_data(self, **kwargs):
        return {'name': 'Mój pulpit', 'description': 'Opis pulpitu', 'visibility': 'private', 'layout': 'equal', **kwargs}

    def test_create_member_uses_workspace_owner_and_actual_creator(self):
        self.login(self.member)
        response = self.client.post('/dashboards/create/', self.form_data(), HTTP_X_PULPIT_MODAL='true')
        self.assertEqual(response.status_code, 200)
        dashboard = Dashboard.objects.get()
        self.assertEqual((dashboard.owner, dashboard.created_by, dashboard.workplace), (self.owner, self.member, self.workplace))
        self.assertEqual(dashboard.gadgets.count(), 0)
        self.assertTrue(dashboard.favorited_by.filter(pk=self.member.pk).exists())
        self.assertTrue(response.json()['saved'])
        self.login(self.owner)
        self.assertEqual(self.client.get(self.url(dashboard)).status_code, 404)

    def test_new_dashboard_stays_empty_until_first_gadget_is_added(self):
        for prefix in ['/dashboards/', scoped_workplace_app_path(self.workplace, 'dashboards')]:
            for modal in [False, True]:
                with self.subTest(prefix=prefix, modal=modal):
                    headers = {'HTTP_X_PULPIT_MODAL': 'true'} if modal else {}
                    response = self.client.post(prefix + 'create/', self.form_data(), **headers)
                    self.assertEqual(response.status_code, 200 if modal else 302)
                    detail_url = response.json()['url'] if modal else response['Location']
                    dashboard = Dashboard.objects.get(pk=int(detail_url.rstrip('/').rsplit('/', 1)[-1]))
                    self.assertFalse(dashboard.gadgets.exists())
                    for _ in range(2):
                        response = self.client.get(detail_url)
                        self.assertContains(response, 'Ten pulpit jest pusty.')
                        self.assertContains(response, 'Edytuj pulpit')
                        self.assertNotContains(response, 'data-editable="true"')
                        self.assertNotContains(response, 'data-pulpit-gadget=')
                        self.assertFalse(dashboard.gadgets.exists())
                    response = self.client.post(detail_url + 'gadgets/add/', {
                        'kind': 'progress', 'title': '', 'status': '',
                        'assignee': 'all',
                    }, **headers)
                    self.assertEqual(response.status_code, 200 if modal else 302)
                    self.assertEqual(dashboard.gadgets.get().kind, 'progress')
                    response = self.client.get(detail_url)
                    self.assertContains(response, 'Postęp pracy')
                    self.assertNotContains(response, 'Ten pulpit jest pusty.')

    def test_private_selected_workspace_and_revoked_membership(self):
        private = self.dashboard()
        selected = self.dashboard(visibility='selected')
        shared = self.dashboard(visibility='workspace')
        selected.shared_with.add(self.member)
        self.login(self.member)
        self.assertEqual(self.client.get(self.url(private)).status_code, 404)
        for dashboard in [selected, shared]:
            self.assertEqual(self.client.get(self.url(dashboard)).status_code, 200)
        selected.shared_with.remove(self.member)
        self.assertEqual(self.client.get(self.url(selected)).status_code, 404)
        self.membership.is_active = False
        self.membership.save()
        self.assertNotEqual(self.client.get(self.url(shared)).status_code, 200)

    def test_viewing_and_editing_gadgets_are_separate_for_the_creator(self):
        dashboard = self.dashboard()
        DashboardGadget.objects.create(dashboard=dashboard, kind='progress')
        for prefix in ['/dashboards/', scoped_workplace_app_path(self.workplace, 'dashboards')]:
            response = self.client.get(f'{prefix}{dashboard.pk}/')
            self.assertFalse(response.context['pulpits_management_mode'])
            self.assertContains(response, f'href="{scoped_workplace_app_path(self.workplace, "dashboards", f"{dashboard.pk}/gadgets/")}"')
            for control in ['data-editable="true"', 'data-pulpit-drag', 'data-pulpit-move', 'data-pulpit-layout', 'Dodaj gadżet']:
                self.assertNotContains(response, control)
            editor = self.client.get(f'{prefix}{dashboard.pk}/gadgets/')
            self.assertTemplateUsed(editor, 'dashboard/pulpits/gadgets.html')
            self.assertTrue(editor.context['pulpits_management_mode'])
            for control in ['data-editable="true"', 'data-pulpit-drag', 'data-pulpit-move', 'data-pulpit-layout', 'Dodaj gadżet', 'Wróć do pulpitu']:
                self.assertContains(editor, control)
            self.assertContains(editor, 'Zmiany układu zapisują się automatycznie.')

    def test_editor_get_requires_creator_and_current_workspace(self):
        dashboard = self.dashboard(visibility='workspace')
        self.login(self.member)
        for prefix in ['/dashboards/', scoped_workplace_app_path(self.workplace, 'dashboards')]:
            for suffix in [f'{dashboard.pk}/gadgets/', f'manage/{dashboard.pk}/gadgets/']:
                self.assertEqual(self.client.get(prefix + suffix).status_code, 403)
        self.login(self.owner)
        foreign = Dashboard.objects.create(owner=self.owner, workplace=self.other, created_by=self.owner, name='Obcy pulpit')
        self.assertEqual(self.client.get(self.url(foreign, 'gadgets/')).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(self.url(dashboard, 'gadgets/')).status_code, 302)

    def test_direct_gadget_forms_use_editor_background_and_return_to_editor(self):
        dashboard = self.dashboard()
        values = {'kind': 'progress', 'title': 'Statystyki', 'assignee': 'all'}
        for prefix in ['/dashboards/', scoped_workplace_app_path(self.workplace, 'dashboards')]:
            with self.subTest(prefix=prefix):
                editor_url = f'{prefix}{dashboard.pk}/gadgets/'
                target = scoped_workplace_app_path(self.workplace, 'dashboards', f'{dashboard.pk}/gadgets/')
                response = self.client.get(editor_url + 'add/')
                self.assertTemplateUsed(response, 'dashboard/pulpits/gadgets.html')
                self.assertTrue(response.context['pulpits_management_mode'])
                self.assertEqual(response.context['return_url'], target)
                invalid = self.client.post(editor_url + 'add/', {**values, 'kind': ''})
                self.assertEqual(invalid.status_code, 400)
                self.assertTemplateUsed(invalid, 'dashboard/pulpits/gadgets.html')
                self.assertContains(invalid, 'value="Statystyki"', status_code=400)
                added = self.client.post(editor_url + 'add/', values, HTTP_X_PULPIT_MODAL='true')
                self.assertEqual(added.json(), {'saved': True, 'url': target})
                gadget = dashboard.gadgets.latest('pk')
                updated = self.client.post(editor_url + f'{gadget.pk}/edit/', {**values, 'title': 'Po edycji'})
                self.assertRedirects(updated, target)
                deleted = self.client.post(editor_url + f'{gadget.pk}/delete/', HTTP_X_PULPIT_MODAL='true')
                self.assertEqual(deleted.json(), {'saved': True, 'url': target})
                self.assertFalse(dashboard.gadgets.exists())

    def test_empty_editor_can_save_each_layout_without_adding_gadgets(self):
        dashboard = self.dashboard()
        for revision, layout in enumerate(Dashboard.Layout.values):
            count = 1 if layout == 'single' else 3 if layout == 'three' else 2
            response = self.client.post(self.url(dashboard, 'arrange/'), json.dumps({
                'layout': layout, 'columns': [[] for _ in range(count)], 'revision': revision,
            }), content_type='application/json')
            self.assertEqual(response.status_code, 200)
            editor = self.client.get(self.url(dashboard, 'gadgets/'))
            self.assertContains(editor, f'value="{layout}" selected')
            self.assertContains(editor, 'data-pulpit-catalog')
            self.assertContains(editor, 'data-editable="true"')
            self.assertNotContains(editor, 'data-editable="true" hidden')
            self.assertFalse(dashboard.gadgets.exists())

    def test_selected_people_must_belong_to_active_workspace(self):
        response = self.client.post('/dashboards/create/', self.form_data(visibility='selected', shared_with=[self.outsider.pk]), HTTP_X_PULPIT_MODAL='true')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Dashboard.objects.exists())
        response = self.client.post('/dashboards/create/', self.form_data(visibility='selected', shared_with=[self.member.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(list(Dashboard.objects.get().shared_with.all()), [self.member])

    def test_read_only_member_cannot_change_dashboard_or_gadgets(self):
        dashboard = self.dashboard(visibility='workspace')
        gadget = DashboardGadget.objects.create(dashboard=dashboard, kind='progress')
        self.login(self.member)
        paths = ['edit/', 'access/', 'delete/', 'arrange/', 'gadgets/add/', f'gadgets/{gadget.pk}/edit/', f'gadgets/{gadget.pk}/delete/']
        for path in paths:
            self.assertEqual(self.client.post(self.url(dashboard, path), self.form_data()).status_code, 403, path)
        response = self.client.get(self.url(dashboard))
        self.assertNotContains(response, 'data-editable="true"')
        self.assertNotContains(response, 'data-pulpit-drag')

    def test_workspace_and_owner_scope_on_direct_urls(self):
        other = Dashboard.objects.create(owner=self.owner, workplace=self.other, created_by=self.owner, name='Inny pulpit', visibility='workspace')
        wrong = Dashboard.objects.create(owner=self.member, workplace=self.workplace, created_by=self.owner, name='Błędny właściciel', visibility='workspace')
        for dashboard in [other, wrong]:
            self.assertEqual(self.client.get(self.url(dashboard)).status_code, 404)
            self.assertEqual(self.client.post(self.url(dashboard, 'edit/'), self.form_data()).status_code, 404)

    def test_gadgets_respect_private_ancestors_owner_and_workspace(self):
        dashboard = self.dashboard(visibility='workspace')
        for kind in DashboardGadget.Kind.values:
            DashboardGadget.objects.create(dashboard=dashboard, kind=kind)
        visible = self.task(assignee=self.member, due_at=timezone.now()-timedelta(days=1))
        project = TaskProject.objects.create(user=self.owner, workplace=self.workplace, name='Sekretna przestrzeń', visibility='private', private_owner=self.owner)
        section = TaskSection.objects.create(project=project, title='Grupa')
        secret = self.task(title='Tajny tytuł', section=section, assignee=self.member)
        self.task(title='Tajne podzadanie', parent=secret)
        self.task(title='Z innego Workspace', workplace=self.other)
        self.task(title='Inny właściciel', user=self.outsider, assignee=self.member)
        TaskActivity.objects.create(task=secret, actor=self.owner, message='Sekretna aktywność')
        TaskActivity.objects.create(task=visible, actor=self.owner, action='updated', metadata={'subtask_pk': secret.pk})
        self.login(self.member)
        response = self.client.get(self.url(dashboard))
        self.assertEqual(response.status_code, 200)
        data = [entry for column in response.context['columns'] for entry in column]
        self.assertEqual([entry['count'] for entry in data], [1])
        self.assertEqual(data[0]['percent'], 0)
        self.assertContains(response, 'Zamknięte: 0 z 1')
        for text in ['Tajny tytuł', 'Tajne podzadanie', 'Z innego Workspace', 'Inny właściciel', 'Sekretna przestrzeń']:
            self.assertNotContains(response, text)

    def test_inaccessible_space_returns_no_metadata_or_fallback_data(self):
        dashboard = self.dashboard(visibility='workspace')
        project = TaskProject.objects.create(user=self.owner, workplace=self.workplace, name='Nazwa tajnej przestrzeni', visibility='private', private_owner=self.owner)
        DashboardGadget.objects.create(dashboard=dashboard, kind='progress', space=project.space)
        self.task()
        self.login(self.member)
        response = self.client.get(self.url(dashboard))
        self.assertContains(response, 'Nie masz dostępu do źródłowej przestrzeni')
        self.assertNotContains(response, project.name)
        self.assertTrue(response.context['columns'][0][0]['unavailable'])

    def test_retired_copy_routes_return_404_without_changing_configuration(self):
        dashboard = self.dashboard(visibility='workspace', layout='three')
        DashboardGadget.objects.create(dashboard=dashboard, kind='progress', title='Pilne', column=2, position=3)
        dashboard.shared_with.add(self.member)
        dashboard.favorited_by.add(self.owner)
        dashboards_before = list(Dashboard.objects.values())
        gadgets_before = list(DashboardGadget.objects.values())
        for viewer in [self.owner, self.member]:
            self.login(viewer)
            for prefix in ['/dashboards/', scoped_workplace_app_path(self.workplace, 'dashboards')]:
                for suffix in [f'{dashboard.pk}/copy/', f'manage/{dashboard.pk}/copy/']:
                    for method in ['get', 'post']:
                        with self.subTest(viewer=viewer.pk, prefix=prefix, suffix=suffix, method=method):
                            response = getattr(self.client, method)(prefix + suffix, self.form_data(), HTTP_X_PULPIT_MODAL='true')
                            self.assertEqual(response.status_code, 404)
        self.assertEqual(list(Dashboard.objects.values()), dashboards_before)
        self.assertEqual(list(DashboardGadget.objects.values()), gadgets_before)
        self.assertEqual(list(dashboard.shared_with.all()), [self.member])
        self.assertEqual(list(dashboard.favorited_by.all()), [self.owner])

    def test_copy_action_is_absent_from_catalog_detail_and_management(self):
        dashboard = self.dashboard(visibility='workspace')
        for viewer in [self.owner, self.member]:
            self.login(viewer)
            for prefix in ['/dashboards/', scoped_workplace_app_path(self.workplace, 'dashboards')]:
                for suffix in ['?tab=all', f'{dashboard.pk}/', 'manage/']:
                    with self.subTest(viewer=viewer.pk, prefix=prefix, suffix=suffix):
                        response = self.client.get(prefix + suffix)
                        self.assertEqual(response.status_code, 200)
                        self.assertNotContains(response, 'Kopiuj pulpit')
                        self.assertNotContains(response, '/copy/')
                        if suffix == f'{dashboard.pk}/':
                            self.assertContains(response, 'data-pulpit-refresh')
                            if viewer == self.owner:
                                for action in ['Gadżety i układ', 'Dostępy', 'Ustawienia', 'Usuń pulpit']:
                                    self.assertContains(response, action)
                            else:
                                self.assertNotContains(response, f'id="pulpit-actions-{dashboard.pk}"')

    def test_arrangement_validates_complete_set_and_revision(self):
        dashboard = self.dashboard()
        a = DashboardGadget.objects.create(dashboard=dashboard, kind='progress')
        b = DashboardGadget.objects.create(dashboard=dashboard, kind='progress')
        def arrange(columns, revision=0, layout='equal'):
            return self.client.post(self.url(dashboard, 'arrange/'), json.dumps({'layout': layout, 'columns': columns, 'revision': revision}), content_type='application/json')
        for columns in [[[a.pk], []], [[a.pk], [a.pk]], [[a.pk], [999999]]]:
            self.assertEqual(arrange(columns).status_code, 400)
        self.assertEqual(arrange([[b.pk], [a.pk]]).status_code, 200)
        a.refresh_from_db();b.refresh_from_db()
        self.assertEqual((a.column, b.column), (1, 0))
        self.assertEqual(arrange([[a.pk], [b.pk]]).status_code, 409)
        self.assertEqual(arrange([[b.pk, a.pk]], revision=1, layout='single').status_code, 200)
        dashboard.refresh_from_db()
        self.assertEqual((dashboard.layout, dashboard.revision), ('single', 2))

    def test_settings_edit_keeps_layout_and_gadgets_and_stales_old_arrangement(self):
        dashboard = self.dashboard(layout='three')
        gadget = DashboardGadget.objects.create(dashboard=dashboard, kind='progress', column=2)
        response = self.client.post(self.url(dashboard, 'edit/'), self.form_data(layout='single'))
        self.assertEqual(response.status_code, 302)
        gadget.refresh_from_db();dashboard.refresh_from_db()
        self.assertEqual((dashboard.layout, gadget.column), ('three', 2))
        self.assertEqual(dashboard.revision, 1)
        stale = self.client.post(self.url(dashboard, 'arrange/'), json.dumps({
            'layout': 'three', 'columns': [[], [], [gadget.pk]], 'revision': 0,
        }), content_type='application/json')
        self.assertEqual(stale.status_code, 409)

    def test_gadget_config_rejects_foreign_source_and_invalid_assignment(self):
        dashboard = self.dashboard()
        foreign = TaskProject.objects.create(user=self.owner, workplace=self.other, name='Obca przestrzeń')
        values = {'kind': 'progress', 'title': '', 'assignee': 'all'}
        for extra in [{'space': foreign.space.pk}, {'assignee': 'unknown'}, {'kind': 'unknown'}]:
            response = self.client.post(self.url(dashboard, 'gadgets/add/'), {**values, **extra}, HTTP_X_PULPIT_MODAL='true')
            self.assertEqual(response.status_code, 400)
            if 'assignee' in extra:
                self.assertEqual(response.json()['html'].count('id="id_assignee_error"'), 1)
        self.assertFalse(dashboard.gadgets.exists())
        response = self.client.post(self.url(dashboard, 'gadgets/add/'), values)
        self.assertEqual(response.status_code, 302)
        gadget = dashboard.gadgets.get()
        another = self.dashboard()
        self.assertEqual(self.client.post(self.url(another, f'gadgets/{gadget.pk}/delete/')).status_code, 404)

    def test_favorites_are_personal_search_and_scoped_links(self):
        dashboard = self.dashboard(visibility='workspace')
        self.assertEqual(self.client.post(self.url(dashboard, 'favorite/')).status_code, 302)
        self.assertContains(self.client.get('/dashboards/'), dashboard.name)
        self.login(self.member)
        self.assertContains(self.client.get('/dashboards/'), dashboard.name)
        self.assertFalse(dashboard.favorited_by.filter(pk=self.member.pk).exists())
        response = self.client.get(f'/workplaces/{self.workplace.slug}/dashboards/?q=Przegląd')
        self.assertContains(response, f'/workplaces/{self.workplace.slug}/dashboards/{dashboard.pk}/')
        self.assertEqual(self.client.post(self.url(dashboard, 'favorite/')).status_code, 302)
        self.assertEqual(dashboard.favorited_by.count(), 2)

    def test_delete_only_removes_configuration(self):
        dashboard = self.dashboard()
        DashboardGadget.objects.create(dashboard=dashboard, kind='progress')
        task = self.task()
        self.assertEqual(self.client.post(self.url(dashboard, 'delete/')).status_code, 302)
        self.assertFalse(Dashboard.objects.exists())
        self.assertFalse(DashboardGadget.objects.exists())
        self.assertTrue(Task.objects.filter(pk=task.pk).exists())

    def test_post_csrf_login_and_get_mutation_guards(self):
        dashboard = self.dashboard()
        guarded = Client(enforce_csrf_checks=True)
        self.login(self.owner, guarded)
        self.assertEqual(guarded.post(self.url(dashboard, 'favorite/')).status_code, 403)
        for suffix in ['delete/', 'favorite/', 'arrange/']:
            self.assertEqual(self.client.get(self.url(dashboard, suffix)).status_code, 405)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('pulpits:index')).status_code, 302)

    def test_progress_assignment_filters_are_viewer_specific(self):
        dashboard = self.dashboard(visibility='workspace')
        DashboardGadget.objects.create(dashboard=dashboard, kind='progress', assignee='me')
        DashboardGadget.objects.create(dashboard=dashboard, kind='progress')
        DashboardGadget.objects.create(dashboard=dashboard, kind='progress', assignee='unassigned')
        self.task(priority='urgent', assignee=self.member)
        self.task(priority='urgent', assignee=self.owner, status='closed')
        self.task(priority='low')
        self.login(self.member)
        response = self.client.get(self.url(dashboard))
        data = response.context['columns'][0]
        self.assertEqual(data[0]['count'], 1)
        self.assertEqual((data[1]['count'], data[1]['closed_count'], data[1]['percent']), (3, 1, 33))
        self.assertEqual(data[2]['count'], 1)
        self.login(self.owner)
        response = self.client.get(self.url(dashboard))
        self.assertEqual(response.context['columns'][0][0]['percent'], 100)

    def test_progress_counts_all_main_tasks_and_reopened_status(self):
        dashboard = self.dashboard()
        DashboardGadget.objects.create(dashboard=dashboard, kind='progress')
        for status, _label in Task.STATUS_CHOICES:
            for _ in range(6):
                self.task(status=status)
        closed = Task.objects.filter(status='closed').first()
        self.task(parent=closed, status='closed')
        for prefix in ['/dashboards/', scoped_workplace_app_path(self.workplace, 'dashboards')]:
            response = self.client.get(f'{prefix}{dashboard.pk}/')
            data = response.context['columns'][0][0]
            self.assertEqual((data['count'], data['closed_count'], data['percent']), (30, 6, 20))
            self.assertEqual(data['statuses'], [
                {'key': key, 'label': label, 'count': 6} for key, label in Task.STATUS_CHOICES
            ])
            self.assertContains(response, 'Zamknięte: 6 z 30')
            self.assertContains(response, 'value="20"')
        closed.status = 'reopened'
        closed.save()
        data = self.client.get(scoped_workplace_app_path(self.workplace, 'dashboards', f'{dashboard.pk}/')).context['columns'][0][0]
        self.assertEqual((data['count'], data['closed_count'], data['percent']), (30, 5, 17))
        self.assertEqual(next(row['count'] for row in data['statuses'] if row['key'] == 'reopened'), 7)

    def test_progress_empty_state_matches_reference_card(self):
        dashboard = self.dashboard()
        DashboardGadget.objects.create(dashboard=dashboard, kind='progress')
        response = self.client.get(self.url(dashboard))
        data = response.context['columns'][0][0]
        self.assertEqual((data['count'], data['closed_count'], data['percent']), (0, 0, 0))
        self.assertEqual([row['count'] for row in data['statuses']], [0] * 5)
        self.assertContains(response, 'Zamknięte: 0 z 0')
        self.assertContains(response, 'Zadania we wszystkich przestrzeniach Workspace')
        self.assertTemplateUsed(response, 'dashboard/includes/work_progress.html')
        self.assertTemplateUsed(self.client.get('/'), 'dashboard/includes/work_progress.html')

    def test_progress_filters_space_and_private_tasks_without_granting_access(self):
        dashboard = self.dashboard(visibility='workspace')
        project = TaskProject.objects.create(user=self.owner, workplace=self.workplace, name='Wybrane źródło')
        section = TaskSection.objects.create(project=project, title='Publiczna grupa')
        hidden_section = TaskSection.objects.create(project=project, title='Prywatna grupa', visibility='private', private_owner=self.owner)
        self.task(section=section, status='closed')
        self.task(section=section, status='new')
        self.task(section=section, status='closed', visibility='private', private_owner=self.owner, assignee=self.member)
        self.task(section=hidden_section, status='closed', assignee=self.member)
        self.task(status='closed')
        DashboardGadget.objects.create(dashboard=dashboard, kind='progress', space=project.space)
        self.login(self.member)
        response = self.client.get(self.url(dashboard))
        data = response.context['columns'][0][0]
        self.assertEqual((data['count'], data['closed_count'], data['percent']), (2, 1, 50))
        self.assertContains(response, 'Zadania w przestrzeni Wybrane źródło')
        project.visibility = 'private'
        project.private_owner = self.owner
        project.save()
        response = self.client.get(self.url(dashboard))
        self.assertTrue(response.context['columns'][0][0]['unavailable'])
        self.assertNotContains(response, project.name)
        self.assertNotContains(response, 'Zamknięte:')

    def test_deleting_space_cannot_broaden_saved_filter(self):
        dashboard = self.dashboard()
        project = TaskProject.objects.create(user=self.owner, workplace=self.workplace, name='Źródło')
        DashboardGadget.objects.create(dashboard=dashboard, kind='progress', space=project.space)
        project.space.delete()
        self.assertFalse(dashboard.gadgets.exists())

    def test_gadget_cap_and_failed_form_preserve_existing_configuration(self):
        dashboard = self.dashboard()
        DashboardGadget.objects.bulk_create([DashboardGadget(dashboard=dashboard, kind='progress', position=i) for i in range(24)])
        response = self.client.post(self.url(dashboard, 'gadgets/add/'),
                                    {'kind': 'progress', 'title': 'Zachowany szkic', 'assignee': 'all'}, HTTP_X_PULPIT_MODAL='true')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Zachowany szkic', response.json()['html'])
        self.assertIn('maksymalnie 24', response.json()['html'])
        self.assertEqual(dashboard.gadgets.count(), 24)

    def test_only_progress_is_available_for_add_and_edit(self):
        dashboard = self.dashboard()
        gadget = DashboardGadget.objects.create(dashboard=dashboard, kind='progress')
        for prefix in ['/dashboards/', scoped_workplace_app_path(self.workplace, 'dashboards')]:
            for suffix in ['gadgets/add/', f'gadgets/{gadget.pk}/edit/']:
                for modal in [False, True]:
                    with self.subTest(prefix=prefix, suffix=suffix, modal=modal):
                        headers = {'HTTP_X_PULPIT_MODAL': 'true'} if modal else {}
                        response = self.client.get(f'{prefix}{dashboard.pk}/{suffix}', **headers)
                        self.assertEqual(response.status_code, 200)
                        html = response.json()['html'] if modal else response.content.decode()
                        for kind in DashboardGadget.Kind.values:
                            self.assertIn(f'<option value="{kind}"', html)
                        for kind in ['assigned', 'results', 'summary', 'statistics', 'activity']:
                            self.assertNotIn(f'<option value="{kind}"', html)
                        for field in ['status', 'group_by', 'limit']:
                            self.assertNotIn(f'name="{field}"', html)

    def test_unknown_gadget_kinds_cannot_be_saved_and_preserve_existing_data(self):
        dashboard = self.dashboard()
        gadget = DashboardGadget.objects.create(dashboard=dashboard, kind='progress', title='Zapisany gadżet')
        values = {'title': 'Nowy tytuł', 'assignee': 'all'}
        for prefix in ['/dashboards/', scoped_workplace_app_path(self.workplace, 'dashboards')]:
            for suffix in ['gadgets/add/', f'gadgets/{gadget.pk}/edit/']:
                for kind in ['unknown', '<script>', 'assigned', 'results', 'summary', 'statistics', 'activity']:
                    with self.subTest(prefix=prefix, suffix=suffix, kind=kind):
                        response = self.client.post(f'{prefix}{dashboard.pk}/{suffix}', {**values, 'kind': kind}, HTTP_X_PULPIT_MODAL='true')
                        self.assertEqual(response.status_code, 400)
                        self.assertIn('Nowy tytuł', response.json()['html'])
                        self.assertEqual(dashboard.gadgets.count(), 1)
                        gadget.refresh_from_db()
                        dashboard.refresh_from_db()
                        self.assertEqual((gadget.kind, gadget.title, dashboard.revision), ('progress', 'Zapisany gadżet', 0))

    def test_all_available_kinds_can_be_added_and_reconfigured(self):
        dashboard = self.dashboard()
        values = {'title': '', 'assignee': 'all'}
        for kind in DashboardGadget.Kind.values:
            with self.subTest(kind=kind):
                response = self.client.post(self.url(dashboard, 'gadgets/add/'), {**values, 'kind': kind})
                self.assertEqual(response.status_code, 302)
                gadget = dashboard.gadgets.filter(kind=kind).latest('pk')
                self.assertEqual(gadget.assignee, 'all')
                legacy = DashboardGadget.objects.create(dashboard=dashboard, kind='progress')
                response = self.client.post(self.url(dashboard, f'gadgets/{legacy.pk}/edit/'), {**values, 'kind': kind})
                self.assertEqual(response.status_code, 302)
                legacy.refresh_from_db()
                self.assertEqual(legacy.kind, kind)

    def test_favorite_keeps_catalog_search_without_retired_tab(self):
        dashboard = self.dashboard()
        response = self.client.post(self.url(dashboard, 'favorite/'), {'tab': 'all', 'q': 'Przegląd'}, HTTP_X_PULPIT_MODAL='true')
        self.assertNotIn('tab=', response.json()['url'])
        self.assertIn('q=Przegl%C4%85d', response.json()['url'])

    def test_catalog_visibility_filter_respects_access_and_workspace(self):
        own = self.dashboard(visibility='private')
        shared = self.dashboard(visibility='selected')
        shared.shared_with.add(self.member)
        public = self.dashboard(visibility='workspace')
        member_private = Dashboard.objects.create(
            owner=self.owner, workplace=self.workplace, created_by=self.member,
            name='Prywatny członka', visibility='private',
        )
        Dashboard.objects.create(owner=self.owner, workplace=self.other, created_by=self.member,
                                 name='Obcy Workspace', visibility='workspace')
        self.login(self.member)
        for prefix in ['/dashboards/', scoped_workplace_app_path(self.workplace, 'dashboards')]:
            for tab in ['', 'all', 'favorites', 'mine', 'unknown']:
                with self.subTest(prefix=prefix, tab=tab):
                    response = self.client.get(prefix, {'tab': tab} if tab else {})
                    self.assertEqual({row.pk for row in response.context['dashboards']},
                                     {member_private.pk, shared.pk, public.pk})
                    self.assertNotContains(response, 'aria-label="Katalog pulpitów"')
                    search_form = response.content.decode().split('data-pulpit-search>', 1)[1].split('</form>', 1)[0]
                    self.assertNotIn('name="tab"', search_form)
                    self.assertContains(response, 'css/components/spaces.css')
            for visibility, expected in [('private', member_private), ('selected', shared), ('workspace', public)]:
                with self.subTest(prefix=prefix, visibility=visibility):
                    response = self.client.get(prefix, {'visibility': visibility})
                    self.assertEqual([row.pk for row in response.context['dashboards']], [expected.pk])
                    self.assertEqual(response.context['visibility_filter'], visibility)
            response = self.client.get(prefix, {'visibility': 'unknown'})
            self.assertEqual(response.context['visibility_filter'], '')
            self.assertEqual({row.pk for row in response.context['dashboards']}, {member_private.pk, shared.pk, public.pk})
            self.assertNotIn(own.pk, [row.pk for row in response.context['dashboards']])
        shared.shared_with.remove(self.member)
        response = self.client.get(scoped_workplace_app_path(self.workplace, 'dashboards'),
                                   {'visibility': 'selected'})
        self.assertEqual(response.context['page'].paginator.count, 0)
        self.assertContains(response, 'Brak pasujących pulpitów')
        self.assertContains(response, 'css/components/spaces.css')
        self.assertContains(response, f'href="{scoped_workplace_app_path(self.workplace, "dashboards")}"')

    def test_catalog_filters_survive_pagination_and_favorite(self):
        for number in range(31):
            Dashboard.objects.create(owner=self.owner, workplace=self.workplace, created_by=self.owner,
                                     name=f'Lista {number:02}', visibility='workspace')
        for prefix in ['/dashboards/', scoped_workplace_app_path(self.workplace, 'dashboards')]:
            filters = {'q': 'Lista', 'visibility': 'workspace', 'page': 2}
            response = self.client.get(prefix, filters)
            self.assertEqual(len(response.context['dashboards']), 1)
            self.assertEqual(response.context['page'].paginator.per_page, 30)
            self.assertEqual(response.context['page'].paginator.count, 31)
            self.assertEqual(parse_qs(urlparse(response.context['previous_url']).query), {
                'q': ['Lista'], 'visibility': ['workspace'], 'page': ['1'],
            })
            dashboard = response.context['dashboards'][0]
            next_url = response.wsgi_request.get_full_path()
            saved = self.client.post(dashboard.favorite_url, {'next': next_url}, HTTP_X_PULPIT_MODAL='true')
            self.assertEqual(saved.json()['url'], next_url)
