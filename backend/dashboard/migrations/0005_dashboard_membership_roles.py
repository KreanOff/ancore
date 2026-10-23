import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('dashboard', '0004_dashboard_emoji_library'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Adopt the existing M2M table without recreating it or copying its rows.
        migrations.SeparateDatabaseAndState(state_operations=[
            migrations.CreateModel(
                name='DashboardMembership',
                fields=[
                    ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                    ('dashboard', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                        related_name='memberships', to='dashboard.dashboard')),
                    ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,
                        related_name='dashboard_memberships', to=settings.AUTH_USER_MODEL)),
                ],
                options={'db_table': 'dashboard_dashboard_shared_with', 'unique_together': {('dashboard', 'user')}},
            ),
            migrations.AlterField(model_name='dashboard', name='shared_with',
                field=models.ManyToManyField(blank=True, related_name='shared_dashboards',
                    through='dashboard.DashboardMembership', to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.AddField(model_name='dashboardmembership', name='role',
            field=models.CharField(choices=[('admin', 'Administrator'), ('member', 'Członek'), ('observer', 'Obserwator')],
                                   default='observer', db_default='observer', max_length=20)),
        # Historical recipients have no recorded join date; leave it unknown.
        migrations.AddField(model_name='dashboardmembership', name='created_at',
            field=models.DateTimeField(blank=True, null=True)),
        migrations.AlterField(model_name='dashboardmembership', name='created_at',
            field=models.DateTimeField(blank=True, default=django.utils.timezone.now, null=True)),
        migrations.AddConstraint(model_name='dashboardmembership',
            constraint=models.CheckConstraint(condition=models.Q(role__in=['admin', 'member', 'observer']),
                                             name='dashboard_member_role_valid')),
    ]
