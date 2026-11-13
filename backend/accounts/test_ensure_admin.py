"""The installer succeeds only when an administrator can sign in."""
from io import StringIO
from unittest.mock import Mock, patch

from django.contrib.auth import authenticate, get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase


class EnsureAdminTests(TestCase):
    password = 'Ancore-setup!57-private-credential'
    answers = ('admin@example.test', 'ancore-admin', 'Anna', 'Nowak')

    def run_command(self, *, stdin=None, **options):
        self.output = StringIO()
        self.errors = StringIO()
        call_command('ensure_admin', stdin=stdin if stdin is not None else Mock(isatty=Mock(return_value=True)),
                     stdout=self.output, stderr=self.errors, **options)

    def create_admin(self):
        with patch('builtins.input', side_effect=self.answers) as fields, patch(
            'django.contrib.auth.management.commands.createsuperuser.getpass.getpass',
            side_effect=(self.password, self.password),
        ) as password:
            self.run_command()
        self.assertEqual(fields.call_count, 4)
        self.assertEqual(password.call_count, 2)
        return get_user_model().objects.get(email=self.answers[0])

    def test_native_prompts_create_administrator_with_hashed_password_and_working_login(self):
        user = self.create_admin()
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)
        self.assertEqual((user.username, user.first_name, user.last_name), self.answers[1:])
        self.assertNotEqual(user.password, self.password)
        self.assertTrue(user.check_password(self.password))
        self.assertEqual(authenticate(email=user.email, password=self.password), user)
        self.assertNotIn(self.password, self.output.getvalue() + self.errors.getvalue())

    def test_existing_administrator_skips_prompts_and_preserves_credentials_without_tty(self):
        user = self.create_admin()
        original = get_user_model().objects.values().get(pk=user.pk)
        with patch('builtins.input') as fields, patch(
            'django.contrib.auth.management.commands.createsuperuser.getpass.getpass',
        ) as password:
            self.run_command(stdin=StringIO())
        fields.assert_not_called()
        password.assert_not_called()
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(get_user_model().objects.values().get(pk=user.pk), original)
        self.assertIn('Administrator już istnieje', self.output.getvalue())

    def test_other_accounts_and_unusable_superusers_do_not_skip_creation_or_gain_permissions(self):
        for name, flags in (
            ('ordinary', {}),
            ('staff', {'is_staff': True}),
            ('inactive', {'is_staff': True, 'is_superuser': True, 'is_active': False}),
            ('nonstaff', {'is_superuser': True}),
            ('unusable', {'is_staff': True, 'is_superuser': True}),
            ('blank', {'is_staff': True, 'is_superuser': True}),
        ):
            user = get_user_model().objects.create_user(
                username=name, email=f'{name}@example.test',
                password=None if name == 'unusable' else self.password, **flags,
            )
            if name == 'blank':
                user.password = ''
                user.save(update_fields=['password'])
        original = list(get_user_model().objects.order_by('pk').values())
        created = self.create_admin()
        self.assertEqual(get_user_model().objects.count(), len(original) + 1)
        self.assertEqual(list(get_user_model().objects.exclude(pk=created.pk).order_by('pk').values()), original)

    def test_noninteractive_or_missing_tty_fails_without_creating_account(self):
        for options in ({'stdin': StringIO()}, {'interactive': False}, {'stdin': object()}):
            with self.subTest(options=options), patch('builtins.input') as fields, patch(
                'django.contrib.auth.management.commands.createsuperuser.getpass.getpass',
            ) as password, self.assertRaisesMessage(CommandError, 'interaktywnego terminala'):
                self.run_command(**options)
            fields.assert_not_called()
            password.assert_not_called()
            self.assertFalse(get_user_model().objects.exists())

    def test_eof_or_cancellation_during_fields_or_password_fails_without_creating_account(self):
        for failure in (EOFError, KeyboardInterrupt):
            for stage in ('fields', 'password'):
                with self.subTest(failure=failure, stage=stage), patch(
                    'builtins.input', side_effect=failure if stage == 'fields' else self.answers,
                ), patch(
                    'django.contrib.auth.management.commands.createsuperuser.getpass.getpass',
                    side_effect=failure if stage == 'password' else (self.password, self.password),
                ), self.assertRaisesMessage(CommandError, 'Przerwano tworzenie administratora'):
                    self.run_command()
                self.assertFalse(get_user_model().objects.exists())

    def test_native_command_skip_cannot_be_reported_as_success(self):
        with patch('django.contrib.auth.management.commands.createsuperuser.Command.handle'), self.assertRaisesMessage(
            CommandError, 'Nie utworzono aktywnego administratora',
        ):
            self.run_command()
        self.assertFalse(get_user_model().objects.exists())
