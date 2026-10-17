"""Retirement contracts for the four former Contacts directories."""
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import Resolver404, resolve, reverse

from kanban.models import KanbanProject
from tasks.models import TaskProject
from workplaces.models import SidebarFavorite, WorkplaceMembership, create_workplace_for_user
from workplaces.services import scoped_workplace_app_path, workplace_management_url

from legacy.contacts.models import Company, Contact, UserContact


RETIRED_SUFFIXES = (
    '', 'users/', 'users/lookup/', 'users/1/add/',
    'companies/', 'companies/1/', 'companies/1/edit/', 'companies/1/delete/',
    'guests/', 'view-contact/1/', 'view-contact/1/edit/', 'delete/1/',
    'new/', 'companies/new/',
)
RETIRED_FAVORITES = (
    'contacts-all', 'contacts-companies', 'contacts-guests', 'contacts-people',
)


class RetiredContactRoutesTests(SimpleTestCase):
    def test_plain_and_workspace_routes_are_not_registered(self):
        for prefix in ('/contacts/', '/workplaces/example/contacts/'):
            for suffix in RETIRED_SUFFIXES:
                with self.subTest(path=prefix + suffix), self.assertRaises(Resolver404):
                    resolve(prefix + suffix)

    def test_retired_models_are_not_exposed_in_admin(self):
        for model in (Company, Contact, UserContact):
            self.assertFalse(admin.site.is_registered(model))


class RetiredContactDirectoryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        users = get_user_model()
        cls.owner = users.objects.create_user(username='retired-owner', email='owner@retired.test')
        cls.member = users.objects.create_user(username='retired-member', email='member@retired.test')
        cls.outsider = users.objects.create_user(username='retired-outsider', email='outsider@retired.test')
        cls.workplace = create_workplace_for_user(cls.owner, 'Workspace testowy')
        cls.other = create_workplace_for_user(cls.owner, 'Drugi Workspace')
        cls.membership = WorkplaceMembership.objects.create(workplace=cls.workplace, user=cls.member)
        cls.company = Company.objects.create(owner=cls.owner, workplace=cls.workplace, name='ArchivedCompanyProbe')
        cls.contact = Contact.objects.create(user=cls.owner, workplace=cls.workplace, first_name='ArchivedContactProbe', company_record=cls.company)
        cls.link = UserContact.objects.create(owner=cls.owner, workplace=cls.workplace, target_user=cls.member, linked_contact=cls.contact)
        cls.project = TaskProject.objects.create(user=cls.owner, workplace=cls.workplace, name='Projekt z historyczną firmą', company=cls.company)
        cls.kanban = KanbanProject.objects.create(user=cls.owner, workplace=cls.workplace, name='Tablica z historyczną firmą', company=cls.company)

    def login(self, user):
        self.client.force_login(user)
        session = self.client.session
        session['active_workplace_id'] = self.workplace.pk
        session['workspace_url_scope_enabled'] = True
        session.save()

    def test_retired_get_and_post_return_404_for_every_audience(self):
        for user in (None, self.owner, self.member, self.outsider):
            if user:
                self.login(user)
            else:
                self.client.logout()
            for prefix in ('/contacts/', f'/workplaces/{self.workplace.slug}/contacts/'):
                for suffix in RETIRED_SUFFIXES:
                    for method in ('get', 'post'):
                        with self.subTest(user=user, path=prefix + suffix, method=method):
                            response = getattr(self.client, method)(prefix + suffix)
                            self.assertEqual(response.status_code, 404)
        self.assertEqual(Company.objects.count(), 1)
        self.assertEqual(Contact.objects.count(), 1)
        self.assertEqual(UserContact.objects.count(), 1)
        self.contact.refresh_from_db()
        self.assertEqual(self.contact.first_name, 'ArchivedContactProbe')

    def test_search_omits_retired_records_and_navigation(self):
        for user in (self.owner, self.member):
            self.login(user)
            for query in ('ArchivedContactProbe', 'ArchivedCompanyProbe', 'Kontakty', 'Firmy', 'Użytkownicy', 'Goście'):
                response = self.client.get(reverse('global_search'), {'q': query})
                self.assertEqual(response.status_code, 200)
                groups = response.json()['groups']
                self.assertFalse({'contacts', 'companies'} & {group['key'] for group in groups})
                self.assertNotContains(response, '/contacts/')
            # Historical project/company relations remain stored, but neither
            # retired directory participates in active search.
            response = self.client.get(reverse('global_search'), {'q': 'ArchivedCompanyProbe'})
            self.assertFalse({'projects', 'contacts', 'companies'} & {group['key'] for group in response.json()['groups']})
            self.assertNotContains(response, self.project.name)
            self.project.refresh_from_db()
            self.assertEqual(self.project.company_id, self.company.pk)

    def test_legacy_favorites_do_not_restore_retired_directories(self):
        self.login(self.owner)
        for key in RETIRED_FAVORITES:
            SidebarFavorite.objects.create(user=self.owner, workplace=self.workplace, item_key=key)
        for workplace in (self.workplace, self.other):
            response = self.client.get(scoped_workplace_app_path(workplace, 'spaces'))
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, '/contacts/')
            for label in ('Kontakty', 'Firmy', 'Użytkownicy', 'Goście'):
                self.assertNotContains(response, f'>{label}</span>')
            self.assertNotContains(response, 'Starsze widoki')
        endpoint = reverse('workplaces:toggle-sidebar-favorite', args=[self.workplace.pk])
        for key in RETIRED_FAVORITES:
            response = self.client.post(endpoint, {'item_key': key, 'favorite_action': 'add'}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            self.assertEqual(response.status_code, 400)

    def test_accounts_team_and_historical_project_relations_remain_available(self):
        self.login(self.member)
        for path in (reverse('profile'), scoped_workplace_app_path(self.workplace, 'teams')):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)
        self.assertRedirects(
            self.client.get(reverse('workplaces:team', args=[self.workplace.pk])),
            workplace_management_url(self.workplace),
        )
        for project in (self.project, self.kanban):
            project.refresh_from_db()
            self.assertEqual(project.company_id, self.company.pk)
        self.assertTrue(WorkplaceMembership.objects.filter(pk=self.membership.pk, is_active=True).exists())

    def test_workspace_switch_does_not_backfill_archived_contacts(self):
        company = Company.objects.create(owner=self.owner, name='Firma bez Workspace')
        contact = Contact.objects.create(user=self.owner, first_name='Dawny kontakt', company_record=company)
        link = UserContact.objects.create(owner=self.owner, target_user=self.member, linked_contact=contact)
        self.login(self.owner)
        for workplace in (self.workplace, self.other):
            response = self.client.get(scoped_workplace_app_path(workplace, 'spaces'))
            self.assertEqual(response.status_code, 200)
            for item in (company, contact, link):
                item.refresh_from_db()
                self.assertIsNone(item.workplace_id)
