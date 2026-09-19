from django.db import migrations, models


class Migration(migrations.Migration):
    """Bring the initial custom-user schema up to the state used by 0006.

    The original migration referenced by ``0006`` was absent from the
    repository.  These fields are present on ``accounts.User`` and must exist
    before its presence-status alteration can run.
    """

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='middle_name',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='user',
            name='profile_photo',
            field=models.FileField(blank=True, upload_to='profile_photos/'),
        ),
        migrations.AddField(
            model_name='user',
            name='phone_number',
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name='user',
            name='job_title',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='user',
            name='bio',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='user',
            name='presence_status',
            field=models.CharField(
                choices=[
                    ('active', 'Aktywny'),
                    ('inactive', 'Nieaktywny'),
                    ('out_of_office', 'Poza biurem'),
                    ('busy', 'Zajęty'),
                    ('do_not_disturb', 'Nie przeszkadzać'),
                ],
                default='inactive',
                max_length=20,
            ),
        ),
    ]
