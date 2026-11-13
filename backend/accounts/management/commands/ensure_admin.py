"""Create the first usable administrator through Django's native prompts."""
from django.contrib.auth.management.commands.createsuperuser import Command as CreateSuperuserCommand
from django.core.management.base import CommandError


class Command(CreateSuperuserCommand):
    help = 'Tworzy administratora, jeśli nie istnieje aktywny administrator z hasłem.'

    def has_administrator(self, database):
        users = self.UserModel._default_manager.db_manager(database).filter(
            is_active=True, is_staff=True, is_superuser=True,
        ).only('password')
        return any(user.password and user.has_usable_password() for user in users.iterator())

    def handle(self, *args, **options):
        if self.has_administrator(options['database']):
            self.stdout.write('Administrator już istnieje. Zachowano jego konto i hasło.')
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
