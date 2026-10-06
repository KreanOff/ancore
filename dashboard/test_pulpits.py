import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from tasks.models import Task, TaskActivity, TaskProject, TaskSection
from workplaces.models import WorkplaceMembership, create_workplace_for_user
from workplaces.services import ACTIVE_WORKPLACE_SESSION_KEY
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
        self.assertEqual(dashboard.gadgets.count(), 4)
        self.assertTrue(dashboard.favorited_by.filter(pk=self.member.pk).exists())
        self.assertTrue(response.json()['saved'])
        self.login(self.owner)
        self.assertEqual(self.client.get(self.url(dashboard)).status_code, 404)

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

    def test_selected_people_must_belong_to_active_workspace(self):
        response = self.client.post('/dashboards/create/', self.form_data(visibility='selected', shared_with=[self.outsider.pk]), HTTP_X_PULPIT_MODAL='true')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Dashboard.objects.exists())
        response = self.client.post('/dashboards/create/', self.form_data(visibility='selected', shared_with=[self.member.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(list(Dashboard.objects.get().shared_with.all()), [self.member])

    def test_read_only_member_cannot_change_dashboard_or_gadgets(self):
        dashboard = self.dashboard(visibility='workspace')
        gadget = DashboardGadget.objects.create(dashboard=dashboard, kind='summary')
        self.login(self.member)
        paths = ['edit/', 'delete/', 'arrange/', 'gadgets/add/', f'gadgets/{gadget.pk}/edit/', f'gadgets/{gadget.pk}/delete/']
        for path in paths:
            self.assertEqual(self.client.post(self.url(dashboard, path), self.form_data()).status_code, 403, path)
        response = self.client.get(self.url(dashboard))
        self.assertContains(response, 'Tylko do odczytu')
        self.assertNotContains(response, 'data-pulpit-drag')

    def test_workspace_and_owner_scope_on_direct_urls(self):
        other = Dashboard.objects.create(owner=self.owner, workplace=self.other, created_by=self.owner, name='Inny pulpit', visibility='workspace')
        wrong = Dashboard.objects.create(owner=self.member, workplace=self.workplace, created_by=self.owner, name='Błędny właściciel', visibility='workspace')
        for dashboard in [other, wrong]:
            self.assertEqual(self.client.get(self.url(dashboard)).status_code, 404)
            self.assertEqual(self.client.post(self.url(dashboard, 'copy/'), self.form_data()).status_code, 404)

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
        self.assertEqual([entry['count'] for entry in data if entry['gadget'].kind != 'activity'], [1]*4)
        activity = next(entry for entry in data if entry['gadget'].kind == 'activity')
        self.assertEqual(activity['count'], 1)
        self.assertEqual([row['action'] for row in activity['rows']], ['Utworzono zadanie'])
        self.assertContains(response, visible.title)
        for text in ['Tajny tytuł', 'Tajne podzadanie', 'Z innego Workspace', 'Inny właściciel', 'Sekretna przestrzeń']:
            self.assertNotContains(response, text)

    def test_inaccessible_space_returns_no_metadata_or_fallback_data(self):
        dashboard = self.dashboard(visibility='workspace')
        project = TaskProject.objects.create(user=self.owner, workplace=self.workplace, name='Nazwa tajnej przestrzeni', visibility='private', private_owner=self.owner)
        DashboardGadget.objects.create(dashboard=dashboard, kind='summary', space=project.space)
        self.task()
        self.login(self.member)
        response = self.client.get(self.url(dashboard))
        self.assertContains(response, 'Nie masz dostępu do źródłowej przestrzeni')
        self.assertNotContains(response, project.name)
        self.assertTrue(response.context['columns'][0][0]['unavailable'])

    def test_copy_is_private_independent_and_preserves_filters(self):
        dashboard = self.dashboard(visibility='workspace', layout='three')
        original = DashboardGadget.objects.create(dashboard=dashboard, kind='results', title='Pilne', status='new', column=2, position=3)
        self.login(self.member)
        response = self.client.post(self.url(dashboard, 'copy/'), self.form_data(layout='three'))
        self.assertEqual(response.status_code, 302)
        copied = Dashboard.objects.exclude(pk=dashboard.pk).get()
        self.assertEqual((copied.created_by, copied.visibility), (self.member, 'private'))
        gadget = copied.gadgets.get()
        self.assertNotEqual(gadget.pk, original.pk)
        self.assertEqual((gadget.title, gadget.status, gadget.column), ('Pilne', 'new', 2))
        self.assertFalse(copied.shared_with.exists())

    def test_arrangement_validates_complete_set_and_revision(self):
        dashboard = self.dashboard()
        a = DashboardGadget.objects.create(dashboard=dashboard, kind='summary')
        b = DashboardGadget.objects.create(dashboard=dashboard, kind='statistics')
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

    def test_layout_edit_keeps_all_gadgets_and_stales_old_arrangement(self):
        dashboard = self.dashboard(layout='three')
        gadget = DashboardGadget.objects.create(dashboard=dashboard, kind='summary', column=2)
        response = self.client.post(self.url(dashboard, 'edit/'), self.form_data(layout='single'))
        self.assertEqual(response.status_code, 302)
        gadget.refresh_from_db();dashboard.refresh_from_db()
        self.assertEqual(gadget.column, 0)
        self.assertEqual(dashboard.revision, 1)

    def test_gadget_config_rejects_foreign_source_limit_and_arbitrary_status(self):
        dashboard = self.dashboard()
        foreign = TaskProject.objects.create(user=self.owner, workplace=self.other, name='Obca przestrzeń')
        values = {'kind': 'results', 'title': '', 'status': '', 'assignee': 'all', 'group_by': 'status', 'limit': 10}
        for extra in [{'space': foreign.space.pk}, {'limit': 1000}, {'status': 'unknown'}, {'kind': 'unknown'}]:
            response = self.client.post(self.url(dashboard, 'gadgets/add/'), {**values, **extra}, HTTP_X_PULPIT_MODAL='true')
            self.assertEqual(response.status_code, 400)
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
        self.assertNotContains(self.client.get('/dashboards/'), dashboard.name)
        response = self.client.get(f'/workplaces/{self.workplace.slug}/dashboards/?tab=all&q=Przegląd')
        self.assertContains(response, f'/workplaces/{self.workplace.slug}/dashboards/{dashboard.pk}/')
        self.assertEqual(self.client.post(self.url(dashboard, 'favorite/')).status_code, 302)
        self.assertEqual(dashboard.favorited_by.count(), 2)

    def test_delete_only_removes_configuration(self):
        dashboard = self.dashboard()
        DashboardGadget.objects.create(dashboard=dashboard, kind='summary')
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

    def test_filter_statistics_and_assigned_are_viewer_specific(self):
        dashboard = self.dashboard(visibility='workspace')
        DashboardGadget.objects.create(dashboard=dashboard, kind='assigned')
        DashboardGadget.objects.create(dashboard=dashboard, kind='statistics', group_by='priority')
        self.task(priority='urgent', assignee=self.member)
        self.task(priority='urgent', assignee=self.owner, status='closed')
        self.task(priority='low')
        self.login(self.member)
        response = self.client.get(self.url(dashboard))
        data = response.context['columns'][0]
        self.assertEqual(data[0]['count'], 1)
        self.assertEqual(data[1]['rows'][0], {'label': 'Pilny', 'count': 2, 'percent': 67})

    def test_deleting_space_cannot_broaden_saved_filter(self):
        dashboard = self.dashboard()
        project = TaskProject.objects.create(user=self.owner, workplace=self.workplace, name='Źródło')
        DashboardGadget.objects.create(dashboard=dashboard, kind='results', space=project.space)
        project.space.delete()
        self.assertFalse(dashboard.gadgets.exists())

    def test_gadget_cap_and_failed_form_preserve_existing_configuration(self):
        dashboard = self.dashboard()
        DashboardGadget.objects.bulk_create([DashboardGadget(dashboard=dashboard, kind='summary', position=i) for i in range(24)])
        response = self.client.post(self.url(dashboard, 'gadgets/add/'),
                                    {'kind': 'results', 'title': 'Zachowany szkic', 'status': '', 'assignee': 'all', 'group_by': 'status', 'limit': 10}, HTTP_X_PULPIT_MODAL='true')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Zachowany szkic', response.json()['html'])
        self.assertIn('maksymalnie 24', response.json()['html'])
        self.assertEqual(dashboard.gadgets.count(), 24)

    def test_favorite_keeps_catalog_tab_and_search(self):
        dashboard = self.dashboard()
        response = self.client.post(self.url(dashboard, 'favorite/'), {'tab': 'all', 'q': 'Przegląd'}, HTTP_X_PULPIT_MODAL='true')
        self.assertIn('tab=all', response.json()['url'])
        self.assertIn('q=Przegl%C4%85d', response.json()['url'])
