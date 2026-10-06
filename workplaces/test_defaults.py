from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, local
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from django.db.models.query import QuerySet
from django.test import TestCase, TransactionTestCase
from django.urls import reverse

from .models import SidebarFavorite, Workplace, WorkplaceMembership, create_workplace_for_user
from .services import DEFAULT_WORKPLACE_NAMES, ensure_default_workplace, scoped_workplace_app_path


class DefaultWorkplaceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='default-owner', email='default-owner@example.test', password='testpass123',
        )

    def login(self):
        return self.client.post(reverse('login'), {
            'username': self.user.email, 'password': 'testpass123',
        }, follow=True)

    def test_first_login_creates_random_workspace_and_owner_setup(self):
        with patch('workplaces.services.choice', return_value=DEFAULT_WORKPLACE_NAMES[0]) as choose:
            response = self.login()

        workplace = Workplace.objects.get(owner=self.user)
        choose.assert_called_once_with(DEFAULT_WORKPLACE_NAMES)
        self.assertEqual(workplace.name, 'Biuro Latających Pierogów')
        self.assertEqual(workplace.slug, 'biuro-latajacych-pierogow')
        self.assertEqual(workplace.code, 'BIURO-LATAJACYCH-PIE')
        self.assertEqual(self.client.session['active_workplace_id'], workplace.pk)
        self.assertEqual(WorkplaceMembership.objects.get(
            workplace=workplace, user=self.user,
        ).role, WorkplaceMembership.Role.OWNER)
        self.assertTrue(SidebarFavorite.objects.filter(
            workplace=workplace, user=self.user, item_key='dashboard',
        ).exists())
        self.assertContains(response, workplace.name)

    def test_relogin_and_scoped_visit_keep_saved_name_after_edit(self):
        self.login()
        workplace = Workplace.objects.get(owner=self.user)
        workplace.name = 'Moje własne biuro'
        workplace.save(update_fields=['name'])
        self.client.logout()

        with patch('workplaces.services.choice') as choose:
            response = self.login()
            scoped_response = self.client.get(scoped_workplace_app_path(workplace, 'spaces'))

        choose.assert_not_called()
        workplace.refresh_from_db()
        self.assertEqual(workplace.name, 'Moje własne biuro')
        self.assertEqual(Workplace.objects.filter(owner=self.user).count(), 1)
        self.assertContains(response, workplace.name)
        self.assertContains(scoped_response, workplace.name)

    def test_existing_default_name_is_preserved(self):
        workplace = create_workplace_for_user(self.user, 'Moje miejsce pracy')

        with patch('workplaces.services.choice') as choose:
            self.assertEqual(ensure_default_workplace(self.user).pk, workplace.pk)

        choose.assert_not_called()
        workplace.refresh_from_db()
        self.assertEqual(workplace.name, 'Moje miejsce pracy')

    def test_membership_uses_shared_workspace_without_creating_personal_one(self):
        owner = get_user_model().objects.create_user(username='other-owner', email='other-owner@example.test')
        workplace = create_workplace_for_user(owner, 'Wspólne biuro')
        WorkplaceMembership.objects.create(workplace=workplace, user=self.user, role='member')

        with patch('workplaces.services.choice') as choose:
            self.assertEqual(ensure_default_workplace(self.user).pk, workplace.pk)

        choose.assert_not_called()
        self.assertFalse(Workplace.objects.filter(owner=self.user).exists())

    def test_same_random_name_for_different_owners_has_distinct_scoped_urls(self):
        other = get_user_model().objects.create_user(username='second-owner', email='second-owner@example.test')

        with patch('workplaces.services.choice', return_value=DEFAULT_WORKPLACE_NAMES[0]):
            first = ensure_default_workplace(self.user)
            second = ensure_default_workplace(other)

        self.assertEqual(first.name, second.name)
        self.assertNotEqual(first.slug, second.slug)
        self.assertNotEqual(scoped_workplace_app_path(first), scoped_workplace_app_path(second))

    def test_anonymous_visit_does_not_create_workspace(self):
        self.assertIsNone(ensure_default_workplace(AnonymousUser()))
        self.assertFalse(Workplace.objects.exists())


class ConcurrentDefaultWorkplaceTests(TransactionTestCase):
    def test_simultaneous_first_visits_create_one_workspace(self):
        user = get_user_model().objects.create_user(username='concurrent-owner', email='concurrent-owner@example.test')
        initial_reads = Barrier(2)
        thread_state = local()
        original_first = QuerySet.first

        def simultaneous_first(queryset):
            result = original_first(queryset)
            if queryset.model is Workplace and not getattr(thread_state, 'initial_read', False):
                thread_state.initial_read = True
                initial_reads.wait(timeout=10)
            return result

        def first_visit():
            close_old_connections()
            try:
                return ensure_default_workplace(user).pk
            finally:
                close_old_connections()

        with patch.object(QuerySet, 'first', simultaneous_first):
            with patch('workplaces.services.choice', return_value=DEFAULT_WORKPLACE_NAMES[0]) as choose:
                with ThreadPoolExecutor(max_workers=2) as executor:
                    ids = list(executor.map(lambda _: first_visit(), range(2)))

        self.assertEqual(ids[0], ids[1])
        self.assertEqual(Workplace.objects.filter(owner=user).count(), 1)
        self.assertEqual(WorkplaceMembership.objects.filter(user=user).count(), 1)
        self.assertEqual(SidebarFavorite.objects.filter(user=user, item_key='dashboard').count(), 1)
        choose.assert_called_once_with(DEFAULT_WORKPLACE_NAMES)
