import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0002_user_default_workplace'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='profile_banner',
            field=models.FileField(
                blank=True,
                upload_to='profile_banners/',
                validators=[django.core.validators.FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
            ),
        ),
    ]
