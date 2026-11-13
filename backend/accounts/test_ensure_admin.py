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

    def installer_input(self, *, answers=None, password=None):
        return StringIO('\n'.join((*((answers or self.answers)),
                                  self.password if password is None else password)) + '\n')

    def test_installer_stdin_creates_valid_administrator_without_interactive_prompts(self):
        password = f'  {self.password}  '
        with patch('builtins.input') as fields, patch(
            'django.contrib.auth.management.commands.createsuperuser.getpass.getpass',
        ) as prompt:
            self.run_command(from_stdin=True, interactive=False,
                             stdin=self.installer_input(password=password))
        fields.assert_not_called()
        prompt.assert_not_called()
        user = get_user_model().objects.get(email=self.answers[0])
        self.assertTrue(user.is_active and user.is_staff and user.is_superuser)
        self.assertEqual((user.username, user.first_name, user.last_name), self.answers[1:])
        self.assertNotEqual(user.password, password)
        self.assertEqual(authenticate(email=user.email, password=password), user)
        self.assertIsNone(authenticate(email=user.email, password=self.password))
        self.assertNotIn(password, self.output.getvalue() + self.errors.getvalue())

    def test_installer_validation_rejects_bad_fields_and_password_without_account(self):
        for answers, password in (
            (('wrong-email', *self.answers[1:]), self.password),
            ((self.answers[0], 'invalid username!', *self.answers[2:]), self.password),
            ((self.answers[0], '', *self.answers[2:]), self.password),
            ((*self.answers[:2], '', self.answers[3]), self.password),
            ((*self.answers[:3], ''), self.password),
            ((*self.answers[:3], 'x' * 151), self.password),
            (self.answers, ''),
            (self.answers, 'abc'),
            (self.answers, '12345678901234'),
            (self.answers, 'password123'),
            (self.answers, 'ancore-admin'),
        ):
            with self.subTest(answers=answers, password_length=len(password)), self.assertRaisesMessage(
                CommandError, 'Nieprawidłowe dane administratora',
            ) as raised:
                self.run_command(from_stdin=True, stdin=self.installer_input(answers=answers, password=password))
            self.assertFalse(get_user_model().objects.exists())
            if password:
                self.assertNotIn(password, str(raised.exception) + self.output.getvalue() + self.errors.getvalue())

    def test_installer_rejects_truncated_extra_or_control_character_input(self):
        payload = self.installer_input().getvalue()
        invalid_payloads = ('', '\n'.join(self.answers) + '\n', payload[:-1], payload + 'extra\n',
                            payload.replace('Anna', 'An\rna'), payload.replace('Anna', 'An\x00na'),
                            payload.replace(self.password, 'x' * 4097))
        for payload in invalid_payloads:
            with self.subTest(length=len(payload)), self.assertRaisesMessage(
                CommandError, 'Niepełne lub nieprawidłowe dane',
            ):
                self.run_command(from_stdin=True, stdin=StringIO(payload))
            self.assertFalse(get_user_model().objects.exists())

    def test_installer_cannot_overwrite_or_promote_existing_account_with_same_identity(self):
        existing = get_user_model().objects.create_user(
            username=self.answers[1], email=self.answers[0].upper(), password=self.password,
        )
        original = get_user_model().objects.values().get(pk=existing.pk)
        for answers in (self.answers, ('other@example.test', *self.answers[1:]),
                        (self.answers[0], 'other-name', *self.answers[2:])):
            with self.subTest(answers=answers), self.assertRaisesMessage(CommandError, 'już używane'):
                self.run_command(from_stdin=True, stdin=self.installer_input(answers=answers))
            self.assertEqual(get_user_model().objects.count(), 1)
            self.assertEqual(get_user_model().objects.values().get(pk=existing.pk), original)

    def test_installer_existing_administrator_skips_read_and_preserves_all_fields(self):
        user = self.create_admin()
        original = get_user_model().objects.values().get(pk=user.pk)
        stdin = Mock(readline=Mock(side_effect=AssertionError('Input must remain unread')))
        self.run_command(from_stdin=True, stdin=stdin)
        stdin.readline.assert_not_called()
        self.assertEqual(get_user_model().objects.count(), 1)
        self.assertEqual(get_user_model().objects.values().get(pk=user.pk), original)

    def test_check_only_never_reads_input_or_creates_account_and_requires_usable_admin(self):
        stdin = Mock(readline=Mock(side_effect=AssertionError('Input must remain unread')))
        with patch('builtins.input') as fields, self.assertRaisesMessage(CommandError, 'Brak aktywnego administratora'):
            self.run_command(check_only=True, stdin=stdin)
        fields.assert_not_called()
        self.assertFalse(get_user_model().objects.exists())
        user = get_user_model().objects.create_superuser(username='existing', email='existing@example.test', password=None)
        with self.assertRaisesMessage(CommandError, 'Brak aktywnego administratora'):
            self.run_command(check_only=True, stdin=stdin)
        user.set_password(self.password)
        user.save(update_fields=['password'])
        original = get_user_model().objects.values().get(pk=user.pk)
        self.run_command(check_only=True, stdin=stdin)
        stdin.readline.assert_not_called()
        self.assertEqual(get_user_model().objects.values().get(pk=user.pk), original)
