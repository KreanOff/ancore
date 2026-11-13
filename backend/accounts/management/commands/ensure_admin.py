"""Create the first usable administrator from prompts or installer stdin."""
from django.contrib.auth.management.commands.createsuperuser import Command as CreateSuperuserCommand
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction


class Command(CreateSuperuserCommand):
    help = 'Tworzy administratora, jeśli nie istnieje aktywny administrator z hasłem.'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument('--from-stdin', action='store_true',
                          help='Odczytuje dane konta i hasło z wejścia instalatora, bez pytań.')
        mode.add_argument('--check-only', action='store_true',
                          help='Sprawdza istnienie administratora, bez tworzenia konta.')

    def has_administrator(self, database):
        users = self.UserModel._default_manager.db_manager(database).filter(
            is_active=True, is_staff=True, is_superuser=True,
        ).only('password')
        return any(user.password and user.has_usable_password() for user in users.iterator())

    def create_from_stdin(self, database):
        # The shell sends five newline-terminated values through a pipe. Bound
        # reads and require EOF so a partial or shifted payload never creates an
        # account. Password whitespace is significant and must remain intact.
        fields = ('email', 'username', 'first_name', 'last_name', 'password')
        values = {}
        try:
            for field in fields:
                line = self.stdin.readline(4098)
                if not line.endswith('\n') or len(line) > 4097 or any(char in line for char in '\r\x00'):
                    raise ValueError
                value = line[:-1]
                values[field] = value if field == 'password' else value.strip()
            if self.stdin.read(1):
                raise ValueError
        except (AttributeError, OSError, ValueError, EOFError, KeyboardInterrupt) as error:
            raise CommandError('Niepełne lub nieprawidłowe dane administratora z instalatora.') from error

        password = values.pop('password')
        manager = self.UserModel._default_manager.db_manager(database)
        candidate = self.UserModel(**values, is_active=True, is_staff=True, is_superuser=True)
        candidate._state.db = database
        try:
            # Validate all model fields, including the required profile fields.
            # Uniqueness is checked below on the explicitly selected database.
            candidate.full_clean(exclude=('password',), validate_unique=False, validate_constraints=False)
            validate_password(password, candidate)
        except ValidationError as error:
            raise CommandError(
                'Nieprawidłowe dane administratora. Sprawdź e-mail, nazwę, imię, nazwisko i siłę hasła.'
            ) from error

        values = {field: getattr(candidate, field) for field in values}
        try:
            with transaction.atomic(using=database):
                if manager.filter(email__iexact=values['email']).exists() or manager.filter(username=values['username']).exists():
                    raise IntegrityError
                manager.create_superuser(password=password, **values)
        except IntegrityError as error:
            raise CommandError(
                'E-mail lub nazwa administratora są już używane. Istniejące konto pozostało bez zmian.'
            ) from error
        self.stdout.write('Utworzono administratora Ancore.')

    def handle(self, *args, **options):
        if options['from_stdin'] and options['check_only']:
            raise CommandError('Wybierz tylko jeden tryb: --from-stdin albo --check-only.')
        if self.has_administrator(options['database']):
            self.stdout.write('Administrator już istnieje. Zachowano jego konto i hasło.')
            return
        if options['check_only']:
            raise CommandError('Brak aktywnego administratora z ustawionym hasłem.')
        if options['from_stdin']:
            self.create_from_stdin(options['database'])
            return
        if not options['interactive'] or not getattr(self.stdin, 'isatty', lambda: False)():
            raise CommandError('Utworzenie administratora wymaga interaktywnego terminala. Uruchom instalator w terminalu.')

        self.stdout.write('Utwórz konto administratora Ancore.')
        try:
            super().handle(*args, **options)
        except (EOFError, KeyboardInterrupt, SystemExit) as error:
            raise CommandError('Przerwano tworzenie administratora. Uruchom instalator ponownie.') from error
        if not self.has_administrator(options['database']):
            raise CommandError('Nie utworzono aktywnego administratora z hasłem. Uruchom instalator ponownie.')
