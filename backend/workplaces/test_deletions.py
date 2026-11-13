"""Deleting two Workspaces must never bypass the owner's last-Workspace guard."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.db import SessionStore
from django.db import OperationalError, close_old_connections, connection, transaction
from django.test import RequestFactory, TransactionTestCase
from django.urls import reverse

from spaces.models import SpaceTask
from spaces.testing import make_space
from .models import Workplace, create_workplace_for_user
from .views import delete_workplace


class ConcurrentWorkplaceDeletionTests(TransactionTestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username='delete-owner', email='delete-owner@example.test')
        self.workspaces = [create_workplace_for_user(self.owner, f'Deletion {number}') for number in range(2)]
        for workplace in self.workspaces:
            space = make_space(user=self.owner, workplace=workplace, name='Przestrzeń')
            SpaceTask.objects.create(space=space, title='Zachowaj ostatnie dane', created_by=self.owner)

    def request(self, workplace):
        request = RequestFactory().post(reverse('workplaces:delete', args=[workplace.pk]), {'name': workplace.name})
        request.user, request.workplace = self.owner, workplace
        request.session = SessionStore()
        request._messages = FallbackStorage(request)
        return request

    def test_simultaneous_deletions_keep_one_workspace_and_its_data(self):
        start = Barrier(2)

        def remove(workplace):
            close_old_connections()
            try:
                request = self.request(workplace)
                start.wait(timeout=10)
                response = delete_workplace(request, workplace.pk)
                return response.status_code, [str(message) for message in get_messages(request)]
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(remove, self.workspaces))
        self.assertEqual([status for status, _ in results], [302, 302])
        messages = [message for _, rows in results for message in rows]
        self.assertIn('Nie możesz usunąć ostatniego miejsca pracy.', messages)
        remaining = Workplace.objects.get(owner=self.owner)
        self.assertEqual(SpaceTask.objects.filter(space__workplace=remaining).count(), 1)
        self.assertEqual(SpaceTask.objects.count(), 1)

    def test_deletion_waits_for_the_owner_lock_before_checking_replacement(self):
        def remove():
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '250ms'")
                try:
                    delete_workplace(self.request(self.workspaces[0]), self.workspaces[0].pk)
                except OperationalError as error:
                    return error.__cause__.pgcode
                return None
            finally:
                close_old_connections()

        with transaction.atomic():
            get_user_model().objects.select_for_update().get(pk=self.owner.pk)
            with ThreadPoolExecutor(max_workers=1) as executor:
                self.assertEqual(executor.submit(remove).result(timeout=10), '55P03')
        self.assertEqual(Workplace.objects.filter(owner=self.owner).count(), 2)
        self.assertEqual(SpaceTask.objects.count(), 2)

    def test_deletion_locks_target_before_validating_current_name(self):
        def remove():
            close_old_connections()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SET lock_timeout = '250ms'")
                try:
                    delete_workplace(self.request(self.workspaces[0]), self.workspaces[0].pk)
                except OperationalError as error:
                    return error.__cause__.pgcode
                return None
            finally:
                close_old_connections()

        with transaction.atomic():
            Workplace.objects.select_for_update().get(pk=self.workspaces[0].pk)
            with ThreadPoolExecutor(max_workers=1) as executor:
                self.assertEqual(executor.submit(remove).result(timeout=10), '55P03')
        self.assertEqual(Workplace.objects.filter(owner=self.owner).count(), 2)
        self.assertEqual(SpaceTask.objects.count(), 2)
