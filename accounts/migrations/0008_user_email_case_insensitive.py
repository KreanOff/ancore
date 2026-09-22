from django.db import migrations, models
from django.db.models.functions import Lower


def check_email_duplicates(apps, schema_editor):
    users = apps.get_model('accounts', 'User').objects.using(schema_editor.connection.alias)
    duplicates = users.annotate(email_key=Lower('email')).values('email_key').annotate(
        total=models.Count('pk'),
    ).filter(total__gt=1)
    if duplicates.exists():
        # Never merge identities or delete accounts automatically.
        raise RuntimeError(
            'Nie można dodać unikalności e-maili: istnieją konta różniące się tylko '
            'wielkością liter adresu. Wyjaśnij duplikaty w accounts.User i ponów migrate. '
            'Żadne konto nie zostało zmienione.'
        )


class Migration(migrations.Migration):
    dependencies = [('accounts', '0007_alter_user_profile_photo')]
    operations = [
        migrations.RunPython(check_email_duplicates, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='user',
            constraint=models.UniqueConstraint(Lower('email'), name='accounts_user_email_ci_unique'),
        ),
    ]
